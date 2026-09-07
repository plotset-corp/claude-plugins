# Publishing this marketplace

## Before the first push

- [ ] **Choose a licence.** The other PlotSet repos are proprietary; a public
      plugin repo needs something users can install under. `plugin.json` has no
      `license` field yet — set it and add a `LICENSE` file. This is a business
      decision, deliberately left open.
- [ ] Confirm the repo name. Everything here assumes
      `github.com/plotset-corp/claude-plugins`; change `repository` in
      `plugins/plotset/.claude-plugin/plugin.json` and the install commands in
      both READMEs if it differs.
- [ ] Decide whether the repo is public. `/plugin marketplace add` needs read
      access, so a private repo only works for people who already have it.

## Publish

```bash
git remote add origin git@github.com:plotset-corp/claude-plugins.git
git push -u origin main
```

Then verify as a stranger would, from a clean machine or a scratch account:

```bash
claude plugin marketplace add plotset-corp/claude-plugins
claude plugin install plotset@plotset
```

Restart Claude Code and confirm the PlotSet MCP tools appear and OAuth prompts on
first use.

## Releasing a version

`claude plugin tag` creates a `{name}--v{version}` git tag and checks that
`plugin.json` and the marketplace entry agree:

```bash
claude plugin tag plugins/plotset
```

Bump `version` in `plugins/plotset/.claude-plugin/plugin.json` for anything users
should receive. `claude plugin update plotset@plotset` is how they get it.

## Getting into Anthropic's official directory

Vendors in `claude-plugins-official` host their own repo; the official
marketplace only points at it, pinned by ref and SHA:

```json
"source": {
  "source": "git-subdir",
  "url": "https://github.com/plotset-corp/claude-plugins.git",
  "path": "plugins/plotset",
  "ref": "plotset--v0.1.0",
  "sha": "<commit sha>"
}
```

So this repo is the prerequisite, not a detour — submit a PR to
`anthropics/claude-plugins-official` adding an entry of that shape once a tagged
version is live.

## Claude apps (claude.ai, desktop)

Claude Code plugins do not reach the Claude apps. For those, package the skill
directory as a `.skill` file and upload it under Settings → Capabilities. That
surface has no MCP bundling, so the PlotSet connector must be added separately —
worth doing as a second track.

## Known gaps in v0.1.0

- The video path is verified only up to the free `preview_video_frame` step. The
  `create_video` → poll → deliver tail is written from the tool contracts and has
  never been executed end to end.
- Auto-binding can leave a required binding slot empty while returning
  `warnings: []`, which renders a blank chart. Observed on an ordinary two-column
  CSV; not yet documented in the skill.
- One iteration of evals has been run (3 cases). Only one of the three
  discriminated against a no-skill baseline.
