# The ten design systems

Machine-readable values live in [design-systems.json](design-systems.json); this
page is the reasoning. `scripts/apply_design.py` reads the JSON, so change values
there and this page stays the rationale.

## How these were chosen

Each system is grounded in a real visual vernacular — a kind of printed or
broadcast artefact that already exists in the world — rather than assembled from
chart defaults. That is the whole reason they do not look alike: an accounting
pad, a jumbotron and a herbarium sheet disagree about everything, and the
disagreement is what you are buying.

They were deliberately kept clear of the looks that generated design falls into
by default: warm cream grounds with a high-contrast serif and a terracotta accent;
near-black with one acid-green or vermilion accent; broadsheet hairline rules;
identical rounded cards with the same soft grey shadow; and the template chrome of
tracked-out all-caps eyebrows, middle-dot meta strings and appended arrows. Where
a system lands near one of those — `editorial` is a serif display, `terminal` is
dark — it gets there from its own subject matter and differs in the specifics:
`editorial` sets Bodoni on stark white with an ink red, not a serif on cream with
clay; `terminal` runs amber/cyan/rose signal colours on slate-navy, not a single
acid hue on black.

## Anatomy

Every system defines the same roles, which is what lets one script map any of
them onto any template:

| Role | What it paints |
|---|---|
| `bg` | the chart ground (`palette.bg_color`) |
| `surface` | raised surfaces — tooltip fill, bar track |
| `ink` | titles and the highest-contrast text |
| `body` | axis labels, legend labels, subtitles |
| `muted` | source lines, notes, footnotes |
| `rule` | axis lines, tick marks, borders |
| `grid` | gridlines only — always quieter than `rule` |
| `ramp` | 9 categorical series colours, in priority order |
| `sequential` | 7 steps light→dark for one continuous measure |
| `diverging` | 5 steps for data with a meaningful midpoint |
| `fonts.display` / `fonts.body` | the two type roles, per medium |
| `scale` | absolute px sizes, calibrated for a 1200px-wide export |
| `shape` | bar radius/opacity/width, swatch and tooltip radius, line widths |
| `gridPolicy` | `none`, `value-axis-only`, or `both` |
| `valueLabels` | whether numbers are printed on the marks |

`fonts` carry separate `static` and `video` names because PlotSet's two renderers
ship different catalogues — `Source Sans Pro` is `Source Sans 3` in video, and
`Neuzeit Grotesk Light` is `Neuzeit Grotesk`. Static charts additionally need the
matching `fontFamily_url`; the `fontUrls` map in the JSON is the only correct
source for those.

---

## ledger · light

**Grounded in** the green columnar accounting pad: ruled bands, figures aligned
right, totals stamped in ink.

**Use for** money — revenue, cost, budget, P&L, unit economics, anything a CFO
would recognise. Also headcount and inventory where precision beats drama.

Ink navy leads the ramp with brass second, on a pale ledger-green ground that is
deliberately *not* the warm cream of generated design — real accounting pads are
green. Roboto Slab gives the title the weight of a printed statement; Inter keeps
the figures neutral. Gridlines on the value axis only, square bars, values on.

## bulletin · light

**Grounded in** health-ministry data bulletins and public wayfinding: one voice,
maximum legibility, nothing decorative competing with the number.

**Use for** public-interest statistics — health, population, education, safety,
survey results, NGO and government reporting. The right default when the audience
is the general public and the subject is serious.

One family (Noto Sans) doing both roles through weight alone, because institutional
communication should not look art-directed. Deep teal leads; the coral at index 1
is warm enough to mark a contrast without alarming. Slightly larger body sizes
than the other light systems — this is the system most likely to be read on a
phone by someone who did not choose to.

## broadcast · dark

**Grounded in** the stadium jumbotron and TV sports lower-thirds: condensed heavy
type, saturated signal colours, values burnt into the bars so they read from
across a room.

**Use for** competition and ranking — leagues, leaderboards, market-share races,
head-to-head. The first choice for `racebar` / `racecolumn` / `racepie` video.

Anton for the title and Oswald for everything else: both condensed, so long team
names survive. Gridlines off entirely — the bars are the grid. The largest value
labels of any system, because this one is designed to be watched, not read.

## fieldnotes · light

**Grounded in** botanical survey notebooks and herbarium sheets: pigments mixed
from the subject itself, rules drawn thin so the specimen stays loudest.

**Use for** nature and the slow sciences — climate, ecology, agriculture, energy,
water, land use, longitudinal research. Good where the data rewards patient
reading rather than a headline.

A sage-grey ground and low-chroma earth pigments; the ramp is muted on purpose so
that a single highlighted series can carry emphasis. Bree Serif over Lato. Value
labels off by default — this system assumes the reader will consult the axis.

