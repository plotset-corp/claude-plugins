# Video charts

Animated charts are a different subsystem from static charts, with a different
config shape, a different font list and a real cost per render.

| | Static | Video |
|---|---|---|
| config shape | flat dotted keys | genuinely nested objects |
| schema tool | `get_chart_schema` | `get_video_template_schema` |
| fonts | family name **+ `fontFamily_url`** | bare enum name, no URL |
| colours | `palette.colors` array | `palette.data_color`: `[{key, value}]` |
| free preview | `export_chart` (publishes) | `preview_video_frame` (free, publishes nothing) |
| commit | persists a project | `create_video` — costs quota, publishes the MP4 |

## Templates

`list_video_templates`: `racebar`, `racecolumn`, `raceline`, `racepie`,
`raceswarm`, `chronobar`, `choropleth`, `flowmap`, `maptour`.

`get_video_template_schema(type)` returns `defaults` (a complete, valid config on
its own), `fields` (every path with its kind, enum and `condition`), `configSchema`
(a JSON Schema with `additionalProperties: false` — unknown keys are rejected),
`theme.options`, `video` (allowed fps/resolution/quality) and `dataFormat`.

Start from `defaults` and change only what you mean to. A field with a
`condition.parent` is a panel-UI visibility rule, not a renderer rule — the
renderer applies the value regardless — but the parent still has to hold a
sensible value for the child to make visual sense.

## The field you cannot forget

`palette.data_color` maps your CSV's series names to colours:

```json
{"palette": {"bg_color": "#0E1826",
             "data_color": [{"key": "Arsenal",   "value": "#00C2FF"},
                            {"key": "Liverpool", "value": "#FF3D77"}]}}
```

It cannot be pre-filled in `defaults` because the keys come from the data. Leave
it empty and **every series renders flat black**. `apply_design.py --series` builds
it; the series names are the cleaned CSV's header row minus the date column, spelled
exactly as they appear there.

## Data format

Video templates use the `date-series` parser: **first column a date, every other
column one numeric series named by its header.** At least 2 rows, since frames are
interpolated between points.

Long-format data (`date, series, value`) must be pivoted first or the animation
shows one bar that never moves:

```bash
python3 scripts/profile_data.py raw.csv --pivot --out wide.csv --profile profile.json
```

Day-first dates are auto-detected by the renderer, but ambiguously — `03/04/2024`
is a coin flip. `profile_data.py` normalizes to `yyyy-MM-dd` first so the reading
is fixed before the renderer sees it.

## Layers, timing and canvas

Both `preview_video_frame` and `create_video` take the same project shape:

```json
{"fps": 30, "resolution": "1920x1080", "quality": "high",
 "margin": {"top": 40, "right": 40, "bottom": 40, "left": 40},
 "layers": [{"type": "racebar",
             "settings": {"start": 0, "duration": 20,
                          "top": 0, "left": 0, "width": 1840, "height": 1000},
             "config": { ... },
             "dataCsv": "Date,Arsenal,Liverpool\n2024-03-01,64,63\n..."}]}
```

- `fps`: 30 or 60. `resolution`: `1920x1080`, `1080x1080`, `1080x1920`,
  `1200x1600`, `1600x1200`. `quality`: low / medium / high.
- `duration` is 5–120 seconds per layer.

**`settings.width` and `settings.height` do not scale the chart.** This is
verified behaviour and it is counter-intuitive. `top` and `left` translate the
layer as you would expect, but `width`/`height` only size the layer's background
box — the chart itself still renders at full frame scale and simply overflows,
spilling its bars and axis off the edge of the video while the background patch
sits in the declared rectangle.

So for a single-layer video, set `top: 0, left: 0` and `width`/`height` to the
full resolution, and **use `margin` to buy breathing room**. `margin.right` is
the one that matters most on a race chart: the leading bar's value label sits
hard against the frame edge otherwise. A right margin of ~200px at 1920 wide
gives it a proper gutter.

