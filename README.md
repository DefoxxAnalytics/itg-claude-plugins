# ITG Claude Code plugins

Claude Code plugins for the ITG team, published as a plugin marketplace.

| Plugin | What it does |
|---|---|
| [`itg-tracker`](plugins/itg-tracker) | Keeps the ITG SharePoint "Progress tracker list" current with the work projects you worked on in Claude Code. It drafts new rows and status updates, shows you one preview, and writes through Chrome only after your yes. |

## Install

The repository is private: you need read access to it, and git on your laptop signed in to GitHub (for example with `gh auth login`).

In Claude Code:

```
/plugin marketplace add DefoxxAnalytics/itg-claude-plugins
/plugin install itg-tracker@itg-plugins
```

Start a new session, then run `/itg-tracker:tracker-update`, or ask Claude to "update the progress tracker". The first run sets you up: see the plugin's [README](plugins/itg-tracker/README.md).

## Updates

`/plugin marketplace update itg-plugins` fetches new versions; `/plugin` lists what can be updated. Your own settings live outside the plugin (`~/.claude/tracker-update/`), so updates keep them.

## For maintainers

- Run the tests: `python -m pytest plugins/itg-tracker/tests -q`.
- Check the manifests: `claude plugin validate .`.
- Raise `version` in `plugins/itg-tracker/.claude-plugin/plugin.json` for every release, so installed copies see the update.