## terminal · dark

**Grounded in** amber-phosphor CRT crossed with a modern observability console: a
dark instrument panel where each series is a distinct signal, not decoration.

**Use for** engineering telemetry — latency, throughput, error rates, uptime,
build and deploy metrics, infra cost. Use when the reader is technical and expects
density.

Multi-hue by design (amber, cyan, rose, mint) rather than the single acid accent
of generic dark-mode work — an ops chart usually has several series and they all
need to be distinguishable. VT323 is a bitmap face and only reads above ~28px,
which is why the display sizes here are large; never route body text through it.
Gridlines on both axes: this is the one system where reading exact values off the
grid is the point.

## atlas · light

**Grounded in** topographic survey sheets and nautical charts: land tinted in
graduated washes, place names set small and calm, the legend doing real work.

**Use for** anything geographic — choropleth, hexagon and point maps, flow maps,
regional comparison. Also the right pick for any single-measure ranking that wants
a sequential rather than categorical palette.

Its `sequential` ramp is the most carefully stepped of the ten, because on a map
the ramp *is* the chart. Pass `--palette sequential` and the script fills the map
colour family (`colors.colorSeq`, `colors.colorMin|Mid|Max`).

**Do not reach for `palette.type: "spectrum"` on a bar or line chart** — verified
behaviour is that it paints every mark the same single step. A value-ordered bar
chart wants `multi` with one interpolated colour per bar: pass `--categories N`.
Montserrat titles over Source Sans Pro labels.

## editorial · light

**Grounded in** the data page of a culture magazine: one didone headline at a size
that commits, everything else stepped far below it, a single ink red doing all the
pointing.

**Use for** feature journalism, opinion, analysis, launch posts — anywhere the
chart carries an argument rather than serving as a lookup table.

The 36/18 jump between headline and labels *is* the idea. Do not soften it toward
the middle: a Bodoni headline at 22px is just a small serif. Stark white rather
than cream, and the near-invisible grid keeps the headline and the one red series
as the only things with presence.

## playbook · light

**Grounded in** children's picture books and board-game boards: fat rounded forms,
colours that stay friendly beside each other, every number said out loud.

**Use for** education, classrooms, kids, consumer apps, onboarding, community and
fundraising updates — anywhere the reader is not being paid to look at the chart.

Passion One over Montserrat, 8px bar radius, thick bars, no gridlines, values
always on. The brights are desaturated just enough to sit together without
vibrating, which is what separates this from a default rainbow palette.

## clinical · light

**Grounded in** lab report printouts and patient monitors: a dense cool grid where
blue is normal, red means out of range, and the reader is scanning for the
exception.

**Use for** medicine, diagnostics, quality control, compliance, SLA and threshold
monitoring, A/B readouts. Use when some values are good and some are bad and the
chart has to say which.

The smallest type and tightest grid of the ten — density is the point, and the
reader is a professional. **The red at ramp index 1 is a semantic slot.** If
nothing in the data is an exception, skip it and go from index 0 to index 2, or
the chart implies an alarm that isn't there.

## nocturne · dark

**Grounded in** stage lighting against a night sky: jewel tones lit from within,
on deep indigo rather than black so the colours keep saturation on a phone screen.

**Use for** keynote slides, launch announcements, social and vertical video,
year-in-review pieces. The dark option when `broadcast` is too loud and `terminal`
too technical.

Indigo rather than black is the deliberate choice: pure black crushes saturated
hues on OLED phone screens, indigo lets violet and aqua stay luminous. Montserrat
throughout, 6px radius, values on. Pairs naturally with `1080x1920` video.

---

## Adapting a system

The systems are starting points. Three adaptations are almost always worth making:

1. **Reorder the ramp to the argument.** Position 0 goes to the series the chart
   is about. Everything else can drift toward the muted end. A chart where the
   subject is coloured like the context has no subject.
2. **Match the ramp kind to the measure.** `--palette categorical` for unrelated
   series, `sequential` for one continuous measure (all maps, all heatmaps),
   `diverging` where there is a real midpoint — change against last year,
   over/under target, sentiment.
3. **Follow the venue, not the topic, when they disagree.** Revenue on a keynote
   slide is `nocturne`; revenue in a board pack is `ledger`. The data profile's
   hints only see column names.

## Going beyond the ten

When the brief is a company brand, a specific publication's look, or a mood none
of these carry, invoke the **`frontend-design`** skill and design a token set for
that brief. Then express it in the same roles above, add it to a copy of
`design-systems.json`, and run `apply_design.py --systems-file <your-copy>` so it
gets the same schema-aware mapping as the built-ins.

Two constraints do not bend: the typeface must be one of the 21 in `fontUrls`, and
static charts need both the family name and its URL.
