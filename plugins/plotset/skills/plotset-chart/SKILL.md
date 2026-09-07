---
name: plotset-chart
description: Build, restyle and export charts and animated data videos on PlotSet through the PlotSet MCP server. Use whenever someone wants a chart, graph, plot, map or data video made from a spreadsheet, CSV, pasted numbers or query results — bar, column, line, area, pie, donut, treemap, scatter, sankey, choropleth, bar-chart race — or wants an existing PlotSet chart restyled, rebranded, recoloured, given a different palette or design system, embedded or exported to PNG/SVG. Covers cleaning messy data first, choosing the chart type and the visual design from what the data actually is, and applying one of ten built-in design systems. Reach for this even when the request is only "visualise this", "make this look better", "turn this into a video", or mentions PlotSet without saying the word chart.
---

# PlotSet charts

You are making something someone will publish. A chart that renders is not the
same as a chart that reads, and PlotSet will happily accept a config that does
nothing at all — so the work is: clean the data, let the data choose the chart,
dress it in a system rather than in ad-hoc colours, and **look at the result**
before you say it is done.

Everything runs through the PlotSet MCP tools (`create_chart`, `set_chart_config`,
`export_chart`, `preview_video_frame`, …). Two bundled scripts do the parts that
are otherwise re-invented every single time.

## The one thing that will bite you

PlotSet stores chart config as a **flat map of dotted keys** — `"palette.colors"`,
`"header.titleStyle.fontFamily"` — not as nested objects. Writing
`{"palette": {"colors": [...]}}` is stored happily and ignored completely: no
error, no warning, an unchanged chart. Worse, the key names differ between
template *revisions* (an older bar chart uses `fonts.header.title_font_family`
where the current one uses `header.titleStyle.fontFamily`).

So: never write a static config from memory. Read that template's schema, and let
`apply_design.py` write back only the keys that schema actually contains.

Video config is the opposite — genuinely nested. Details in
[references/video-charts.md](references/video-charts.md).

## Step 1 — normalize and profile the data

Do this before anything else, even when the data looks clean. Spreadsheets carry
things that bind wrong rather than fail loudly: blank or duplicate header cells,
`$1,234`, `(500)` meaning −500, and `03/04/2024` meaning the 3rd of April.

```bash
python3 scripts/profile_data.py input.csv --out clean.csv --profile profile.json
```

The profile is not bookkeeping — it is the evidence for every choice that follows.
Read it. It tells you the shape (`wide-time-series`, `single-series-categorical`,
`hierarchical-or-grouped`, …), which columns are dates/numbers/categories, the
category cardinality, whether the data is part-to-whole, whether it is
`videoReady`, and `designSystemHints` — design systems ranked by subject-matter
words found in the headers and category values.

Tell the user what you changed. "Normalized 4 day-first dates and stripped
currency formatting from Revenue" is information they need; silent cleaning of
their data is not.

For a bar-chart race from long-format data (`date, series, value`), add `--pivot`
— video templates need one date column and one column per series, and unpivoted
data renders as a single bar that never moves.

## Step 2 — let the data choose the chart

`list_templates` returns 434 templates. Narrow with the profile's `shape` first,
then the question the user is asking.

| Profile shape | Reach for | Slugs |
|---|---|---|
| `single-series-categorical`, ≤ 12 categories | ranked bar | `barchart-d3`, `columnchart-d3` |
| `single-series-categorical`, > 25 categories | treemap or packed circles | `simple-treemap`, `circle-packing-2` |
| `partToWholeCandidate: true` (2–8 parts summing to a whole) | donut, or a stacked bar if you also want the total | `donut-chart`, `stacked-barchart-percentage-d3` |
| `wide-time-series` | line, or area when the magnitude matters | `line-chart2`, `area-charttest` |
| `long-time-series` | bump chart for rank, grouped bars for level | `bump-chart`, `grouped-columnchart-d3` |
| `multi-series-categorical` | grouped when comparing series, stacked when comparing totals | `grouped-barchart-d3`, `stacked-barchart-d3` |
| `hierarchical-or-grouped`, 2+ category columns | treemap with category, sunburst | `treemap-with-category`, `sunburst` |
| two numeric columns, looking for correlation | scatter or bubble | `scatter-plot-with-groups`, `bubble-chart-new` |
| flows between categories | sankey, chord | `sankey`, `chord` |
| distribution of one measure | histogram, box, violin, ridge | `histogram`, `boxplot-horizontal`, `ridge-plot` |
| `geographic: true` | choropleth for the right geography | `world`, `usa-counties`, `europe`, + ~350 more |

