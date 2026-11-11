# Browser snippets for the ITG "Progress tracker list"

Run each with `mcp__claude-in-chrome__javascript_tool` (`action: "javascript_exec"`) in a tab open on the list, so the calls use the user's own SharePoint session. Every snippet starts with:

```js
const site = "/sites/ITG";
const base = `${site}/_api/web/lists/getbytitle('Progress tracker list')`;
const nm = "application/json;odata=nometadata";
```

Columns (internal names): `Title`, `Summary`, `Notes` (plain multi-line text), `Description` (rich text: send one HTML paragraph, `<p>…</p>`), `AssignedTo0` (one person: write `AssignedTo0Id` with the person's site user id), `Progress` (Not started / In progress / Completed / Blocked / Behind), `Phase` (Discover / Design / Deliver), `Business` (Corporate / Versatex / XLC / FX / Foxx Construction), `ProjectPeople` (text), `Priority`, `StartDate`, `DueDate`, `KeyStakeholders`, `Category0`. Others edit this list too.

## Read every row, with its etag

```js
const answer = await fetch(base + "/items?$top=500&$select=Id,Title,Summary,Notes,Description,AssignedTo0Id,Progress,Phase,Business,ProjectPeople",
  {headers: {Accept: "application/json;odata=minimalmetadata"}}).then(r => r.json());
const me = await fetch(site + "/_api/web/currentuser?$select=Id,Title", {headers: {Accept: nm}}).then(r => r.json());
({me, rows: answer.value.map(i => ({id: i.Id, etag: i["odata.etag"], title: i.Title, summary: i.Summary, notes: i.Notes,
  description: i.Description, assignedId: i.AssignedTo0Id, progress: i.Progress, phase: i.Phase, business: i.Business,
  people: i.ProjectPeople}))})
```

`me.Id` is the signed-in user's site id, the value for `AssignedTo0Id`. If `me.Title` is not the settings' `assigned_to.name`, stop and ask: someone else is signed in. (On a first run there is no `assigned_to` yet; save it with `tracker.py person`.)

Keep each row's `etag` from this read for the write. `odata=nometadata` leaves the etag out.

## Write the approved batch

Fill `updates` and `creates` with exactly what the user approved. Write the strings as JSON: double quotes, `\n` between lines of Notes. An update sends only the fields that change.

```js
const updates = [/* {id: 10, etag: "\"3\"", fields: {Notes: "Status 12 Nov 2026:\n• ..."}} */];
const creates = [/* {Title: "...", Summary: "...", Description: "<p>...</p>", AssignedTo0Id: <me.Id>, Business: "Versatex", Phase: "Design", Progress: "In progress", ProjectPeople: "<people_default>", Notes: "..."} */];
const digest = (await fetch(site + "/_api/contextinfo", {method: "POST", headers: {Accept: nm}}).then(r => r.json())).FormDigestValue;
const results = [];
for (const u of updates) {
  const r = await fetch(`${base}/items(${u.id})`, {method: "POST", body: JSON.stringify(u.fields), headers: {
    Accept: nm, "Content-Type": nm, "X-RequestDigest": digest, "X-HTTP-Method": "MERGE", "IF-MATCH": u.etag}});
  results.push({id: u.id, status: r.status});
}
for (const c of creates) {
  const r = await fetch(`${base}/items`, {method: "POST", body: JSON.stringify(c), headers: {
    Accept: nm, "Content-Type": nm, "X-RequestDigest": digest}});
  const body = await r.json();
  results.push({title: c.Title, status: r.status, id: body.Id, error: body["odata.error"]});
}
results
```

- 204: updated. 201: created; `id` is the new row.
- 412: someone changed the row after the preview read. Nothing was written to it. Read it again, show the user that row again, and ask again.
- Anything else: stop and report the status. Never retry a create blindly: check first whether the row now exists.

## Check what changed

```js
const id = 10;
const keys = ["Title", "Summary", "Notes", "Description", "AssignedTo0", "Progress", "Phase", "Business", "ProjectPeople"];
const versions = await fetch(`${base}/items(${id})/versions?$select=VersionLabel,${keys.join(",")}`,
  {headers: {Accept: nm}}).then(r => r.json());
const [latest, before] = versions.value;
const same = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
({version: latest.VersionLabel, previous: before && before.VersionLabel,
  changed: keys.filter(k => !same(latest[k], before && before[k]))})
```

The newest version comes first. `changed` must list exactly the approved fields.
