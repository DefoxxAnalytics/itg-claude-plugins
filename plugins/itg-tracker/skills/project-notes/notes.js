/* Reads and builds ITG Notebook project pages for the project-notes skill.
 *
 * Loaded into a SharePoint tab (it sets window.Notes) and into Node for its tests. Page HTML stays in the page,
 * in Notes.pages, and never passes through the conversation: the functions return short summaries only.
 */
(function (root) {
  const SECTIONS = [
    ["purpose", "Purpose and scope"],
    ["how", "How it works"],
    ["decisions", "Key decisions"],
    ["links", "Links and files"],
    ["questions", "Open questions"],
  ];
  const PLACEHOLDERS = ["", "Not written yet."];
  const SITE = "/sites/ITG";
  const JSON_PLAIN = "application/json;odata=nometadata";
  const REQUESTS = `${SITE}/_api/web/lists/getbytitle('Project notes requests')/items`;
  const TRACKER = "https://defoxx365.sharepoint.com/sites/ITG/Lists/Progress%20tracker%20list/DispForm.aspx?ID=";

  function escapeHtml(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function plainText(html) {
    return String(html || "")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(p|li|h\d|div|title)>/gi, "\n")
      .replace(/<[^>]+>/g, "")
      .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
      .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
      .replace(/&nbsp;/g, " ")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&amp;/g, "&")
      .split("\n")
      .map((line) => line.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join("\n");
  }

  /** What the flow returns for a "read" request: a line of dates, then the page's HTML. */
  function parsePage(result) {
    const cut = result.indexOf("\n");
    const dates = /^created=([^;]+);modified=(.+)$/.exec(result.slice(0, cut).trim());
    if (!dates) throw new Error("Not a page read: the first line has no dates");
    const html = result.slice(cut + 1);
    const sections = {};
    for (const [key] of SECTIONS) {
      const found = new RegExp(`<div data-id="${key}"[^>]*>([\\s\\S]*?)</div>`).exec(html);
      if (!found) continue;
      const text = plainText(found[1]);
      sections[key] = { text, empty: PLACEHOLDERS.includes(text) };
    }
    return {
      created: dates[1],
      layout: Object.keys(sections).length === SECTIONS.length ? "named" : "old",
      sections,
      html,
    };
  }

  function wording(html) {
    return plainText(html).split("\n").filter((line) => !PLACEHOLDERS.includes(line)).join("\n");
  }

  /** True when the page says exactly what `expectedHtml` says. OneNote's page dates do not move when a person
   *  types on a page, so the wording is the only evidence that nobody has. */
  function untouched(page, expectedHtml) {
    return wording(page.html) === wording(expectedHtml);
  }

  /** Plain text to page HTML: lines starting with a bullet become a list, every other line a paragraph. */
  function sectionHtml(text) {
    const parts = [];
    let items = [];
    const closeList = () => {
      if (items.length) parts.push(`<ul>${items.join("")}</ul>`);
      items = [];
    };
    for (const line of String(text || "").split("\n").map((each) => each.trim()).filter(Boolean)) {
      const bullet = /^[•\-*]\s+(.*)$/.exec(line);
      if (bullet) {
        items.push(`<li>${escapeHtml(bullet[1])}</li>`);
      } else {
        closeList();
        parts.push(`<p>${escapeHtml(line)}</p>`);
      }
    }
    closeList();
    return parts.join("");
  }

  /** A whole page, in the layout of the flow that creates pages. Sections without text keep an empty line. */
  function buildPage(page) {
    const body = SECTIONS.map(([key, heading]) => {
      const inner = sectionHtml(page.sections && page.sections[key]) || "<p>&nbsp;</p>";
      return `<h2>${heading}</h2><div data-id="${key}">${inner}</div>`;
    }).join("");
    return (
      `<html><head><title>${escapeHtml(page.title)}</title></head><body>` +
      `<p><a href="${TRACKER}${Number(page.row)}">Open the tracker item</a></p>` +
      "<p><i>Status lives in the tracker. Keep client data out of this page.</i></p>" +
      `<p><b>Business:</b> ${escapeHtml(page.business || "Not set")}<br/>` +
      `<b>Owner at creation:</b> ${escapeHtml(page.owner || "Unassigned")}</p>` +
      `<h2>Description</h2>${sectionHtml(plainText(page.description)) || "<p>None yet.</p>"}` +
      `${body}</body></html>`
    );
  }

  /** Commands that add text to named sections and touch nothing else. */
  function fillCommands(sections) {
    return SECTIONS.filter(([key]) => sections[key]).map(([key]) => ({
      target: `#${key}`,
      action: "append",
      content: sectionHtml(sections[key]),
    }));
  }

  /** Which sections a write may touch, and how: "rebuild" the page, "fill" empty sections, or nothing. */
  function plan(page) {
    const keys = SECTIONS.map(([key]) => key);
    if (page.untouched === true) return { mode: "rebuild", writable: keys, reason: "Nobody has edited this page." };
    if (page.layout === "old") return { mode: "none", writable: [], reason: "People have edited this page and it has the old layout, so its sections cannot be addressed." };
    const writable = keys.filter((key) => page.sections[key].empty);
    return { mode: writable.length ? "fill" : "none", writable, reason: "People have edited this page: only empty sections can be filled." };
  }

  const pages = {};

  async function getJson(url) {
    return (await fetch(url, { headers: { Accept: JSON_PLAIN } })).json();
  }

  async function ask(body) {
    const context = await fetch(`${SITE}/_api/contextinfo`, { method: "POST", headers: { Accept: JSON_PLAIN } });
    const digest = (await context.json()).FormDigestValue;
    const response = await fetch(REQUESTS, {
      method: "POST",
      headers: { Accept: JSON_PLAIN, "Content-Type": JSON_PLAIN, "X-RequestDigest": digest },
      body: JSON.stringify(body),
    });
    const created = await response.json();
    if (!response.ok) throw new Error(`Request not created: ${response.status}`);
    return created.Id;
  }

  async function answer(id, seconds) {
    for (let waited = 0; waited < seconds; waited += 4) {
      const request = await getJson(`${REQUESTS}(${id})?$select=RequestStatus,Result`);
      if (request.RequestStatus !== "Pending") return request;
      await new Promise((resolve) => setTimeout(resolve, 4000));
    }
    return { RequestStatus: "Pending", Result: "" };
  }

  /** The page the skill last built for this row, or null when it never has. */
  async function lastBuilt(row) {
    const filter = `TrackerItemId eq ${Number(row)} and Section eq 'rebuild' and RequestStatus eq 'Done'`;
    const found = await getJson(`${REQUESTS}?$select=Id,Content&$filter=${encodeURIComponent(filter)}&$orderby=Id desc&$top=1`);
    return found.value.length ? found.value[0].Content : null;
  }

  /** Starts a read; returns the request id at once, because the flow takes up to a few minutes. */
  async function startRead(row, title) {
    return ask({ Title: title, TrackerItemId: row, Section: "read" });
  }

  /** The page's state once its read is answered, without its HTML. Call again while `pending`.
   *  `details` is the tracker row as it is now: {title, business, owner, description}. */
  async function finishRead(row, id, details, seconds = 30) {
    const request = await answer(id, seconds);
    if (request.RequestStatus === "Pending") return { row, pending: true };
    if (request.RequestStatus !== "Done") return { row, refused: request.Result };
    const page = parsePage(request.Result);
    const expected = (await lastBuilt(row)) || buildPage({ ...details, row, sections: {} });
    page.untouched = untouched(page, expected);
    pages[row] = page;
    const summary = {};
    for (const [key, section] of Object.entries(page.sections)) summary[key] = section.empty ? "" : section.text;
    return { row, layout: page.layout, untouched: page.untouched, plan: plan(page), sections: summary };
  }

  /** Sends the approved text for one page. `details` is {title, business, owner, description, sections}. */
  async function startWrite(row, details) {
    const page = pages[row];
    if (!page) throw new Error("Read the page first");
    const choice = plan(page);
    const sections = {};
    for (const key of choice.writable) if (details.sections[key]) sections[key] = details.sections[key];
    if (choice.mode === "none" || !Object.keys(sections).length) return { row, mode: "none", reason: choice.reason };
    const content =
      choice.mode === "rebuild"
        ? buildPage({ ...details, row, sections })
        : JSON.stringify(fillCommands(sections));
    const id = await ask({ Title: details.title, TrackerItemId: row, Section: choice.mode, Content: content, Expected: page.html });
    delete pages[row];
    return { row, mode: choice.mode, id, sections: Object.keys(sections) };
  }

  async function finishWrite(row, id, seconds = 30) {
    const request = await answer(id, seconds);
    if (request.RequestStatus === "Pending") return { row, pending: true };
    return { row, status: request.RequestStatus, result: request.RequestStatus === "Done" ? "written" : request.Result };
  }

  const api = {
    SECTIONS, parsePage, plainText, untouched, sectionHtml, buildPage, fillCommands, plan, pages,
    startRead, finishRead, startWrite, finishWrite,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Notes = api;
})(typeof window !== "undefined" ? window : globalThis);