Two judgement calls worth making deliberately:

- **Pie charts lose to bars for anything but a genuine part-to-whole with few
  slices.** If cardinality is above 8, or the values do not sum to a meaningful
  total, a ranked bar answers the question and a pie hides it.
- **Horizontal bars beat columns whenever the category labels are words.**
  "North America" fits on a horizontal bar and gets rotated 45° on a column
  chart. Use `columnchart-d3` for time along the x-axis, `barchart-d3` for
  ranked names.

Maps need three extra things. Match the geography exactly — the slug decides which
regions exist, and rows whose names do not match one are dropped **silently**.
They have no `palette.*` keys at all (colours live under `colors.colorSeq` /
`mapType.colorScaleType`), so pass `--palette sequential`. And their
`bindingsGroup` is `null`, so auto-binding is skipped and you must call
`set_chart_binding` yourself. Details in
[references/static-charts.md](references/static-charts.md).

## Step 3 — choose the design system

Ten systems ship with this skill, each grounded in a real visual vernacular
rather than assembled from chart defaults. Full descriptions, palettes and
rationale: [references/design-systems.md](references/design-systems.md).

| System | Mode | Reach for it when |
|---|---|---|
| `ledger` | light | money — revenue, cost, budget, P&L, unit economics |
| `bulletin` | light | public-interest statistics for a general audience |
| `broadcast` | dark | competition and ranking; the default for race videos |
| `fieldnotes` | light | climate, ecology, agriculture, energy, long research |
| `terminal` | dark | engineering telemetry for a technical reader |
| `atlas` | light | anything geographic, and single-measure sequential ramps |
| `editorial` | light | journalism and analysis where the chart makes an argument |
| `playbook` | light | education, kids, consumer, community |
| `clinical` | light | medicine, QC, thresholds — where some values are *bad* |
| `nocturne` | dark | keynote, launch, social and vertical video |

`profile.json`'s `designSystemHints` ranks these by words it actually found in the
data. Treat it as evidence, not a verdict: it sees column names, not the room the
chart is going into. A revenue chart destined for a keynote slide is `nocturne`,
not `ledger`, and the hint cannot know that. Where the user tells you the venue,
the venue wins.

Then adapt. The system is a starting point, not a skin:

- **Order the palette to the argument.** The ramp is a list, not an assignment.
  Give position 0 to the series the chart is about; push context series to the
  muted end. A chart where the point is coloured the same as everything else has
  no point.
- **`clinical`'s red at index 1 is a semantic slot**, not the second-favourite
  colour. If nothing in the data is an exception, skip it.
- **Sequential, not categorical, for one continuous measure** — a ranking of one
  quantity, or any map. Pass `--palette sequential --categories <row count>` so
  every bar gets its own step; `--palette diverging` when there is a meaningful
  midpoint (change vs. last year, over/under target). Do **not** set
  `palette.type: "spectrum"` to get this on a bar chart — it paints every bar the
  same single step. Maps are the exception and have their own colour family.

When the user wants something these ten do not cover — a company brand, a
specific publication's look, an unusual mood — invoke the **`frontend-design`**
skill and build a token set for that brief instead, then express it in the same
roles (`bg / surface / ink / body / muted / rule / grid / ramp / display / body
font / scale / shape`). You can hand it to `apply_design.py` by adding it to a
copy of `references/design-systems.json` and pointing `--systems-file` at it.

## Step 4 — build it

**Static charts.** Save the schema, generate the config, create the chart, then
open the resulting `embedUrl` in the browser (Step 5) before you report back:

