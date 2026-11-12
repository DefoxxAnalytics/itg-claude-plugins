const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const notes = require(path.join(__dirname, "..", "skills", "project-notes", "notes.js"));

const STYLE = ' style="margin-top:5.5pt;margin-bottom:5.5pt"';
const DATES = "created=2026-11-12T14:47:24Z;modified=2026-11-12T14:47:24Z";
const DETAILS = { title: "Alpha", row: 7, business: "Versatex", owner: "Lovelace, Ada", description: "<p>What it is.</p>" };

function oneNotePage(sections, { named = true } = {}) {
  const body = notes.SECTIONS.map(([key, heading]) => {
    const inner = `\r\n\t\t\t\t<p${STYLE}>${sections[key] ?? "Not written yet."}</p>\r\n\t\t\t`;
    return `<h2${STYLE}>${heading}</h2>\r\n\t\t\t` + (named ? `<div data-id="${key}">${inner}</div>` : inner);
  }).join("\r\n\t\t\t");
  return (
    '<html lang="en-US">\r\n\t<head>\r\n\t\t<title>Alpha</title>\r\n\t</head>\r\n\t<body>\r\n\t\t' +
    `<div data-id="_default" style="position:absolute">\r\n\t\t\t${body}\r\n\t\t</div>\r\n\t</body>\r\n</html>\r\n`
  );
}

function read(sections, options) {
  return `${DATES}\n${oneNotePage(sections, options)}`;
}

function asOneNoteReturns(html) {
  const restyled = html
    .replace(/<p>/g, `<p${STYLE}>`)
    .replace(/<b>(.*?)<\/b>/g, '<span style="font-weight:bold">$1</span>')
    .replace(/&nbsp;/g, "&#160;")
    .replace(/<\/(p|h2|ul|div)>/g, "</$1>\r\n\t\t\t");
  return `${DATES}\n${restyled}`;
}

test("a fresh page has five empty named sections", () => {
  const page = notes.parsePage(read({}));
  assert.equal(page.layout, "named");
  assert.deepEqual(Object.keys(page.sections), ["purpose", "how", "decisions", "links", "questions"]);
  assert.ok(Object.values(page.sections).every((section) => section.empty));
});

test("an empty line counts as empty too, however OneNote writes it", () => {
  const page = notes.parsePage(read({ how: "&nbsp;", links: "&#160;", questions: "&#xA0;" }));
  assert.deepEqual(["how", "links", "questions"].map((key) => page.sections[key].empty), [true, true, true]);
});

test("numbered character codes are read as their characters", () => {
  assert.equal(notes.plainText("Caf&#233; &#x2014; 5 &#38; 6"), "Café — 5 & 6");
});

test("text in a section is read without its markup", () => {
  const page = notes.parsePage(read({ purpose: 'Tracks <span style="font-weight:bold">spend</span> &amp; savings' }));
  assert.deepEqual(page.sections.purpose, { text: "Tracks spend & savings", empty: false });
});

test("the page keeps its html, line breaks included, for the flow to compare", () => {
  const result = read({});
  assert.equal(notes.parsePage(result).html, result.slice(result.indexOf("\n") + 1));
});

test("a read without the dates line is refused", () => {
  assert.throws(() => notes.parsePage("<html></html>"));
});

test("a page that still says what the skill wrote is untouched, however OneNote restyles it", () => {
  const written = notes.buildPage({ ...DETAILS, sections: { purpose: "Why it exists", how: "• one\n• two" } });
  const page = notes.parsePage(asOneNoteReturns(written));
  assert.equal(notes.untouched(page, written), true);
});

test("one line added by a person makes the page touched, though its dates say nothing", () => {
  const written = notes.buildPage({ ...DETAILS, sections: { purpose: "Why it exists" } });
  const edited = written.replace('<div data-id="links"><p>&nbsp;</p>', '<div data-id="links"><p>&nbsp;A person wrote this line.</p>');
  assert.notEqual(edited, written);
  assert.equal(notes.untouched(notes.parsePage(asOneNoteReturns(edited)), written), false);
});

