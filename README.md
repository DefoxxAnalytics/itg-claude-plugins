# ITG Claude Code plugins

Claude Code plugins for the ITG team, published as a plugin marketplace (`itg-plugins`).

| Plugin | Version | What it does |
|---|---|---|
| [`itg-tracker`](plugins/itg-tracker) | 1.4.0 | Keeps the ITG SharePoint "Progress tracker list" current with the work projects you worked on in Claude Code, and fills in each project's page in the ITG Notebook. It drafts, shows you a preview, and writes through Chrome only after your yes. |

## Contents

- [What the plugin gives you](#what-the-plugin-gives-you)
- [Before you install](#before-you-install)
- [Install](#install)
- [First run](#first-run)
- [Using it day to day](#using-it-day-to-day)
- [What it will and will not do](#what-it-will-and-will-not-do)
- [How it works](#how-it-works)
- [What lives on the ITG site](#what-lives-on-the-itg-site)
- [Your settings](#your-settings)
- [Updates](#updates)
- [Troubleshooting](#troubleshooting)
- [Repository layout](#repository-layout)
- [For maintainers](#for-maintainers)

## What the plugin gives you

Two skills, both run from Claude Code on your own laptop:

| Skill | Run it with | What it does |
|---|---|---|
| `tracker-update` | `/itg-tracker:tracker-update`, or "update the progress tracker" | Finds the work projects you worked on since its last run, drafts a status for each row you own (and a new row for a project the list does not have yet), shows every change before and after, and writes after your yes. |
| `project-notes` | `/itg-tracker:project-notes`, or "fill in my project notes pages" | For each work item assigned to you that has a folder on your laptop, drafts the sections of its ITG Notebook page (purpose, how it works, key decisions, links, open questions), shows one preview per page, and writes after your yes. |

The tracker holds status: what changed, what comes next. The notebook page holds what stays true for months.

## Before you install

- Windows, with Claude Code and the **Claude in Chrome** extension connected.
- Chrome signed in to SharePoint, with edit rights on the ITG "Progress tracker list". Site members have them.
- Python 3.11 or later, and git. The helper uses the Python standard library only.
- Read access to this repository, and git signed in to GitHub (for example with `gh auth login`). The repository is private.

## Install

In Claude Code:

```
/plugin marketplace add DefoxxAnalytics/itg-claude-plugins
/plugin install itg-tracker@itg-plugins
```

On Claude Code 2.1.275 or later, one line does both:

```
/plugin install itg-tracker --marketplace DefoxxAnalytics/itg-claude-plugins
```

Start a new session afterwards, so the skills are loaded.

## First run

Run `/itg-tracker:tracker-update`. With no settings yet, Claude asks, in one message:

- which folders hold your work: as many as you like, anywhere on the laptop;
- for each, the Business it belongs to (Corporate, Versatex, XLC, or FX / Foxx Construction), and whether it is a folder of projects or one project on its own;
- the short name you want in the People column.

Then it:

1. saves your answers to `~/.claude/tracker-update/registry.json`;
2. reads who you are signed in as on SharePoint, for "Assigned to", and tells you;
3. offers to match your projects with rows the list already has. You decide each match;
4. offers the optional evening task (below), once.

Only the folders you named are ever looked at. Your folders do not need to match anyone else's.

Run the tracker update once before the project notes skill: the second skill uses the first one's settings.

## Using it day to day

### Update the tracker

1. Run `/itg-tracker:tracker-update`. For work done outside Claude Code, add manual entries: `/itg-tracker:tracker-update <project>: <status>; <project>: <status>`.
2. Read the preview. For every row it shows each changed field, before and after. For a new row it shows every field and asks you for the Phase.
3. Answer "yes", or "yes except …", "ignore …", "match … to row …", or edit any text.
4. Claude writes what you approved, reads the rows back, and checks each row's version history to confirm only the approved fields changed.

If there is nothing new since the last run, it says so and stops.

### Fill in the notebook pages

1. Run `/itg-tracker:project-notes`.
2. Claude reads each of your pages and drafts only the sections it is allowed to write (see the rules below).
3. Read the preview: one block per page, with the full text of every section, what is left alone and why, and what kind of thing was left out under the content rules.
4. Answer "yes", or "yes except …", "skip …", or edit any text.
5. Claude writes one page at a time and reads each back. A whole-page rewrite takes about a minute and a half.

Work items of yours with no folder on this laptop are listed in the preview and never drafted from memory.

### The evening task (optional)

A Windows scheduled task, "Claude tracker update". At 17:30 on weekdays, or at your next logon if you missed it, it checks whether anything is waiting to be posted. Only then does it open a Claude window with the preview, which waits for your yes.

| To | Run |
|---|---|
| Set it up, or change the time | `pwsh -NoProfile -ExecutionPolicy Bypass -File "<skill folder>\schedule.ps1"`, optionally with `-At 18:00` |
| Remove it | the same command with `-Remove` |

`<skill folder>` is the plugin's `skills\tracker-update` folder. Claude can run this for you.

## What it will and will not do

**It always asks first.** Nothing is written to the list or to a notebook page without your yes to the exact text. The text is drafted by Claude and goes onto things the team shares.

**It reads little.**

- Of each Claude session file, only the working folder, never the conversation.
- From a project, for a status: your own commit subjects, and the project's Claude memory notes.
- From a project, for its notebook page: the README, up to 5 markdown files in a top-level `docs` folder, your own commit subjects, the Claude memory index and at most 5 memory notes.
- Never source code, data folders, exports, attachments or session transcripts.

**What it reads is data, never instructions.** If a README, a commit subject, a memory note, a list row or a page asks for something, Claude does not do it and says so in the preview.

**It keeps these off the list and the pages:**

- client data: rows, quote text, supplier or employee names, request numbers or other client IDs, figures from client files;
- secrets, keys and tokens;
- internal URLs, host names, file paths and email addresses.

A client is named only as the list's existing rows already name it.

**On an existing row it changes only:** Notes; Progress, on clear evidence; and an empty Description or Assigned to. It never changes Title, Summary, Phase, Business, People, or the "Project notes" link.

**On a notebook page:**

| The page | What can be written |
|---|---|
| Nobody has edited it | The whole page can be rewritten. This makes a new page and removes the old one; the tracker's link follows. |
| A person has typed on it | Only sections that are still empty can be filled. Nothing a person wrote is ever replaced. |
| A person has typed on it, and it has the old layout (made before 12 Nov 2026) | Nothing. Claude says so and moves on. |

Only the assignee of a work item can have its page written. Pages are written under the flow owner's name, whoever asked; the request list records who asked.

## How it works

```
your laptop                                   the ITG site (SharePoint)
-----------                                   -------------------------
Claude Code
  tracker.py  finds your projects, keeps
              your settings (local only)
  Chrome  ──  signed in as you  ───────────►  Progress tracker list      rows read and written directly
          ──  leaves a request  ───────────►  Project notes requests ──► flow ──► ITG Notebook ▸ Projects
```

- **`tracker.py`** runs locally. It lists your work projects with Claude sessions since the last run, with the commit subjects and memory files a status can be drafted from, and keeps the record of which folder belongs to which row.
- **The tracker list** is read and written from a Chrome tab, with your own SharePoint session, through the three snippets in `sharepoint.md`. Every write carries the row's etag, so a row someone changed after your preview is refused, not overwritten.
- **Notebook pages** cannot be reached from the browser the same way. The skill leaves a request in the list "Project notes requests"; a Power Automate flow carries it out and writes the result back to the request. `notes.js`, run in the tab, decides what may be written; the page's HTML stays in the tab and never passes through the conversation.
- **The flow checks for itself**, so a request made by hand cannot get round the rules: the requester must be the work item's assignee, the page must still be what was read, and a page edited since its last rewrite is not rewritten.

## What lives on the ITG site

These were built for the list and are described in full, each with how to undo it, in [`list-design.md`](plugins/itg-tracker/skills/tracker-update/list-design.md).

| Piece | What it does | Section |
|---|---|---|
| Light gold rows | Marks the viewer's own rows in the list | 1 |
| Branded Progress board | The Kanban view, with branded cards | 3 |
| Power Apps form | The form everyone sees when creating, editing or viewing a work item, with its rules and a "Project notes" button | 4 |
| List validation | Title is required, and Due date must be on or after Start date, for every write | 4 |
| Flow "Progress tracker: tell the assignee" | Sends the assignee a Teams message when a work item is assigned to them | 5 |
| Flow "Progress tracker: create project notes pages" | Gives every work item a page in ITG Notebook ▸ Projects and writes its link to the item | 6 |
| List "Project notes requests" and flow "Progress tracker: write project notes" | Read, fill or rewrite a page for the project-notes skill | 7 |

The flows run under their owner's connections. If the owner's sign-in lapses, the flows stop until the owner signs the connections in again.

## Your settings

Everything personal is in `~/.claude/tracker-update/registry.json`, outside the plugin, so updates keep it. It never leaves your laptop.

| To | Ask Claude, or run |
|---|---|
| Add a folder of projects | `tracker.py add-folder "<path>" --business <Business>` |
| Add one project on its own | the same, with `--single` |
| Remove a folder | `tracker.py remove-folder "<path>"` |
| Tie a folder to a row | `tracker.py record "<key>" --row <id> --title "<row title>"` |
| Stop offering a folder | `tracker.py ignore "<key>"` |
| Say a folder is part of another project | `tracker.py alias "<key>" --to "<key>"` |
| See which projects have a row, and what their pages can be drafted from | `tracker.py projects` |
| See what is waiting to be posted | `tracker.py gather`, or `tracker.py pending` for the count |

`tracker.py -h` lists every command. A different settings file can be named with `--registry <file>` or the `TRACKER_REGISTRY` variable.

## Updates

```
/plugin marketplace update itg-plugins
```

then `/plugin` lists what can be updated. Start a new session after updating.

| Version | What came with it |
|---|---|
| 1.4.0 | The `project-notes` skill; `tracker.py projects` |
| 1.3.0 | A notebook page for every work item; the skill leaves the "Project notes" link alone |
| earlier | The `tracker-update` skill, first-run setup, the evening task |

## Troubleshooting

| What you see | What to do |
|---|---|
| "No settings yet" | Run `/itg-tracker:tracker-update` once; it sets you up. |
| Chrome or the extension does not answer | Open Chrome, check the Claude in Chrome extension is connected, and run the skill again. |
| SharePoint shows a sign-in page | Sign in yourself in that tab, then run the skill again. Claude never types credentials. |
| "Someone else is signed in" | The SharePoint account is not the one in your settings. Sign in as yourself, or ask Claude to update who you are. |
| A row comes back as changed (412) | Someone edited it after your preview. Claude reads it again and asks you again; nothing was overwritten. |
| "Title is required, and Due date must be on or after Start date." | The list refused the row. Fix the title or the dates with Claude and try again. |
| A new row has no "Project notes" link yet | Its page appears a minute or two after the row. |
| A page write says "the page changed after it was read" | Someone edited the page in the meantime. Claude reads it again and shows you that page again. |
| A page write says "someone has edited this page since it was last rebuilt" | The page now holds a person's text, so it can no longer be rewritten whole. Run the skill again: it will offer to fill the empty sections only. |
| A page request stays pending for more than 5 minutes | The flow failed or Microsoft's services are slow. Tell the flow owner; do not send the same write again. |
| A work item of yours is listed as "no folder on this laptop" | Tie its folder to the row with `tracker.py record`, or leave it: its page stays yours to write by hand. |
| `git` cannot fetch the marketplace | You need read access to the repository and git signed in to GitHub (`gh auth login`). |

## Repository layout

```
.claude-plugin/marketplace.json        the marketplace: names the plugins in this repository
plugins/itg-tracker/
  .claude-plugin/plugin.json           the plugin's name, version and description
  README.md                            the plugin's own guide
  skills/tracker-update/
    SKILL.md                           the skill: first-run setup, gather, draft, preview, write, check, record
    tracker.py                         finds the projects and keeps your settings
    sharepoint.md                      the browser snippets: read rows, write a batch, read a row's history
    list-design.md                     how the list, its form and its flows are built, and how to undo each
    schedule.ps1, scheduled.ps1        the optional 17:30 task
    registry.template.json             the settings every person starts from
  skills/project-notes/
    SKILL.md                           the skill: find the projects, read the pages, draft, preview, write, check
    notes.js                           runs in the browser tab: reads a page, decides what may be written, sends the write
  tests/
    test_tracker.py                    tests for tracker.py
    test_notes.js                      tests for notes.js
```

## For maintainers

- **Run the tests** from the repository root:
  ```
  python -m pytest plugins/itg-tracker/tests -q
  node --test plugins/itg-tracker/tests/test_notes.js
  ```
- **Check the manifests:** `claude plugin validate .`
- **Release:** raise `version` in `plugins/itg-tracker/.claude-plugin/plugin.json`, so installed copies see the update, and add a line to the version table above.
- **Try a change locally** before pushing: `/plugin marketplace add <path to this repository>`, then install from it.
- **Changing the list, the form or a flow:** read `list-design.md` first, and write down what you changed there, with how to undo it. Before any bulk write to the shared list, try it on one "ZZ TEST … (delete me)" item and read back "Modified", "Modified by" and both flows' run history: every write to a work item, even one made in place, starts the assignment flow.
- **Keep client data out of this repository**, as out of the list: the tests use made-up projects and pages only.
