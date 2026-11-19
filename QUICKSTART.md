# itg-tracker quick start

How to set up the itg-tracker plugin and post your first update to the ITG "Progress tracker list". The [README](README.md) is the full guide.

## 1. Before you start

- Windows or a Mac, with Claude Code and the **Claude in Chrome** extension connected.
- Chrome signed in to SharePoint as yourself, with edit rights on the ITG "Progress tracker list". Site members have them.
- Python 3.11 or later, and git.
- Read access to this repository, and git signed in to GitHub (`gh auth login`).

## 2. Install

In Claude Code:

```
/plugin marketplace add DefoxxAnalytics/itg-claude-plugins
/plugin install itg-tracker@itg-plugins
```

Then start a new session, so the skills are loaded.

## 3. Set it up

Run `/itg-tracker:tracker-update`. The first time, Claude asks you these in one message:

| It asks | What to answer |
|---|---|
| Which folders hold your work | Every folder with work projects in it, anywhere on the laptop, such as `D:\Dev` or `/Users/<you>/Projects`. Only these folders are ever looked at. |
| The Business of each folder | Corporate, Versatex, XLC, or FX / Foxx Construction |
| A folder of projects, or one project? | "Folder of projects" when each folder inside it is a project; "one project" when the folder is the project itself |
| Your short name | The name that goes in the People column |

Then Claude:

1. tells you who you are signed in as on SharePoint;
2. offers to match your projects with rows the list already has. You decide each match;
3. offers the evening task once: at 17:30 on weekdays, it opens the preview when there is something to post. It is optional, and can be set up later.

## 4. Read the preview, then answer

Nothing is written until you say yes to the exact text. A preview looks roughly like this (the projects are made up, and the wording varies):

```
Update row 12 "Expense approvals"
  Notes   before: Status 4 Nov 2026: • First draft of the approval form
          after:  Status 18 Nov 2026:
                  • The approval form is live for two teams.
                  • Next: the remaining teams, then retire the old sheet.
  Open notes

New row "Weekly stock report"
  every field: Title, Summary, Description, Business, Progress, People, Assigned to, Notes
  Phase? Discover, Design or Deliver
  Its notebook page appears a minute or two after the row.

Match folder "onboarding-checklist" to row 7 "New starter onboarding"?

Apply all? You can also say: yes except …, ignore …, match … to row …, or edit any text.
```

Before you say yes, check:

- **Nothing confidential.** No client data (rows, names, request numbers, figures from client files), secrets, file paths, internal links or email addresses. Claude leaves these out, but the text goes on a list the whole team reads, so you are the last check.
- **It reads right to a colleague** who has not seen the project.
- **The Phase of each new row.** Claude asks for it; it never guesses.
- **Each match.** Matches are only suggestions: say no when the row is a different piece of work.

Then reply:

| You say | What happens |
|---|---|
| `yes` | Everything in the preview is written. |
| `yes except row 12` | Everything but row 12 is written. |
| `ignore <project>` | That project is not offered again. |
| `match <folder> to row 7` | The folder is tied to row 7 from now on. |
| An edit, such as "make the second bullet: …" | Your wording replaces Claude's. |

Claude then reads the rows back and checks each row's history, to confirm only the fields you approved changed.

## 5. Fill in your notebook pages

Every work item has a page in ITG Notebook ▸ Projects. Run `/itg-tracker:project-notes`; it uses the settings from step 3. The preview has one block per page:

| The preview says | What it means |
|---|---|
| Rebuild the page | Nobody has edited the page, so all of it is rewritten. About a minute and a half a page. |
| Fill 2 empty sections | Someone has typed on the page. Only empty sections are filled; nothing anyone wrote is replaced. |
| Nothing: … | That page cannot be written, and the reason follows. |

Answer `yes`, `yes except …`, `skip …`, or edit any text. Only work items assigned to you are drafted, and only those with a folder on your laptop.

## Day to day

- Run `/itg-tracker:tracker-update`, or say "update the progress tracker", after a day's work. It covers everything since your last run, and says so when there is nothing new.
- For work done outside Claude Code, name it: `/itg-tracker:tracker-update <project>: <status>; <project>: <status>`.
- Run `/itg-tracker:project-notes` now and then. The tracker holds this week's status; the notebook page holds what stays true for months.
- To update the plugin: `/plugin marketplace update itg-plugins`, then `/plugin` lists what can be updated. Start a new session afterwards.

## If something goes wrong

| What you see | What to do |
|---|---|
| Chrome or the extension does not answer | Open Chrome, check the Claude in Chrome extension is connected, and run the skill again. |
| A SharePoint sign-in page | Sign in yourself in that tab, then run the skill again. Claude never types credentials. |
| "Someone else is signed in" | Sign in to SharePoint as yourself, or ask Claude to update who you are. |
| A row comes back as changed | Someone edited it after your preview. Nothing was overwritten; Claude reads it again and asks you again. |
| A page request stays pending for more than 5 minutes | Tell the flow owner. Do not send the same write again. |
| `git` cannot fetch the marketplace | You need read access to the repository, and git signed in to GitHub (`gh auth login`). |

Anything else: [Troubleshooting](README.md#troubleshooting) in the README.
