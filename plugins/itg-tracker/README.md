# itg-tracker

A Claude Code plugin with one skill, `tracker-update`. It keeps the ITG SharePoint list "Progress tracker list" (`/sites/ITG`) current with your own work projects.

## What it does

1. Finds the work projects you worked on in Claude Code since its last run. It reads only each session's working folder, never the conversation, and only folders you named as work.
2. Drafts a status for each project from the day's commits and the project's Claude memory notes. For a project new to the list, it drafts a new row, or suggests a match with an existing row.
3. Shows you every change in one preview: each field before and after.
4. Writes through Chrome, signed in as you, **only after your yes**. It then checks each row's history to confirm only the approved fields changed.

It never puts client data on the list: no rows, quote text, supplier or employee names, client IDs or figures from client files. It never posts secrets, internal addresses or file paths either.

## You need

- Windows, with Claude Code and the **Claude in Chrome** extension connected.
- Chrome signed in to SharePoint, with edit rights on the ITG Progress tracker list.
- Python 3.11 or later, and git.

## Install

In Claude Code 2.1.275 or later:

```
/plugin install itg-tracker --marketplace DefoxxAnalytics/itg-claude-plugins
```

Or in two steps on any version: `/plugin marketplace add DefoxxAnalytics/itg-claude-plugins`, then `/plugin install itg-tracker@itg-plugins`. The repository is private, so you need read access to it and git signed in to GitHub.

## First run

Run `/itg-tracker:tracker-update`, or ask Claude to "update the progress tracker". With no settings yet, it asks:

- which folders hold your work: as many as you like, anywhere on the laptop (for example `D:\Dev` and a OneDrive folder);
- for each, the Business it belongs to, and whether it is a folder of projects or one project on its own;
- the short name for the People column.

Only those folders are ever looked at, and your folders don't need to match anyone else's. It saves your answers to `~/.claude/tracker-update/registry.json`, and reads who you are from SharePoint for "Assigned to". It then offers to match your projects with rows already on the list.

To change the folders later, ask Claude, or run `tracker.py add-folder "<path>" --business <Business>` (add `--single` for one project) and `tracker.py remove-folder "<path>"`.

## Every evening (optional)

On the first run Claude offers a Windows scheduled task, "Claude tracker update". At 17:30 on weekdays, or at your next logon if you missed it, the task checks for anything new to post. Only then does it open a Claude window with the preview, which waits for your yes.

- Set it up later: `pwsh -NoProfile -ExecutionPolicy Bypass -File "<skill folder>\schedule.ps1"`, optionally with `-At 18:00`.
- Remove it: run the same command with `-Remove`.

## Files

| File | What it is |
|---|---|
| `skills/tracker-update/SKILL.md` | The skill: first-run setup, gather, draft, preview, write, check, record |
| `skills/tracker-update/tracker.py` | Finds the projects and keeps your settings (Python standard library only) |
| `skills/tracker-update/sharepoint.md` | The browser snippets: read rows with their etags, write a batch, read a row's history |
| `skills/tracker-update/list-design.md` | How the list itself is formatted (gold rows, Power Apps form with its rules, branded board), the two flows on it (assignment message, notebook page per item) and how to undo each |
| `skills/tracker-update/scheduled.ps1`, `schedule.ps1` | The optional 17:30 task |
| `skills/tracker-update/registry.template.json` | The settings every person starts from |
| `tests/test_tracker.py` | Tests for `tracker.py` |
