# Static charts

## The tools, in the order you use them

| Tool | Notes |
|---|---|
| `list_templates` | 434 templates; filter by `category` to keep the response small |
| `get_chart_schema` | the ground truth for one template's config keys and binding slots |
| `create_chart` | one-shot: project + title + CSV + auto-binding + initial config |
| `set_chart_data` | replace the dataset and re-run auto-binding |
| `set_chart_config` | deep-merges by default; `replace: true` overwrites wholesale |
| `set_chart_binding` | replaces bindings wholesale, no merge |
| `export_chart` | PNG (inline image), SVG, or raw embed HTML |
| `get_or_create_embed` | idempotent; returns embed + share URLs |

Template categories: 1 misc/specialty, 2 bar & column, 3 line & area, 4 pie &
donut, 7 maps, 8 hierarchy, 9 flow, 10 distribution, 16 animated.

## Config is flat, and revision-specific

`get_chart_schema` returns `settings` as a flat map of dotted key → default.
Those keys are exactly what the stored config must use. Nested objects are stored
and ignored.

Key names track the template *revision*, not just the template. Two real examples
of the same visual role:

| Role | Current revision | Older revision |
|---|---|---|
| title font | `header.titleStyle.fontFamily` | `fonts.header.title_font_family` |
| title size | `header.titleStyle.fontSizeValue` | `header.title_font_size` (+ `header.title_size` mode gate) |
| axis label font | `xAxis.labelFont.fontFamily` | `fonts.xAxis.numbersFontFamily` |
| bar radius | `bar.radius` | `series.bar.barradius` |

Older revisions gate numeric font sizes behind a mode enum — `header.title_size`
must be `"other"`, `xAxis.labelsFontSize` must be `"custom"`, and the option name
differs per field. If `apply_design.py` warns about legacy size gates, call
`get_chart_schema` with `raw: true` and read the `options` array for those
components before setting sizes.

This is why `apply_design.py` writes only keys the fetched schema contains: a key
the template does not know is stored silently and does nothing.

## Bindings

`bindings` in the schema lists the slots — for a bar chart: `labels` (required),
`values` (required, numeric), `filter` (optional colour/grouping), `images`
(optional). Each has a `default` column letter.

`create_chart` and `set_chart_data` auto-bind by column *type and position*, which
is right most of the time. It fails in two ways worth checking:

- **Templates with no `bindingsGroup`** (tables, some specialty charts) cannot be
  auto-bound at all. The `warnings` array says so. Build the binding yourself and
  call `set_chart_binding`.
- **Wrong column picked** when several numeric columns are candidates. Fix by
  passing the full binding array back with the `value` field set to the column
  letter you want:

```json
[{"field":"labels","value":"A","required":true},
 {"field":"values","value":"C","required":true,"type":"number"}]
```

Column letters are spreadsheet-style over the *cleaned* CSV, so run
`profile_data.py` first and count from its header, not the original file.

## Palette keys

- `palette.colors` — the array the chart draws from.
- `palette.type` — `multi`, `spectrum` or `mono`. **`spectrum` is a trap on
  bar and line charts.** It does not graduate colour across the marks; verified
  behaviour is that every bar comes out the same single step of the ramp. To get
  a value-ordered chart, leave `palette.type` at `multi` and put one colour per
  bar into `palette.colors` — `apply_design.py --palette sequential --categories N`
  interpolates exactly N steps for you. Maps are the different case: they have no
  `palette.type` at all and use `mapType.colorScaleType` instead.
- Sequential ramps for **marks** start one stop in from the lightest anchor. That
  near-white first stop exists for map fills, where it reads against a neutral
  basemap; as a bar on a light chart ground it is invisible.

**A value-ordered bar chart needs no colour binding.** Verified: `palette.type:
"multi"` plus sixteen explicit hexes in `palette.colors` renders sixteen bars in
a clean dark-to-light ramp with only `labels` and `values` bound. If you see every
bar come out the same colour, the cause is `palette.type: "spectrum"`, not a
missing binding — do not "fix" it by duplicating a column into the `filter` slot.
- `palette.bg_color` — the chart ground.
- `palette.color__multi_N` — per-swatch overrides the panel writes when a user
  picks colours by hand. They shadow `palette.colors` when present. They are not
  in a fresh template's schema, so `apply_design.py` only fills them on charts
  that already have them.

## Maps are a different colour family

Category-7 templates (~355 of the 434) have **no `palette.*` keys at all**. Styling
a map through `palette.colors` leaves it stock blue and reports no error. Their
keys instead:

