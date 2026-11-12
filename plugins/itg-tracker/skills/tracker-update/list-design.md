# The tracker list's look (applied 11 Nov 2026)

Changes made to the ITG "Progress tracker list" (`/sites/ITG`) at the list owner's request, and how to undo each. They apply to everyone who opens the list; only the list's owners should change them. Apply or undo them with the REST calls in `sharepoint.md`'s style (digest from `/_api/contextinfo`, POST with `X-HTTP-Method: MERGE`, `IF-MATCH: *`).

## 1. The viewer's own rows in light gold

Set as `CustomFormatter` on the views All Items, Grouped by work item progress, Grouped by priority and My work items (`/_api/web/lists/getbytitle('Progress tracker list')/views('<id>')`). All four had no formatter before.

```json
{"$schema":"https://developer.microsoft.com/json-schemas/sp/v2/row-formatting.schema.json","additionalRowClass":"=if([$AssignedTo0.email] == @me, 'sp-css-backgroundColor-BgGold', '')"}
```

- `@me` is whoever is looking, so each person sees their own items coloured (rgb 255, 235, 192).
- A view saved with `ViewType2: "GRIDFIXED"` opens in grid editing mode and shows no row formatting. All Items and My work items are GRIDFIXED. On 11 Nov they were set to `null` (the gold showed), then **put back to `"GRIDFIXED"` at the owner's request**. So the gold shows only in the two grouped views, or after "Exit grid view".
- The Progress board (Kanban) and Homepage cards (tiles) have their own designs and were not touched.
- **Undo:** set `CustomFormatter` to `""` on those four views.

## 2. The branded form (JSON formatting, superseded the same evening)

**No longer what people see.** Later on 11 Nov the list was switched to a Power Apps form (section 4), which replaces the SharePoint form this formatting applies to. The formatter below was not touched by that work, so it shows again only if the list goes back to the default SharePoint form.

Set as `ClientFormCustomFormatter` on the list's **Item** content type (`.../contenttypes('<Item id>')`). It was empty before.

- **Format:** `{"headerJSONFormatter": <object>, "footerJSONFormatter": <object>, "bodyJSONFormatter": "<string>"}`. Header and footer must be **objects**: as strings they don't render, and "Configure layout" shows them as escaped text. The body as a string works.
- **Header:** a black band (`#231f20`, radius 6 px, 4 px yellow `#fdc00f` bottom rule, 12 px below it) holding:
  - the white Versatex logo at 64 px (`/sites/ITG/SiteAssets/versatex-logo-white-128.png`, uploaded the same day, 128 px, 9 KB);
  - "ITG PROGRESS TRACKER" in `#c7c8ca`;
  - the title, or "New work item";
  - a yellow hexagon standing on a point (svg path `M10 0 L20 5.75 L20 17.25 L10 23 L0 17.25 L0 5.75 Z`);
  - chips on `#393536` for Progress ("Not started" when empty), "Phase: …" and Business (both hidden when empty).
- **Body sections:**
  - Overview: Title, Summary, Description
  - Status: Progress, Phase, Priority, Start date, Due date
  - People and business: Assigned to, Key stakeholders, People, Business, Category
  - Notes: Notes

  Attachments falls into a section of its own.
- **Footer:** "Last changed by <Editor> on <Modified date>" ("Saved items appear on the tracker straight away." on a new item), and on the right a small yellow hexagon with "Versatex · ITG".
- **Brand rules kept:** yellow only as a fill or rule, never as text. Black, white and the Versatex greys.
- **Undo:** set the Item content type's `ClientFormCustomFormatter` to `""`. Or open an item, then the form icon ▸ Configure layout, and clear the Header, Body and Footer boxes. The logo file can stay or go.

## 3. The branded Progress board (Kanban view)

The `CustomFormatter` of the view "Progress board" was replaced with `{"kanbanProps": {"hideSelection": false, "formatter": <card>}}`. The card has:

- a black band (yellow 3 px rule) with a yellow hexagon, Business in capitals (or "ITG") and Phase on the right;
- the title, and the Summary clamped to 2 lines;
- a status chip:
  - In progress: black
  - Completed: grey `#58595b`
  - Blocked or Behind: red `#a3201a`
  - Not started: outlined grey
- the Assigned-to photo and name ("Unassigned" in grey);
- "Due <date>" when set, red when past and not Completed;
- a white card, or gold `#ffebc0` when assigned to the viewer.

The view's fields gained Business, Phase and Summary (`addviewfield`). A Kanban card only sees the view's fields.