test("a page nobody has written on matches the page the flow makes, in either layout", () => {
  const template = notes.buildPage({ ...DETAILS, sections: {} });
  const placeholder = template.replace(/<p>&nbsp;<\/p>/g, "<p>Not written yet.</p>");
  const oldLayout = template.replace(/<div data-id="[a-z]+">(.*?)<\/div>/g, "$1");
  assert.notEqual(oldLayout, template);
  for (const html of [template, placeholder, oldLayout]) {
    assert.equal(notes.untouched(notes.parsePage(asOneNoteReturns(html)), template), true);
  }
});

test("a page whose description no longer matches the tracker counts as touched", () => {
  const page = notes.parsePage(asOneNoteReturns(notes.buildPage({ ...DETAILS, sections: {} })));
  const expected = notes.buildPage({ ...DETAILS, description: "<p>Changed since.</p>", sections: {} });
  assert.equal(notes.untouched(page, expected), false);
});

test("an untouched page is rebuilt, whatever its layout", () => {
  const choice = notes.plan({ ...notes.parsePage(read({}, { named: false })), untouched: true });
  assert.equal(choice.mode, "rebuild");
  assert.equal(choice.writable.length, 5);
});

test("on a page people edited, only the empty sections can be filled", () => {
  const page = { ...notes.parsePage(read({ purpose: "Ours", how: "&nbsp;" })), untouched: false };
  assert.deepEqual(notes.plan(page), {
    mode: "fill",
    writable: ["how", "decisions", "links", "questions"],
    reason: "People have edited this page: only empty sections can be filled.",
  });
});

test("an edited page with no empty section, or with the old layout, is left alone", () => {
  const full = Object.fromEntries(notes.SECTIONS.map(([key]) => [key, "Written"]));
  assert.equal(notes.plan({ ...notes.parsePage(read(full)), untouched: false }).mode, "none");
  assert.equal(notes.plan({ ...notes.parsePage(read({}, { named: false })), untouched: false }).mode, "none");
});

test("a page is never rebuilt before it is known to be untouched", () => {
  assert.equal(notes.plan(notes.parsePage(read({}, { named: false }))).mode, "none");
});

test("text becomes paragraphs and lists, with markup made harmless", () => {
  const html = notes.sectionHtml("Why <b>it</b> exists & more\n• first\n- second\nAfter");
  assert.equal(html, "<p>Why &lt;b&gt;it&lt;/b&gt; exists &amp; more</p><ul><li>first</li><li>second</li></ul><p>After</p>");
});

test("a built page reads back as what was put in", () => {
  const html = notes.buildPage({
    title: "Alpha & <Beta>", row: 7, business: "Versatex", owner: "Lovelace, Ada",
    description: '<div class="ExternalClass"><p>What it is.</p></div>',
    sections: { purpose: "Why it exists", decisions: "• one\n• two" },
  });
  assert.ok(html.startsWith("<html><head><title>Alpha &amp; &lt;Beta&gt;</title></head><body>"));
  assert.ok(html.includes('DispForm.aspx?ID=7">Open the tracker item</a>'));
  assert.ok(html.includes("<h2>Description</h2><p>What it is.</p>"));
  assert.ok(!html.includes("ExternalClass"));
  const page = notes.parsePage(`${DATES}\n${html}`);
  assert.equal(page.layout, "named");
  assert.equal(page.sections.purpose.text, "Why it exists");
  assert.equal(page.sections.decisions.text, "one\ntwo");
  assert.equal(page.sections.how.empty, true);
});

test("fill commands only add to the named sections they are given", () => {
  assert.deepEqual(notes.fillCommands({ how: "Runs nightly", unknown: "ignored" }), [
    { target: "#how", action: "append", content: "<p>Runs nightly</p>" },
  ]);
});