```bash
# 1. save get_chart_schema(templateRef) output to <slug>-schema.json (NOT raw=true).
#    Name the file after the template: styling one chart with another template's
#    schema produces a plausible-looking config full of keys the chart ignores.
python3 scripts/apply_design.py --schema schema.json --system ledger \
  --value-axis xAxis --canvas 1200 \
  --max-value 1502900 --has-negatives \
  --title "Q4 revenue by region" --source "Finance ops" \
  --out config.json
```

`--value-axis` is which axis carries the measure — `xAxis` for horizontal bars,
`yAxis` for columns and lines — and it decides which gridlines survive.
`--max-value`, `--percent` and `--has-negatives` come straight out of
`profile.json`; they pick the number format (`1.5M` instead of `1500000`,
which is the difference between flat legible ticks and rotated noise) and move
value labels outside the bar where a negative would otherwise collide with the
axis. Read the stderr warnings — they flag legacy templates that gate font sizes
behind a mode field.

Then `create_chart` with the template, the cleaned CSV and that config. More on
bindings, categories and exports: [references/static-charts.md](references/static-charts.md).

**Video charts.** Same script, nested output, plus one field you must not forget:

```bash
python3 scripts/apply_design.py --schema vschema.json --system broadcast \
  --series "Arsenal,Liverpool,Chelsea" --title "Premier League 2024" \
  --out layer-config.json
```

`--series` is the CSV header minus the date column. Without it `palette.data_color`
is empty and **every series renders flat black** — the renderer assigns no colours
on your behalf. Full layer/timing/render flow:
[references/video-charts.md](references/video-charts.md).

## Step 5 — look at it

Every mutating chart tool returns a rendered PNG. `preview_video_frame` returns a
JPEG and is free. **Read the image before you describe the chart to the user.**

This is not ceremony. In testing, a config that validated perfectly still produced
axis labels too small to read at export size, a value label colliding with the
axis on the one negative bar, and 45°-rotated seven-digit ticks. None of that is
visible in JSON. All of it is obvious in the PNG.

What to check, in order: is any text clipped or overlapping; can you read the
axis labels at 100%; does the colour ordering match the argument; is the value
label legible against its bar; do the number formats look like something a person
would write.

**Two text systems, and they do not scale together.** The header, subtitle and
footer are absolute-pixel HTML. Everything inside the plot — axis labels, legend,
value labels — lives in an SVG that scales to its container. The same
`fontSizeValue` therefore renders at different apparent sizes on different
surfaces: axis text that looks too small in a wide 1200x675 export can be exactly
right in a taller 800px embed, and text sized to fix the export will swamp the
embed. Denser charts shrink it further, because more bars means a smaller scale
factor.

The practical consequence: **verify on the surface you are actually delivering
to.** The export PNG is a convenient inline check, not the artifact people
receive. The bundled scales are tuned to render correctly in a typical embed.

This is the worst failure this skill has produced in testing: a run judged the
export too small, tripled axis and legend sizes to 50-60px, produced a
respectable-looking export, and shipped an embed whose labels swallowed the
canvas and squeezed the plot to a sliver. The export looked fine the whole time.

### Open the embed in a browser

Every mutating call returns an `embedUrl`, and the chart is already public by
then, so viewing it costs nothing and hides nothing. **Open it.** This is the
only way to see what the user will actually get.

```
preview_start  { url: "<embedUrl>" }        # first time — opens the browser pane
navigate       { url: "<embedUrl>" }        # subsequently, or to switch charts
computer       { action: "wait", duration: 4 }
computer       { action: "screenshot" }
```

The wait is not optional. The embed fetches its template bundle and dataset after
the page loads, so a screenshot taken immediately comes back **blank white** —
that is a loading race, not a broken chart. Wait ~3–4s, and if it is still blank,
wait again before concluding anything is wrong.

Then check the width the user actually cares about. `resize_window` with
`{preset: "mobile"}` or `{width: 700, height: 900}` re-renders the embed at that
size; the SVG rescales, so this is a real test rather than a cosmetic one. A blog
column is ~700px, a dashboard tile narrower still.

