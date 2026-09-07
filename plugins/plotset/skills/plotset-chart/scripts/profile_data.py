#!/usr/bin/env python3
"""Normalize a CSV for PlotSet and profile it so the chart can be chosen from evidence.

Two jobs, deliberately in one pass:

1. Normalize. PlotSet's binding engine and the video date-series parser are both
   strict in ways spreadsheets are not: blank header cells, duplicate column
   names, "$1,234", "(500)" for negatives, and DD/MM/YYYY dates all bind or parse
   wrong rather than loudly failing. Cleaning has to happen before upload, not after
   a confusing preview.

2. Profile. Chart type and design system should follow from what the data actually
   is -- its shape, cardinality, and subject matter -- rather than from the first
   chart type that comes to mind. The profile is the evidence for that choice.

Usage:
    profile_data.py IN.csv --out clean.csv --profile profile.json
    profile_data.py IN.csv --out clean.csv --pivot        # long -> wide, for video
    profile_data.py IN.csv --profile -                    # profile to stdout only

Stdlib only, so it runs anywhere without an install step.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime

CURRENCY = "$€£¥₹₽₩฿₪₺R$"
CURRENCY_NAMES = {"usd", "eur", "gbp", "jpy", "inr", "cad", "aud", "chf", "cny"}

DATE_FORMATS = [
    ("%Y-%m-%d", False), ("%Y/%m/%d", False), ("%Y.%m.%d", False),
    ("%d/%m/%Y", True), ("%d-%m-%Y", True), ("%d.%m.%Y", True),
    ("%m/%d/%Y", False), ("%m-%d-%Y", False),
    ("%d %b %Y", True), ("%d %B %Y", True),
    ("%b %d, %Y", False), ("%B %d, %Y", False),
    ("%Y-%m", False), ("%m/%Y", False), ("%b %Y", False), ("%B %Y", False),
    ("%Y", False),
]

DOMAIN_HINTS = OrderedDict([
    ("ledger", "revenue cost price sales profit margin budget spend arr mrr ebitda cashflow "
               "invoice payroll expense earnings gross net units inventory headcount valuation"),
    ("bulletin", "cases deaths births population vaccin patients infection mortality literacy "
                 "poverty unemployment census household migration crime housing turnout voters"),
    ("broadcast", "team club player rank ranking medal medals goals wins losses points score "
                  "championship league season tournament marketshare share competitor podium"),
    ("fieldnotes", "temperature climate co2 emission emissions rainfall precipitation forest "
                   "species biodiversity crop yield harvest soil water energy solar wind renewable"),
    ("terminal", "latency p50 p95 p99 requests rps qps throughput errors error_rate uptime "
                 "downtime cpu memory disk deploy deploys build builds incidents mttr apdex"),
    ("atlas", "country countries state province region city county district municipality "
              "territory continent iso lat lon latitude longitude postcode zip geo"),
    ("clinical", "patient dose dosage bpm glucose cholesterol trial cohort diagnosis lab "
                 "specimen threshold tolerance defect defects sla compliance pass fail variance"),
    ("playbook", "student students grade grades class classroom school pupil reading quiz "
                 "lesson badge badges stars donation donors volunteers members signups"),
])


def sniff_dialect(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def read_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(64 * 1024)
        fh.seek(0)
        return [r for r in csv.reader(fh, sniff_dialect(sample))]


def normalize_header(cells):
    """Blank cells become col-N (matching web-app's normalizeDataHeader), then
    duplicates get a numeric suffix -- two columns with the same name make the
    binding engine pick one arbitrarily."""
    blanks = 0
    out, seen, notes = [], Counter(), []
    for cell in cells:
        name = (cell or "").strip()
        if not name:
            blanks += 1
            name = f"col-{blanks}"
            notes.append(f"blank header renamed to {name}")
        seen[name] += 1
        if seen[name] > 1:
            renamed = f"{name}_{seen[name]}"
            notes.append(f"duplicate header {name!r} renamed to {renamed!r}")
            name = renamed
        out.append(name)
    return out, notes


NUM_RE = re.compile(r"^[-+(]?\s*[%s]?\s*[\d][\d\s,. ']*\s*[%%]?\s*[)]?$" % re.escape(CURRENCY))


def parse_number(raw):
    """Return (float, unit) or (None, None). Handles currency symbols, thousands
    separators in either convention, percentages, and accounting negatives."""
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s or not NUM_RE.match(s):
        return None, None
    unit = None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    for sym in CURRENCY:
        if sym in s:
            unit = "currency"
            s = s.replace(sym, "")
    if "%" in s:
        unit = "percent"
        s = s.replace("%", "")
    s = s.replace(" ", "").replace(" ", "").replace("'", "").strip()
    if not s or s in "+-":
        return None, None
    # "1.234,56" (European) vs "1,234.56" -- decide by which separator is last.
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rindex(".") > s.rindex(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        parts = s.split(",")
        # A lone comma with exactly 3 trailing digits is a thousands separator.
        s = s.replace(",", "") if len(parts[-1]) == 3 and len(parts) > 1 else s.replace(",", ".")
    try:
        value = float(s)
    except ValueError:
        return None, None
    return (-value if negative else value), unit


def format_number(value):
    """Plain decimal, never scientific notation -- PlotSet parses these as text
    and 1.2405e+06 silently becomes a category rather than 1240500."""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


def parse_date(raw):
    """Return (iso_string, was_day_first) or (None, False)."""
    if raw is None:
        return None, False
    s = str(raw).strip()
    if not s or len(s) > 32:
        return None, False
    for fmt, day_first in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if fmt == "%Y":
            return f"{dt.year:04d}-01-01", False
        if fmt in ("%Y-%m", "%m/%Y", "%b %Y", "%B %Y"):
            return f"{dt.year:04d}-{dt.month:02d}-01", False
        return dt.strftime("%Y-%m-%d"), day_first
    return None, False


def classify(column):
    """Decide a column's type from its values. Ambiguity is resolved toward the
    stricter reading: a column is only numeric or a date if nearly all of its
    non-empty values parse that way, because a single stray string will otherwise
    silently drop rows downstream."""
    values = [v for v in column if str(v).strip() != ""]
    if not values:
        return {"type": "empty", "filled": 0}
    dates = [parse_date(v) for v in values]
    n_dates = sum(1 for d, _ in dates if d)
    if n_dates / len(values) >= 0.9:
        isos = sorted(d for d, _ in dates if d)
        return {
            "type": "date", "filled": len(values),
            "dayFirstDetected": any(df for d, df in dates if d),
            "min": isos[0], "max": isos[-1],
        }
    nums = [parse_number(v) for v in values]
    n_nums = sum(1 for n, _ in nums if n is not None)
    if n_nums / len(values) >= 0.9:
        vals = [n for n, _ in nums if n is not None]
        units = {u for _, u in nums if u}
        return {
            "type": "number", "filled": len(values),
            "unit": sorted(units)[0] if units else None,
            "min": min(vals), "max": max(vals),
            "sum": round(sum(vals), 6),
            "allNonNegative": all(v >= 0 for v in vals),
        }
    counts = Counter(str(v).strip() for v in values)
    return {
        "type": "category" if len(counts) <= max(30, len(values) * 0.5) else "text",
        "filled": len(values),
        "unique": len(counts),
        "top": [k for k, _ in counts.most_common(6)],
    }


GEO_HEADER_WORDS = set(
    "country countries state province provinces region regions city cities county counties "
    "district municipality territory continent nation iso lat lon latitude longitude "
    "postcode zip geo location area".split())


def is_geographic(header):
    """Header-driven only, on purpose. Category VALUES are a trap: a league table
    whose clubs include "Man City" is not geographic data, and a choropleth is the
    wrong chart for it."""
    tokens = set()
    for name in header:
        tokens |= set(re.findall(r"[a-z]+", name.lower()))
    return bool(tokens & GEO_HEADER_WORDS)


def domain_hints(header, categories):
    """Rank design systems by subject-matter evidence in the column names and
    category values. Evidence, not a verdict -- the caller still decides."""
    corpus = " ".join(header + categories).lower()
    tokens = set(re.findall(r"[a-z_]+", corpus))
    ranked = []
    for system, words in DOMAIN_HINTS.items():
        matched = sorted(tokens & set(words.split()))
        if matched:
            ranked.append({"system": system, "matched": matched, "score": len(matched)})
    ranked.sort(key=lambda h: -h["score"])
    return ranked


def build_profile(header, rows, columns, types):
    n = len(rows)
    date_cols = [i for i, t in enumerate(types) if t["type"] == "date"]
    num_cols = [i for i, t in enumerate(types) if t["type"] == "number"]
    cat_cols = [i for i, t in enumerate(types) if t["type"] in ("category", "text")]

    shape = "unknown"
    if date_cols and len(num_cols) >= 1 and not cat_cols:
        shape = "wide-time-series"
    elif date_cols and cat_cols and len(num_cols) == 1:
        shape = "long-time-series"
    elif not date_cols and len(cat_cols) == 1 and len(num_cols) == 1:
        shape = "single-series-categorical"
    elif not date_cols and len(cat_cols) == 1 and len(num_cols) > 1:
        shape = "multi-series-categorical"
    elif len(cat_cols) >= 2 and len(num_cols) >= 1:
        shape = "hierarchical-or-grouped"

    first_cat = types[cat_cols[0]] if cat_cols else None
    cardinality = first_cat.get("unique") if first_cat else None
    part_to_whole = bool(
        shape == "single-series-categorical"
        and cardinality is not None and 2 <= cardinality <= 8
        and types[num_cols[0]].get("allNonNegative")
    )

    sample_cats = []
    for i in cat_cols[:2]:
        sample_cats.extend(types[i].get("top", []))
    hints = domain_hints(header, sample_cats)

    return {
        "rows": n,
        "columns": len(header),
        "header": header,
        "shape": shape,
        "columnTypes": {header[i]: types[i] for i in range(len(header))},
        "dateColumns": [header[i] for i in date_cols],
        "numericColumns": [header[i] for i in num_cols],
        "categoryColumns": [header[i] for i in cat_cols],
        "categoryCardinality": cardinality,
        "partToWholeCandidate": part_to_whole,
        "geographic": is_geographic(header),
        "videoReady": shape in ("wide-time-series", "long-time-series") and n >= 2,
        "designSystemHints": hints,
    }


def pivot_long_to_wide(header, rows, types):
    """Video race templates need one date column plus one column per series.
    Long data (date, series, value) has to be pivoted first or every frame
    collapses to a single bar."""
    date_i = next((i for i, t in enumerate(types) if t["type"] == "date"), None)
    num_i = next((i for i, t in enumerate(types) if t["type"] == "number"), None)
    cat_i = next((i for i, t in enumerate(types) if t["type"] in ("category", "text")), None)
    if date_i is None or num_i is None or cat_i is None:
        raise SystemExit("pivot needs one date column, one category column and one numeric column")
    series = sorted({r[cat_i] for r in rows if r[cat_i]})
    buckets = OrderedDict()
    for r in rows:
        buckets.setdefault(r[date_i], {})[r[cat_i]] = r[num_i]
    out_header = [header[date_i]] + series
    out_rows = [[d] + [vals.get(s, "") for s in series] for d, vals in sorted(buckets.items())]
    return out_header, out_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--out", help="write the normalized CSV here ('-' for stdout)")
    ap.add_argument("--profile", help="write the profile JSON here ('-' for stdout)")
    ap.add_argument("--pivot", action="store_true", help="pivot long (date,series,value) to wide for video")
    args = ap.parse_args()

    raw = read_rows(args.input)
    raw = [r for r in raw if any(str(c).strip() for c in r)]
    if not raw:
        raise SystemExit("no rows found")

    header, notes = normalize_header(raw[0])
    width = len(header)
    rows = [[(r[i].strip() if i < len(r) and r[i] is not None else "") for i in range(width)] for r in raw[1:]]

    keep = [i for i in range(width) if any(r[i] for r in rows)]
    if len(keep) < width:
        notes.append(f"dropped {width - len(keep)} entirely empty column(s)")
        header = [header[i] for i in keep]
        rows = [[r[i] for i in keep] for r in rows]

    columns = [[r[i] for r in rows] for i in range(len(header))]
    types = [classify(c) for c in columns]

    # Rewrite cells into canonical form so PlotSet parses what we think it parses.
    for i, t in enumerate(types):
        if t["type"] == "date":
            if t.get("dayFirstDetected"):
                notes.append(f"column {header[i]!r}: day-first dates normalized to yyyy-MM-dd")
            for r in rows:
                iso, _ = parse_date(r[i])
                if iso:
                    r[i] = iso
        elif t["type"] == "number":
            if t.get("unit"):
                notes.append(f"column {header[i]!r}: stripped {t['unit']} formatting to bare numbers")
            for r in rows:
                val, _ = parse_number(r[i])
                if val is not None:
                    r[i] = format_number(val)

    profile = build_profile(header, rows, columns, types)
    profile["normalizationNotes"] = notes

    if args.pivot:
        header, rows = pivot_long_to_wide(header, rows, types)
        profile["pivoted"] = {"to": "wide-time-series", "series": header[1:]}

    if args.out:
        stream = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8", newline="")
        w = csv.writer(stream, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
        if stream is not sys.stdout:
            stream.close()

    if args.profile:
        text = json.dumps(profile, indent=2)
        if args.profile == "-":
            print(text)
        else:
            with open(args.profile, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")

    if not args.out and not args.profile:
        print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
