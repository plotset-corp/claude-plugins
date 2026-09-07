# PlotSet plugin

Charts and animated data videos on [PlotSet](https://plotset.com), driven from
Claude Code.

Install via the marketplace in the repository root:

```bash
/plugin marketplace add plotset-corp/claude-plugins
```

```bash
/plugin install plotset@plotset
```

## Contents

| | |
|---|---|
| `skills/plotset-chart/` | the skill — workflow, ten design systems, template and video references |
| `skills/plotset-chart/scripts/profile_data.py` | normalizes a CSV and profiles it so the chart follows the data |
| `skills/plotset-chart/scripts/apply_design.py` | maps a design system onto a template's own schema |
| `.claude-plugin/plugin.json` | plugin manifest, including the bundled MCP server |

## Why the scripts exist

PlotSet field names are not stable across template revisions — the same visual
role is `header.titleStyle.fontFamily` on one and `fonts.header.title_font_family`
on another — and a key the template does not know is **stored and silently
ignored**. `apply_design.py` reads the target template's own schema and writes
back only keys that exist in it, which is the only safe way to style a chart.

`profile_data.py` exists because every run would otherwise rewrite the same CSV
cleaner, and because chart choice should follow from measured shape and
cardinality rather than from the first chart type that comes to mind.

Both are stdlib-only Python 3.

## Development

The skill is a normal directory — edit `SKILL.md` and the files under
`references/`, then reinstall the plugin to pick up changes. Bump `version` in
`.claude-plugin/plugin.json` for anything users should get.