Republishing updates the embed immediately — there is no cache — so after a
`set_chart_config` fix, `navigate` to the same URL again and re-screenshot to
confirm the fix rather than assuming it landed.

Two caveats. Videos have no embed until they are rendered — the free
`preview_video_frame` JPEG is the only check before that. Once rendered, open the
player page at `https://plotset.com/video/<taskId>`, front the tab, and call
`document.querySelector('video').play()`, because the pane reports the document
hidden and autoplay stays suppressed; see
[references/video-charts.md](references/video-charts.md). And if the
browser tools are unavailable in your environment, say so plainly and fall back
to `export_chart` — but then tell the user you verified the export only, and that
a narrow embed may still break.

**Keep the type hierarchy intact.** If you are raising an axis or legend size past
the title size, stop — you are compensating for the scaling above, not fixing a
type problem. A chart whose axis labels are twice its headline is broken however
it got there. Scale the whole set with `--canvas` rather than moving one number a
long way.

Two fixes that come up constantly:

- **Do not set `bar.value.colorType`.** Left at `auto` the renderer picks a
  contrasting value-label colour per bar — white on dark, dark on light. Forcing
  it `custom` gives you dark-on-dark on half the bars.
- **Type sizes are absolute pixels calibrated for a 1200px-wide export.** If you
  export at another width, pass `--canvas <width>`.

## Working with the user

Decide, build, show, then offer the road not taken. One round trip beats an
interrogation: pick the chart type, design system and normalization from the
data, create it, show the PNG, and then say in a line or two which alternatives
you rejected and why — "went with a ranked bar over a pie because the eight
regions do not sum to a meaningful whole; `ledger` over `editorial` because this
reads like an internal finance review". That gives the user something concrete to
push against instead of a menu to fill in.

Ask first only when the answer would change the work and the data cannot settle
it: which geography a map should use when the names are ambiguous, or whether a
chart is for a slide or a report when that flips the design system between light
and dark.

## Invariants

- **Anything that mutates a chart makes its embed publicly reachable.**
  `create_chart`, `set_chart_config`, `set_chart_data`, `set_chart_title` and
  `export_chart` all publish. Say so when the data is not obviously public.
- **`create_video` consumes the user's render quota and publishes the finished
  video.** Ask before calling it, always, and only after they have seen a
  `preview_video_frame` they approve of.
- **Play a finished video for the user, don't just link it.** Open
  `https://plotset.com/video/<taskId>` in the browser pane and start playback —
  a URL in chat is not a delivered video.
- **Never invent a template slug or a config key.** Slugs come from
  `list_templates`, keys from `get_chart_schema` for that exact template.
- **Fonts are a closed set of 21.** Static charts need the exact family name
  *and* its `fontFamily_url`; video takes a bare name and no URL, and spells two
  of them differently (`Source Sans 3`, `Neuzeit Grotesk`). Both mappings live in
  `references/design-systems.json` under `fontUrls`.
- Check the `warnings` array on every create/set call. Auto-binding silently
  skips templates with no `bindingsGroup`.
- **Open the `embedUrl` in the browser before reporting a static chart as done.**
  The chart is already public at that point, so there is nothing to weigh up —
  and it is the only view of what the user actually receives.

| Tempting shortcut | What actually happens |
|---|---|
| "Small colour tweak, I'll write the config from memory" | Field names differ per template revision; the wrong key is stored and ignored |
| "The JSON is right, no need to view the PNG" | Valid config renders clipped labels, dark-on-dark values, rotated ticks |
| "The export PNG looks good, ship it" | The export and the embed scale their plot text differently; the embed is what the user shares, and it can be unusable while the export looks fine |
| "The embed screenshot came back blank, something's broken" | It loads its bundle and data after page load — wait 3–4s and screenshot again |
| "The CSV looks fine, skip normalizing" | `03/04/2024` parses as March, `(500)` as text, duplicate headers bind arbitrarily |
| "Nested config is cleaner than dotted keys" | Static charts ignore it completely and say nothing |
| "I'll set `data_color` later" | The video renders every series in flat black |
| "They approved the last preview, just render" | Approval applies to the preview they actually saw; renders cost quota and publish |