Multiple layers still stack and `top`/`left` still position them, but because
content does not scale to the layer box, genuine side-by-side composition is not
something the renderer supports the way the field names suggest.

Vertical (`1080x1920`) wants fewer bars and larger type: drop `bar.barCount` to
about 5 and pair it with `nocturne` or `broadcast`.

**Turn the legend off on race charts.** A `racebar` already prints each series
name against its own bar in that bar's colour, so `legend.item.show: true` (the
default) repeats all of them in a band across the top — pure duplication, and it
costs the vertical space that is scarcest in a 9:16 frame. Set
`legend.item.show: false` unless the template does not label its marks.

## The render loop

1. Build the config: `apply_design.py --schema vschema.json --system broadcast --series "..."`.
2. `preview_video_frame` with `framePosition` around `0.5` — free, and the middle
   of the animation is where crowding shows. Preview `0` and `1` too when the
   layout is tight, since the longest bar label appears at the end.
3. **Show the JPEG to the user and get explicit approval.**
4. `create_video`. Ask first — it consumes render quota, and the finished video is
   made publicly streamable.
5. Poll `get_video_status(taskId)` every ~15s until `done` is true. It returns a
   thumbnail JPEG inline plus a `streamUrl`, and tells you the video is now
   public — say so to the user.
6. **Play it for them** (below). Do not stop at handing over a URL.

If the queue is full the call fails fast with a 429 — wait for the running render
rather than resubmitting.

## Delivering the finished video

A completed render has three public addresses, all keyed by the 24-hex `taskId`:

| | URL |
|---|---|
| Player page | `https://plotset.com/video/<taskId>` |
| Direct MP4 | `https://video.plotset.com/storage/video-chart/video/public/<taskId>.mp4` |
| Stream | the `streamUrl` returned by `get_video_status` |

The player page is the one to open — it is a real PlotSet page with the title,
share and fullscreen controls, wrapping a `<video>` element (autoplay, muted,
controls) served from the direct MP4 above.

Open it in the browser pane so the user can watch it in the conversation rather
than clicking a link out:

```
preview_start  { url: "https://plotset.com/video/<taskId>" }
computer       { action: "wait", duration: 5 }
tabs_select    { tabId: "<tab>" }            # front it — this is for the user to see
javascript_tool{ action: "javascript_exec", text: "document.querySelector('video').play()" }
computer       { action: "screenshot" }
```

**The explicit `play()` is required.** The browser pane reports
`document.visibilityState: "hidden"` even with the tab fronted, which suppresses
autoplay and leaves the video paused on its first frame. Calling `play()` starts
it and it keeps running normally. Without that step you show the user a still and
tell them it is a video.

A screenshot a few seconds in is worth taking: it is proof the animation actually
moves, and it catches a render that completed but produced a frozen or empty
chart.

Artifacts are not an option here — the artifact CSP blocks media from every
external host, so a `<video src="https://video.plotset.com/...">` inside one
fails silently. `SendUserFile` on a downloaded MP4 works as a fallback when the
browser pane is unavailable.

## Video-specific gotchas

- Font names differ from static: `Source Sans 3` not `Source Sans Pro`,
  `Neuzeit Grotesk` not `Neuzeit Grotesk Light`. No `_url` field exists.
- `configSchema` has `additionalProperties: false` in most branches — a stray key
  is rejected outright rather than ignored. Validate against it if you hand-edit.
- Line widths are in video pixels, so the values that look right on a static chart
  are invisible here: gridlines want ~1–2px, axis and tick lines ~3–4px.
- Font sizes likewise scale with the frame — roughly 2.2× the static sizes at
  1080p. `apply_design.py` applies each system's `videoScaleMultiplier` for you.
- `theme.options` lists the renderer's own themes with their `dataColors`. The ten
  design systems here supersede them, but the option list is useful when a user
  asks for a named PlotSet theme by name.
