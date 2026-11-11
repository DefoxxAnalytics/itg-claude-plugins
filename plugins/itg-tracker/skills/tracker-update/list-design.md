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

## 2. The branded form

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
