#!/usr/bin/env python3
"""Map a design system onto a PlotSet template schema and emit a ready-to-send config.

Why this is a script and not a paste-in table: PlotSet field names are not stable.
The same visual role is called `header.titleStyle.fontFamily` on one template
revision and `fonts.header.title_font_family` on another, and a key that does not
exist in the template's schema is stored and silently ignored -- you get no error,
just a chart that looks untouched. So the only safe way to style a chart is to read
that template's own schema and write back the keys it actually has. This script does
that by resolving each schema key to a visual role (ink, grid, rule, display font,
axis-label size, ...) and filling it from the chosen system's tokens.

    # static chart -- save get_chart_schema output first
    apply_design.py --schema schema.json --system ledger --value-axis x --out config.json

    # video chart -- save get_video_template_schema output first
    apply_design.py --schema vschema.json --system broadcast \
        --series "Arsenal,Liverpool,Chelsea" --out layer-config.json

Static output is a FLAT map of dotted keys; video output is a NESTED object. That
asymmetry is real -- see references/static-charts.md and references/video-charts.md.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYSTEMS = os.path.join(HERE, "..", "references", "design-systems.json")


def load_systems(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def interpolate(stops, count):
    """Stretch a short ramp to exactly `count` colours by walking its stops.

    Needed because a value-ordered bar chart wants one colour per bar, and
    `palette.type: "spectrum"` does NOT do this for you -- on a bar chart it
    paints every bar the same single step.
    """
    if count <= 1:
        return [stops[0]]
    out = []
    span = len(stops) - 1
    for i in range(count):
        pos = i / (count - 1) * span
        lo = min(int(pos), span - 1)
        t = pos - lo
        a, b = _hex_to_rgb(stops[lo]), _hex_to_rgb(stops[lo + 1])
        out.append(_rgb_to_hex([a[j] + (b[j] - a[j]) * t for j in range(3)]))
    return out


def pick_ramp(system, kind, count):
    key = {"categorical": "ramp", "sequential": "sequential", "diverging": "diverging"}[kind]
    ramp = system.get(key, system["ramp"])
    if kind == "categorical":
        if count <= len(ramp):
            return ramp[:count]
        return [ramp[i % len(ramp)] for i in range(count)]
    # Continuous ramps must span the full count, not repeat or truncate.
    return interpolate(ramp, count)


# --------------------------------------------------------------------------
# static charts: flat dotted keys
# --------------------------------------------------------------------------

def color_role(key):
    k = key.lower()
    if k == "palette.bg_color":
        return "bg"
    if "gridlines" in k or ".grid." in k:
        return "grid"
    if "axisline" in k or "tickline" in k:
        return "rule"
    if "backgroundcolor" in k or "backgroundstyle.color" in k:
        return "surface"
    if "border_color" in k or "bordercolor" in k or "borderlinecolor" in k:
        return "rule"
    if "source" in k or "note" in k:
        return "muted"
    if "subtitle" in k:
        return "body"
    if k.startswith("header.title"):
        return "ink"
    if k.startswith("header.text"):
        return "body"
    if k.startswith("tooltip.text"):
        return "ink"
    if "labelscolor" in k or "labelcustomcolor" in k or k.endswith("label.color"):
        return "body"
    if k.endswith("titlecolor"):
        return "body"
    if ".value.color" in k or k.endswith("value.color"):
        return "ink"
    return "body"


def size_role(key):
    k = key.lower()
    if k.startswith("header.title"):
        return "title"
    if k.startswith("header.subtitle") or k.startswith("header.text"):
        return "subtitle"
    if k.startswith("footer"):
        return "footer"
    if "xaxis" in k or "yaxis" in k:
        return "axisTitle" if "title" in k else "axisLabel"
    if k.startswith("legend"):
        return "legend"
    if k.startswith("tooltip"):
        return "tooltip"
    if "value" in k or "label" in k:
        return "value"
    return "axisLabel"


def is_font_family(key):
    k = key.lower()
    return ("fontfamily" in k or "font_family" in k) and not k.endswith("_url")


def is_font_size(key, default):
    k = key.lower()
    if not isinstance(default, (int, float)) or isinstance(default, bool):
        return False
    return "fontsizevalue" in k or "font_size" in k or "customfontsize" in k or k.endswith("fontsize")


def build_static(schema, system, urls, args):
    settings = schema.get("settings", schema)
    if isinstance(settings, list):
        raise SystemExit("schema looks like raw=true output; re-fetch get_chart_schema without raw")

    display = system["fonts"]["display"]
    body_font = system["fonts"]["body"]
    scale = {k: max(8, int(round(v * args.canvas / 1200.0))) for k, v in system["scale"].items()}
    shape = system["shape"]
    out, warnings, legacy_size_gates = {}, [], []

    value_axis = args.value_axis
    other_axis = "yAxis" if value_axis == "xAxis" else "xAxis"
    seq = system["sequential"]
    div = system["diverging"]
    is_map = "mapType.colorScaleType" in settings

    for key, default in settings.items():
        k = key.lower()

        # -- palette -------------------------------------------------------
        if key == "palette.colors":
            if args.palette == "categorical":
                count = len(default) if isinstance(default, list) and default else 9
            elif args.categories:
                count = args.categories
            else:
                count = len(default) if isinstance(default, list) and default else 9
                warnings.append(
                    "continuous palette without --categories: emitting a 9-step ramp. Pass the row "
                    "count (from profile.json) so every bar gets its own step, or the ramp will "
                    "repeat across the bars")
            if args.palette == "categorical":
                out[key] = pick_ramp(system, args.palette, count)
            else:
                # The lightest sequential stop is an almost-white anchor meant for
                # map fills, where it reads against a neutral basemap. As a bar it
                # disappears into a light chart ground, so marks start one stop in.
                stops = system["sequential" if args.palette == "sequential" else "diverging"]
                stops = stops[1:] if len(stops) > 3 else stops
                out[key] = interpolate(stops, count)
            continue
        if key == "palette.type":
            # "spectrum" is a MAP concept. On a bar/line chart it collapses every
            # mark to one step of the ramp rather than graduating across them, so
            # a value-ordered bar chart stays "multi" with explicit per-bar colours.
            out[key] = "multi"
            continue
        if key.startswith("palette.color__"):
            # Panel-generated per-swatch overrides shadow palette.colors when present.
            idx = key.rsplit("_", 1)[-1]
            if idx.isdigit():
                ramp = pick_ramp(system, args.palette, int(idx) + 1)
                out[key] = ramp[int(idx)]
            continue

        # -- map templates (category 7) use `colors.*` / `mapType.*` and have
        # no palette.* whatsoever; a map styled through palette keys stays the
        # stock blue no matter what you write.
        if key == "colors.backgroundColor":
            out[key] = system["bg"]
            continue
        if key == "colors.colorSeq":
            out[key] = f"{seq[0]},{seq[-1]}"
            continue
        if key == "colors.colorDiv":
            out[key] = f"{div[0]},{div[-1]},{div[len(div) // 2]}"
            continue
        if key == "colors.colorMin":
            out[key] = div[0] if args.palette == "diverging" else seq[0]
            continue
        if key == "colors.colorMid":
            out[key] = div[len(div) // 2] if args.palette == "diverging" else seq[len(seq) // 2]
            continue
        if key == "colors.colorMax":
            out[key] = div[-1] if args.palette == "diverging" else seq[-1]
            continue
        if key == "colors.dynamicColorsCategorical":
            count = len(default) if isinstance(default, list) and default else 8
            out[key] = pick_ramp(system, "categorical", count)
            continue
        if key == "mapType.colorScaleType":
            out[key] = "diverging" if args.palette == "diverging" else "sequential"
            continue
        if key == "borders.stroke":
            out[key] = system["rule"]
            continue
        if key == "missingValues.defaultAreaColor":
            out[key] = system["grid"]
            continue

        # -- typography ----------------------------------------------------
        if is_font_family(key):
            role = display if key.startswith("header.title") and "subtitle" not in k else body_font
            out[key] = role["static"]
            url_key = key + "_url"
            if url_key in settings:
                url = urls.get(role["static"])
                if url:
                    out[url_key] = url
                else:
                    warnings.append(f"no font URL known for {role['static']!r}; left {url_key} alone")
            continue
        if key.endswith("_url"):
            continue  # handled alongside its family key
        if is_font_size(key, default):
            out[key] = scale[size_role(key)]
            # Older revisions gate the numeric size behind a mode enum
            # ("small"/"custom"/"other"). Guessing wrong makes the size a no-op.
            for gate in (key.rsplit(".", 1)[0] + "_size", key.replace("Value", ""),
                         key.replace("CustomFontSize", "FontSizer")):
                if gate != key and gate in settings and isinstance(settings[gate], str):
                    legacy_size_gates.append(gate)
            continue
        if k.endswith("isbold"):
            if key.startswith("header.title") and "subtitle" not in k:
                out[key] = display.get("bold", True)
            elif "title" in k:
                out[key] = False
            continue

        # -- colour --------------------------------------------------------
        if "color" in k and not k.endswith("colortype"):
            role = color_role(key)
            if role:
                out[key] = system[role]
            continue

        # -- structure -----------------------------------------------------
        if k.endswith("gridlines") and isinstance(default, bool):
            axis = "xAxis" if key.startswith("xAxis") else "yAxis"
            policy = system["gridPolicy"]
            out[key] = (policy == "both") or (policy == "value-axis-only" and axis == value_axis)
            continue
        if k.endswith("gridlineswidth"):
            out[key] = shape["gridWidth"]
            continue
        if k.endswith("axislinewidth"):
            out[key] = shape["ruleWidth"]
            continue
        if key in ("bar.radius", "series.bar.barradius", "bar.barradius", "column.radius"):
            out[key] = shape["barRadius"]
            continue
        if k.endswith("swatchescornerradius"):
            out[key] = shape["swatchRadius"]
            continue
        if key == "tooltip.radius":
            out[key] = shape["tooltipRadius"]
            continue
        if key in ("bar.opacity", "series.bar.opacity"):
            out[key] = shape["barOpacity"]
            continue
        if key in ("bar.widthValue", "series.bar.barWidthValue"):
            out[key] = shape["barWidth"]
            continue
        if key in ("bar.value.show", "column.label.show", "series.label.show", "bar.valueShow"):
            out[key] = system["valueLabels"]
            continue

    # -- number formatting, driven by the data itself ----------------------
    # Raw 7-digit tick labels force a 45-degree rotation and read as noise;
    # abbreviating them ("1.5M") lets the labels sit flat and legible.
    fmt_default = str(settings.get("numberformatter.type", ""))
    if "numberformatter.type" in settings and "0" in fmt_default:
        if args.percent:
            out["numberformatter.type"] = "0.[0]"
            if "numberformatter.suffix" in settings:
                out["numberformatter.suffix"] = "%"
        elif args.max_value is not None and abs(args.max_value) >= 10000:
            out["numberformatter.type"] = "0.[0]a"
        elif args.max_value is not None and abs(args.max_value) >= 100:
            out["numberformatter.type"] = "0,0"
        else:
            out["numberformatter.type"] = "0.[00]"
    elif args.percent and "numberformatter.suffix" in settings:
        out["numberformatter.suffix"] = "%"

    # A share-of-total axis must run to 100, not to the largest observed value.
    # Letting it auto-fit makes a 89%-vs-28% gap look like the whole range and
    # quietly exaggerates every comparison on the chart.
    if args.percent and args.axis_to_100:
        if f"{value_axis}.minMax" in settings:
            out[f"{value_axis}.minMax"] = "custom"
            out[f"{value_axis}.minValue"] = 0
            out[f"{value_axis}.maxValue"] = 100
    for axis in ("xAxis", "yAxis"):
        rot = f"{axis}.labelsRotate"
        if rot in settings and axis == value_axis:
            out[rot] = 0

    # Value labels sit inside the bar by default, which collides with the axis
    # on negative or very short bars.
    if args.has_negatives:
        # The enum here is "in" / "after" -- NOT "out". An invalid enum value is
        # stored and ignored exactly like an unknown key, so the negative-label
        # fix would silently never happen.
        # A negative bar is short; its length alone does not communicate the
        # magnitude, so the number has to be printed whatever the system's default
        # says, and it has to sit outside the bar to clear the axis.
        for show_key in ("bar.value.show", "column.label.show", "series.label.show"):
            if show_key in settings:
                out[show_key] = True
        if "bar.value.after" in settings:
            out["bar.value.after"] = "after"
        if "column.label.position" in settings:
            out["column.label.position"] = "end"

    # -- optional copy ------------------------------------------------------
    for field, value in (("header.title", args.title), ("header.subtitle", args.subtitle),
                         ("footer.source_label", args.source)):
        if value and field in settings:
            out[field] = value

    if other_axis + ".gridLines" not in settings and system["gridPolicy"] != "both":
        warnings.append("template exposes no gridLines switch; grid policy not applied")
    if is_map:
        warnings.append(
            "map template: auto-binding is skipped (bindingsGroup is null), so set the binding "
            "yourself with set_chart_binding, and make sure every label matches a region name in "
            "this map or those rows vanish silently")
    if legacy_size_gates:
        warnings.append(
            "this template revision gates font sizes behind mode fields "
            f"({', '.join(sorted(set(legacy_size_gates)))}); fetch get_chart_schema with raw=true, "
            "read their options, and set them to the custom option or the sizes will not apply")
    return out, warnings


# --------------------------------------------------------------------------
# video charts: nested objects
# --------------------------------------------------------------------------

def video_color_role(path):
    p = path.lower()
    if ".grid." in p:
        return "grid"
    if ".line." in p or ".tickline." in p or ".zeroline." in p:
        return "rule"
    if p.startswith("title."):
        return "ink"
    if p.startswith("subtitle."):
        return "body"
    if p.startswith("footer."):
        return "muted"
    if p.endswith("label.color") or p.endswith("title.color"):
        return "body"
    return "ink"


def video_size_role(path):
    p = path.lower()
    if p.startswith("title."):
        return "title"
    if p.startswith("subtitle."):
        return "subtitle"
    if p.startswith("footer."):
        return "footer"
    if "axis" in p:
        return "axisTitle" if ".title." in p else "axisLabel"
    if "legend" in p:
        return "legend"
    return "value"


def build_video(schema, system, args):
    defaults = schema.get("defaults")
    if not isinstance(defaults, dict):
        raise SystemExit("video schema has no `defaults` object")

    display = system["fonts"]["display"]
    body_font = system["fonts"]["body"]
    scale = system["scale"]
    shape = system["shape"]
    mult = system.get("videoScaleMultiplier", 2.2)
    out, warnings = {}, []

    def put(path, value):
        node = out
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def walk(node, prefix=""):
        for key, value in node.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict):
                walk(value, path + ".")
                continue
            leaf = key
            if leaf == "fontFamily":
                role = display if path.startswith("title.") else body_font
                put(path, role["video"])
            elif leaf == "fontWeight":
                bold = path.startswith("title.") or (path.startswith("subtitle.") and display.get("bold"))
                put(path, "700" if bold else "400")
            elif leaf == "fontSizeValue":
                put(path, int(round(scale[video_size_role(path)] * mult)))
            elif leaf == "color":
                put(path, system[video_color_role(path)])
            elif leaf == "stroke":
                put(path, system[video_color_role(path)])
            elif leaf == "width" and (".grid." in path or ".line." in path or ".tickLine." in path
                                      or ".zeroLine." in path):
                base = shape["gridWidth"] if ".grid." in path else shape["ruleWidth"]
                put(path, max(1, int(round(base * (3 if ".grid." in path else 4)))))
            elif leaf == "show" and ".grid." in path:
                policy = system["gridPolicy"]
                axis_is_value = path.startswith(args.value_axis[0].lower() + args.value_axis[1:])
                put(path, (policy == "both") or (policy == "value-axis-only" and axis_is_value))
            elif leaf == "opacity" and path.startswith("bar."):
                put(path, shape["barOpacity"])
            elif leaf == "valueShow":
                put(path, system["valueLabels"])

    walk(defaults)

    series = [s.strip() for s in (args.series or "").split(",") if s.strip()]
    ramp = pick_ramp(system, args.palette, max(len(series), 1))
    put("palette.bg_color", system["bg"])
    if series:
        put("palette.data_color", [{"key": name, "value": ramp[i]} for i, name in enumerate(series)])
    else:
        put("palette.data_color", [])
        warnings.append(
            "no --series given, so palette.data_color is empty and EVERY SERIES WILL RENDER FLAT BLACK. "
            "Pass the CSV's series column names (the header row minus the date column).")

    if args.title:
        put("title.text", args.title)
    if args.subtitle:
        put("subtitle.text", args.subtitle)
    if args.source:
        put("footer.source.text", args.source)
    return out, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", required=True, help="saved get_chart_schema / get_video_template_schema JSON")
    ap.add_argument("--system", required=True, help="design system name (see --list)")
    ap.add_argument("--systems-file", default=DEFAULT_SYSTEMS)
    ap.add_argument("--medium", choices=["static", "video", "auto"], default="auto")
    ap.add_argument("--palette", choices=["categorical", "sequential", "diverging"], default="categorical")
    ap.add_argument("--value-axis", default="xAxis", choices=["xAxis", "yAxis"],
                    help="which axis carries the measure (x for horizontal bars, y for columns/lines)")
    ap.add_argument("--series", help="comma-separated series names, required for video palettes")
    ap.add_argument("--categories", type=int,
                    help="number of categories/bars; with a sequential or diverging palette this "
                         "emits exactly one interpolated colour per bar")
    ap.add_argument("--canvas", type=int, default=1200,
                    help="export width in px; type sizes are calibrated for 1200 and scale from it")
    ap.add_argument("--max-value", type=float,
                    help="largest absolute value in the data (from profile_data.py) -- picks the number format")
    ap.add_argument("--percent", action="store_true", help="values are percentages")
    ap.add_argument("--no-axis-to-100", dest="axis_to_100", action="store_false", default=True,
                    help="with --percent, do NOT pin the value axis to 0-100 (use when the values "
                         "are rates or changes rather than shares of a whole)")
    ap.add_argument("--has-negatives", action="store_true",
                    help="data contains negative values -- moves value labels outside the bar")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--source")
    ap.add_argument("--out", help="write config JSON here ('-' or omitted = stdout)")
    ap.add_argument("--list", action="store_true", help="list design systems and exit")
    args = ap.parse_args()

    catalogue = load_systems(args.systems_file)
    if args.list:
        for name, sysdef in catalogue["systems"].items():
            print(f"{name:<11} {sysdef['mode']:<5} {sysdef['title']:<12} {sysdef['useWhen']}")
        return

    if args.system not in catalogue["systems"]:
        raise SystemExit(f"unknown system {args.system!r}; known: {', '.join(catalogue['systems'])}")
    system = catalogue["systems"][args.system]

    with open(args.schema, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    medium = args.medium
    if medium == "auto":
        medium = "video" if "defaults" in schema and "configSchema" in schema else "static"

    if medium == "static":
        config, warnings = build_static(schema, system, catalogue["fontUrls"], args)
    else:
        config, warnings = build_video(schema, system, args)

    text = json.dumps(config, indent=2)
    if args.out and args.out != "-":
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {len(config)} top-level keys to {args.out}", file=sys.stderr)
    else:
        print(text)

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if system.get("notes"):
        print(f"note: {system['notes']}", file=sys.stderr)


if __name__ == "__main__":
    main()