| Key | Holds |
|---|---|
| `colors.backgroundColor` | the chart ground — not `palette.bg_color` |
| `mapType.colorScaleType` | `sequential`, `diverging` or `categorical` |
| `colors.colorSeq` | a **comma-joined string** of two stops: `"#D7E9FC,#0C5097"` |
| `colors.colorDiv` | three stops, ordered min,max,mid |
| `colors.colorMin` / `colorMid` / `colorMax` | individual continuous stops |
| `colors.dynamicColorsCategorical` | array, only used when the scale is categorical |
| `borders.stroke` / `borders.strokeWidth` | region outlines |
| `missingValues.defaultAreaColor` | regions with no matching data row |
| `areaLabel.*` | in-map region labels |

`apply_design.py` detects maps by the presence of `mapType.colorScaleType` and
fills all of the above from the system's `sequential` / `diverging` ramps.

Two further map-only facts:

- **`bindingsGroup` is `null`, so auto-binding is skipped entirely.** The
  `warnings` array says so. Call `set_chart_binding` yourself.
- **Region names must match the map's own names exactly.** Rows that do not match
  are dropped silently — no warning, just missing regions painted in
  `missingValues.defaultAreaColor`. Export the PNG and count the filled regions
  against your row count.
- Map templates often use a different number-format vocabulary (`"123a"` rather
  than numeral.js `"0.[0]a"`). `apply_design.py` only rewrites
  `numberformatter.type` when the template's default looks like numeral.js.

## Exports and publishing

`export_chart` renders at 1200×675 unless you pass `width`/`height`. The bundled
type scales are calibrated for 1200 wide — pass `--canvas <width>` to
`apply_design.py` for anything else.

**Two text systems.** Header/subtitle/footer are absolute-pixel HTML. Axis,
legend and value-label text lives in the chart's SVG and scales with the
container, so its apparent size depends on both the container dimensions and how
dense the chart is. A number that looks small in a wide 1200x675 export is often
correct in a taller 800px embed.

Verify on the delivery surface. Tuning sizes against the export PNG and shipping
an embed is how you get labels that swallow the canvas.

Open the `embedUrl` returned by any mutating call in the browser pane —
`preview_start {url}` the first time, `navigate {url}` after — then **wait 3–4
seconds before screenshotting**, because the embed loads its template bundle and
dataset asynchronously and screenshots blank white until they arrive. Use
`resize_window {width: 700, height: 900}` to check a blog-column width; the SVG
genuinely rescales, so what you see is what the reader sees. Republishing takes
effect immediately, with no caching, so re-navigating after a fix confirms it.

`export_chart` hands the PNG back **inline for you to read** — there is no public
image URL and no file written to disk. That is fine for verification, which is
what it is for. When the user wants an image file, point them at the panel URL's
download, or at the embed URL; do not spend calls probing for a PNG endpoint that
does not exist.

**Every mutating tool publishes the chart.** `create_chart`, `set_chart_data`,
`set_chart_config`, `set_chart_title` and `export_chart` all ensure a public embed
exists as a side effect. There is no private render path. When the data is
sensitive, say this before the first call, not after.

## Things that look right in JSON and wrong in the PNG

Verified against real exports:

- **Value labels going dark-on-dark.** Leave `bar.value.colorType` at `auto`;
  the renderer picks per-bar contrast. Forcing `custom` breaks half the bars.
- **Rotated seven-digit ticks.** `xAxis.labelsRotate` defaults to `-45`. Set
  `numberformatter.type` to `"0.[0]a"` for abbreviated values (`1.5M`) and the
  rotation to `0`. The number formatter is numeral.js syntax: `0,0` for grouped
  thousands, `0.[0]a` abbreviated, `0.[00]` for small values, with
  `numberformatter.prefix` / `suffix` for units.
- **A negative bar's label colliding with the axis.** Set `bar.value.after` to
  `"out"` when the data contains negatives.
- **Axis labels that look too small in the export.** Before raising them, check
  the embed — the SVG scaling above means they are frequently already correct.
  Raising a label past the title size is the tell that you are compensating for
  scaling rather than fixing type.
- **`bar.widthValue` is a percentage of the available band, not pixels.** Values
  in the 55–80 range give solid bars; treating it as a pixel width produces
  hairlines.
- **Long category names clipped** on column charts. Use `barchart-d3` (horizontal)
  when the categories are words.

## Restyling an existing chart

`get_chart` returns the current config, binding, dataset URL and
`templateRevision`. To restyle: fetch the schema for that template, run
`apply_design.py`, and `set_chart_config` (merge, not replace — replace drops
every key the user set by hand in the panel).

Note `latestTemplateRevision` in the response. If it is ahead of
`templateRevision`, the chart is on an older field-name family; the schema you
fetch describes the *latest* revision, so cross-check a few keys against the
chart's own config before writing.