Gotchas found on 11 Nov when saving view formatters through REST:
- `<` and `&&` in an expression make the save fail with 500.
- `>` saves, but is stored as `&gt;`, which silently breaks the formatter: the board falls back to its default card.
- So use nested `if` instead of `&&`. For a date check, use `(Number(@now) - Number([$DueDate])) == abs(Number(@now) - Number([$DueDate]))` (past or today).
- After a change, load the board with a fresh query string to get past the cached data.

**Undo:** the original formatter (the card designer's, with its `designerConfig`) is saved byte for byte at `/sites/ITG/SiteAssets/progress-board-card-original-2026-11-11.json`. Read it and MERGE it back as the view's `CustomFormatter`. The three added view fields can stay, or be removed with `ViewFields/removeviewfield('<name>')`.

## 4. The Power Apps form (published 11 Nov 2026, redesigned 12 Nov)

The list's new, edit and view forms are a Power Apps customized form, "Progress tracker list on ITG forms" (app id `5409a4a5-135e-4569-9552-8a97985bc5c2`, default environment). Open it for editing from the list: Integrate ▸ Power Apps ▸ Customize forms. Nothing reaches the team until Publish ▸ Publish to SharePoint, and SharePoint then serves the old form from cache for about a minute.

What the form does:

- **Banner:** black band with the white Versatex logo (embedded in the app as a data URI), the item's title or "New work item", and a yellow rule. On an existing item a line of chips under the title shows Progress, Phase and Business, plus a red "Overdue" chip when it applies. The chips follow unsaved edits.
- **Sections**, each with a grey band and a yellow marker:
  - Work item: Title, Description, Category, Business
  - Status: Progress, Priority, Phase
  - Schedule: Start date, Due date
  - People: Assigned to, Key stakeholders
  - Notes: Notes, People, Summary
- **Section order:** as listed above on a new item and in view mode. In edit mode it is Status, Schedule, Notes, Work item, People, so a status update needs no scrolling.
- **Side-by-side fields:** Category and Business, Priority and Phase (40% and 60%), Start date and Due date. Everything else is full width.
- **Progress and Phase are button rows** in new and edit mode (five and three buttons, the selected one black). View mode shows them as plain text.
- **Footer:** "Last changed by <name> on <date>" on an existing item.
- **Defaults on a new item:** Progress "Not started", Phase "Discover", Start date today.
- **Rules:**
  - Title is required.
  - Due date must be on or after Start date (save is refused).
  - Notes is required when Progress is Blocked or Behind.
  - Due date is required when Progress is In progress.
  - "Overdue" shows under Due date when it has passed and Progress is not Completed.
- **Assigned to** lists the members of the ITG Microsoft 365 group, read live through the Office 365 Groups connector (group id `a4d12876-a711-4604-abb1-da885a1f1452`). The "AI Projects" account is filtered out. Add or remove someone in the group and the list follows; no form edit needed.
- **Key stakeholders** searches the whole directory. The owner chose on 11 Nov to keep it open to the entire tenant.
- **People and Summary** are editable and labelled "(updated automatically by the tracker)".
- **View mode:** empty fields are hidden. Description, Notes and Summary show as full-height text, not in a scroll box.
- **Brand rules kept:** yellow only as a fill, rule or marker; selection, hover and focus states are black or grey.
- **Font:** Segoe UI. Power Apps has no Roboto; it offers Arial, Courier New, Georgia, Lato, Open Sans, Segoe UI, Verdana and three script fonts.

Things that are different from a plain list form:

- The form is one tall control inside the page, so it scrolls on its own.
- The first time someone opens it, Power Apps asks them to allow the SharePoint and Office 365 Groups connections.
- Form-only rules (Notes when Blocked or Behind, Due date when In progress, the defaults) do not apply to grid edits or to this skill's REST writes. The two list-level rules below do.

### List-level rules set with the form

- The Title column is required (`Required: true`). Making it required reset the column header from "Work item" to "Title"; the display name of `LinkTitle` and `LinkTitleNoMenu` was set back to "Work item".
- List validation formula, with the message "Title is required, and Due date must be on or after Start date.":

  ```
  =AND(NOT(ISBLANK(Title)),OR(ISBLANK([Due date]),ISBLANK([Start date]),[Due date]>=[Start date]))
  ```

  A write that breaks it is rejected for everyone, including grid edits and REST calls.

### How the button rows and the edit order work

- Each button sets a screen variable (`locProgress` or `locPhase`) to its own label. The original dropdown stays in the card, hidden outside view mode, with `DefaultSelectedItems` set to `If(IsBlank(locProgress), Parent.Default, {Value: locProgress})`. The card still saves the dropdown's value, so the form rules that read it keep working.
- The button labels are typed in, not read from the list. If the Progress or Phase choices change in the list, edit the buttons to match (`Button1` to `Button1_4` in the Progress card, `Button1_5` to `Button1_7` in the Phase card).
- The variables are cleared in the form's `OnReset`. `SharePointIntegration.OnNew`, `OnEdit` and `OnView` call `ResetForm(SharePointForm1)` before opening the form, because `UpdateContext` is not allowed in those handlers. Without this, a click on one item would show on the next item opened.
- Each card's `Y` is its order in the form and accepts a formula. The Work item and People cards use `If(SharePointForm1.Mode = FormMode.Edit, <edit order>, <normal order>)`. Cards that share a row have the same `Y` and different `X`.
- The banner chips are one HTML text control (`HtmlText2`), so they size and wrap on their own.

### Editing gotchas

- Studio opens read-only when an earlier session still holds the edit lock; "Override" takes it over.
- A new button has `BorderStyle.None`; set `BorderStyle.Solid` or the border colour and thickness do nothing.
- The blue border on inputs is `HoverBorderColor`, not the focus border.
- Changing a combo box's `Items` resets its `DisplayFields` and `SearchFields`; set both back to `["DisplayName"]`.
- A card must be unlocked (Advanced tab) before its controls' formulas can be changed.
- Studio's preview cannot show view mode, and in a fresh session it may show "No item to display". Check view mode on the live list after publishing.

**Undo (form):** List settings ▸ Form settings ▸ "Use the default SharePoint form" (and, if wanted, "Delete custom form"). The section 2 formatting then shows again. To drop the list-level rules as well, clear the list's validation formula and set the Title column back to not required.

## 5. The assignment notification flow (12 Nov 2026)

A Power Automate cloud flow, "Progress tracker: tell the assignee" (flow id `85c8d5e0-383b-4f83-a48e-3e378ae90a86`, default environment, owned by the list owner). It sends the assignee a Teams chat message from the Flow bot when a work item is assigned to them.

- **Trigger:** SharePoint "When an item is created or modified" on this list.
- **Change check:** "Get changes for an item or a file (properties only)" with the item's ID and the Trigger Window Start Token.
- **Condition**, all must hold:
  - "Assigned to" has an email;
  - "Assigned to" changed in this edit, or the item is new (Created equals Modified);
  - the assignee is not the person who made the change;
  - the run was not caused by the notes-page flow writing its link (section 6): "Project notes" is empty, or it did not change in this edit and Created differs from Modified.
- **Message:** a bold heading, the item title, a list (Progress, Phase, Priority, Due date, Assigned by) and a link to the item. It is one `concat(...)` expression holding HTML.

What this means for the skill: a row the skill creates or updates for the signed-in person sends nothing, because the assignee and the editor are the same person. A row created for someone else would message them.

Gotchas found while building it in the new designer:

- The expression editor often shows "This expression has a problem" on a valid expression; a second click on Add accepts it. Check Code view afterwards, because a silent failure leaves the field empty.
- The Teams connection must be signed in under an account whose Teams can reach the assignees. An expired connection fails the run with "Unauthorized".
- The trigger polls about once a minute. Two edits inside one window make one run.

**Undo:** My flows ▸ the flow ▸ Turn off (or Delete).

## 6. A notebook page for every work item (12 Nov 2026)

Each work item has a page in the ITG Notebook (`/sites/ITG/SiteAssets/ITG Notebook`), section "Projects". Status stays in the tracker; the page holds what stays true for months.

- **Column:** "Project notes" (`ProjectNotes`, multi-line plain text, because a OneNote link is 200 to 240 characters and a Hyperlink column stops at 255). Column formatting shows it as an "Open notes" link. It is in the views All Items, Grouped by work item progress and Grouped by priority.
- **Flow:** "Progress tracker: create project notes pages" (flow id `f639f77f-4edc-4ede-8978-2814941ab64e`, default environment, owned by the list owner).
  - Trigger: SharePoint "When an item is created", one run at a time.
  - Delay of 2 minutes, so the assignment notification (section 5) sees the new item first.
  - Get items, then keep the items whose "Project notes" is empty. So one run also gives a page to any older item that lacks one.
  - For each: build the page HTML in a Compose step, OneNote (Business) "Create page in a section", then write the page's link to the item with "Send an HTTP request to SharePoint" (`validateUpdateListItem`, `bNewDocumentUpdate: true`).
- **Form button:** "Project notes" on the banner's chip line, right-aligned (`Button1_8` in `DataCard6`, white outline on black). `OnSelect = Launch(ThisItem.'Project notes')`. It is hidden on a new item and while the link is empty.
- **Page:** the item's title, a link back to the tracker item, Business, "Owner at creation", the Description, and empty headings: Purpose and scope, How it works, Key decisions, Links and files, Open questions.
  - Under each heading sits a named block (`data-id` of `purpose`, `how`, `decisions`, `links`, `questions`) holding the line "Not written yet.". The names let a flow add text to one section (section 7). Pages made before 12 Nov 2026 14:30 UTC have no named blocks.

What this means for the skill: read `ProjectNotes`, never write it. Clearing it makes the next run create a second page.

Gotchas, all met on 12 Nov:

- `bNewDocumentUpdate: true` overwrites the item's current version in place. It makes no new version, but it **does reset "Modified" and "Modified by"** unless the same call sends them. The flow sends both: `Modified` as the item's own time in the site's time zone (`M/d/yyyy h:mm tt`; seconds are refused) and `Editor` as `[{"Key":"<claims>"}]`. So after the link is written, "Modified" is rounded down to the minute.
- An in-place overwrite still fires "created or modified" triggers, and "Get changes" then compares the previous version with the overwritten one. The item's last real edit shows up as if it had just happened. The first backfill sent one false "assigned to you" message this way; the last condition in section 5 is the guard.
- The OneNote action's rich-text field strips `<html>` and `<head>`, which loses the page title. Build the full HTML in a Compose step and pass its output.
- Renaming a work item does not rename its page; deleting an item leaves its page. Owner and Description on the page are a snapshot.

**Undo:** turn off or delete the flow; delete the column; delete the Projects section. Remove the guard condition from the section 5 flow if the column goes.

## 7. Writing to the notebook pages (12 Nov 2026)

The `project-notes` skill fills in the pages of section 6. It cannot reach OneNote itself, so it leaves a request in a list and a flow carries it out.

- **List:** "Project notes requests" (`/sites/ITG/Lists/ProjectNotesRequests`, hidden from the site menu). Columns: `Title`, `TrackerItemId`, `Section` (the kind of request: `read`, `fill` or `rebuild`), `Content`, `Expected`, `RequestStatus` (Pending, Done or Refused) and `Result`. It doubles as the log of what was written, by whom and when.
- **Flow:** "Progress tracker: write project notes" (flow id `5725eb07-7124-429c-acc8-b14e092e2165`, default environment, owned by the list owner). Trigger: "When an item is created" on the request list. It finds the work item's page by the link in "Project notes", reads the page, then:
  - **refuses** unless the person who made the request is the work item's assignee;
  - `read`: returns the page's created and modified dates and its HTML in `Result`;
  - `fill` and `rebuild`: refuses unless the page's HTML still equals `Expected`, the HTML the skill read (line breaks and tabs ignored);
  - `fill`: runs the OneNote "Update page content" commands in `Content`. The skill only sends `append` commands aimed at the named blocks;
  - `rebuild`: creates a new page from the HTML in `Content`, writes its link to the work item (keeping "Modified" and "Modified by", as in section 6), then deletes the old page.
- **Who decides what may be written:** `skills/project-notes/notes.js`, in the browser.
  - It allows `rebuild` only while the page says exactly what the page flow or the last `rebuild` put there, word for word.
  - Once a person has typed anything, it allows `fill` only, and only for sections that are still empty.
  - The flow does not repeat this check, so a request made by hand could rebuild an edited page of the requester's own work item.

What OneNote allows, found by testing on 12 Nov:

- A flow **cannot replace** part of a page. "Update page content" refuses `replace` on a block addressed by its `data-id` ("The PATCH target DIV for action replace is not supported"). Replacing needs ids that OneNote generates, and no standard connector returns them: "Get page content" leaves them out, and the Office 365 Groups connector's Graph request is refused for OneNote ("does not contain a valid authentication token"). Hence rebuild-or-fill.
- `append` to a block addressed as `#<data-id>` works.
- A page's `lastModifiedTime` **does not change** when a person types on the page in OneNote for the web. Never use it to tell whether a page was edited. The flow still carries a date check from before this was known; it never fires.
- OneNote returns an empty line as `&#160;` and restyles everything, so compare pages by their text, never by their HTML, except for the `Expected` check, where both sides are OneNote's own output.
- A rebuilt page gets a new address and loses its version history.
- Pages are written under the flow owner's name, whoever asked. The request list shows who asked.

**Undo:** turn off or delete the flow; delete the request list. Pages already written stay as they are.
