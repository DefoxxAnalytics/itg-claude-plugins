---
name: branded-page
description: Use when the user asks for a Versatex-branded page, guide, one-pager, note or standalone HTML file to send or attach, or runs /branded-page. Builds one self-contained HTML file (fonts and logo inside, phone and print ready) from content Claude writes with the kit's components, and checks it against the brand rules. Other skills hand it a body to wrap. For a brief of ITG tracker projects, use itg-tracker's project-brief instead.
---

# Branded page

Turns content into one Versatex-branded HTML file that needs nothing else: the Roboto fonts, the logo and the favicon are inside it, so it works offline, as an email attachment and in print, and it reads well on a phone.

Files in `${CLAUDE_SKILL_DIR}`:
- `page.py` builds a page from a body fragment (`build`) and checks a built page (`check`). Standard library only.
- `components.html` shows every component with a note on when to use it. Write bodies from it.
- `versatex-page.css` is the kit's CSS; `page.py` puts it in every page.
- `assets/` holds the fonts, the logo and the favicon.

**On a Mac:** use `python3` wherever this skill says `python`.

**Never invent content.** Everything on the page comes from the user, their files or the skill that called this one. If something is missing, ask or leave it out; don't fill gaps with plausible text.

## Brand rules

From the Versatex brand guide:
- Black `#231F20`, yellow `#FDC00F`, white, and greys. **Yellow is an accent only**: fills, rules and markers; never text, links or hover states.
- **No navy** (`#1e3a8a` is the old analytics theme, not a brand colour), and no other accent colours.
- Roboto only: 900 for headings, 400 for text, 500 and 700 for emphasis.
- Hexagons standing on a point are the motif: `hex-num`, `hex-list`, `hex`.
- Nothing loads from the network: no web fonts, CDN scripts or remote images. An image goes in as a `data:` URI.

## 1. Content and destination

- What goes on the page: the user's text, a Markdown file, data or notes. If the user gives Markdown, convert it to the kit's components yourself; nothing needs installing.
- The title (two to six words), the band label (topic, such as "ITG · Project check-in"), and a one-sentence description.
- Where to save it: next to the source file when there is one, otherwise `~/Documents`. Use a short, lower-case, hyphenated file name.

## 2. Write the body

Read `components.html` and write the body to the scratchpad. The body is what goes inside `<main>`:
- no `<html>`, `<head>`, `<body>` or `<script>`: `page.py` refuses them;
- start with the `intro`, then one `section` per topic, then a `footer` that says where the content came from and when;
- wrap every table in `<div class="table-wrap">`; give a wide table `class="wide"` so it scrolls on a phone; set column widths with `<colgroup>`;
- escape `&`, `<` and `>` in text.

## 3. Build

```bash
python "${CLAUDE_SKILL_DIR}/page.py" build <body.html> --title "<title>" --label "<band label>" --description "<one sentence>" --out <path.html>
```

Options: `--width 820` for a narrower text page (default 960); `--css <file>` for CSS this page alone needs. Prefer the kit's components to extra CSS.

## 4. Check

```bash
python "${CLAUDE_SKILL_DIR}/page.py" check <path.html>
```

Exit 1 lists errors (external files, yellow text, navy, a missing title or alt text). Fix the body and build again until it says OK. Fix warnings too unless there is a reason not to, and say what it is.

## 5. Look at it (when the browser tools are available)

Browsers here block `file://`. Serve the folder on 127.0.0.1 (`python -m http.server 8765 --bind 127.0.0.1 --directory <folder>`), open the page, and take a screenshot at 1280 px and at 390 px wide. Look for overflow, wrapped headings and empty sections. Stop the server afterwards.

## 6. Finish

Give the full path and the size. The user sends or shares the file themselves.

## For other skills

A skill that makes its own body (such as itg-tracker's project-brief) loads this skill for the path of `page.py`, then runs steps 3 and 4 with its body.
