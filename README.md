# PlotSet for Claude Code

Turn a spreadsheet into a publishable chart — or an animated data video — without
leaving your editor.

```bash
/plugin marketplace add plotset-corp/claude-plugins
```

```bash
/plugin install plotset@plotset
```

Restart Claude Code, then just describe what you want:

> turn ~/Downloads/q3-sales.csv into a chart for the board deck

> here's fibre broadband by country — visualise it for a blog post

> make this into one of those bar chart race videos for socials

That is the whole workflow. You do not need to name the plugin, learn a config
format, or open the PlotSet panel.

## What you get

**One install, both halves.** The plugin ships the PlotSet MCP server alongside
the skill, so there is no separate setup step — Claude gets the chart-building
tools and the judgement to use them at the same time. You sign in through
PlotSet's normal OAuth on first use.

**Your data, cleaned first.** Finance exports and survey dumps carry things that
bind wrong rather than fail loudly: `$1,234`, `(500)` meaning −500, `03/04/2024`
that could be March or April, blank and duplicate header cells. These are
normalized before anything is uploaded, and you are told what changed.

**The chart follows the data.** Chart type is chosen from the data's actual shape
and cardinality — a ranked bar rather than a pie when eight categories do not sum
to a whole, a choropleth when the rows are countries, a bump chart when the story
is rank rather than level.

**Ten design systems, not one default look.** Each is grounded in a real visual
vernacular — an accounting pad, a public-health bulletin, a stadium jumbotron, a
herbarium sheet — and picked from what your data is about:

| | | |
|---|---|---|
| `ledger` | light | money, P&L, unit economics |
| `bulletin` | light | public-interest statistics |
| `broadcast` | dark | competition, rankings, race videos |
| `fieldnotes` | light | climate, ecology, agriculture |
| `terminal` | dark | engineering telemetry |
| `atlas` | light | maps and geography |
| `editorial` | light | journalism and analysis |
| `playbook` | light | education, kids, community |
| `clinical` | light | medicine, QC, thresholds |
| `nocturne` | dark | keynote, social, vertical video |

Ask for a different one at any time, or describe your brand and get something
bespoke.

**It looks at what it made.** Every chart is opened in a browser at the width you
will actually publish it, because a config that validates perfectly still produces
clipped labels and unreadable axes. You get the render, not a promise.

## Charts and videos

Static charts cover bar, column, line, area, pie, donut, treemap, sunburst,
scatter, bubble, sankey, chord, histogram, box, violin — and roughly 355 maps,
from world and continent down to US counties and individual countries' provinces.

Data videos cover bar chart races, race lines and columns, pie fights, swarm
plots, chronobars, animated choropleths, flow maps and map tours. Frame previews
are free; you are always asked before a render, because renders consume quota and
publish the result.

## Requirements

- Claude Code
- A PlotSet account — sign up at [plotset.com](https://plotset.com)
- Python 3 for the bundled data-profiling scripts (stdlib only, nothing to install)

## Good to know

Creating or editing a chart **makes its embed publicly reachable** — that is how
PlotSet embeds work, and there is no private render path. Rendering a video
publishes the finished MP4. You will be told before either happens.

## Links

[plotset.com](https://plotset.com) · [Gallery](https://plotset.com/gallery) ·
[Video Render](https://plotset.com/video-render) · [MCP](https://plotset.com/mcp)
