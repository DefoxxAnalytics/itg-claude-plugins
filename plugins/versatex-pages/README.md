# versatex-pages

Builds Versatex-branded standalone HTML pages from Claude Code: guides, briefs, one-pagers, notes for a client or the team. Each page is one file with the Roboto fonts, the logo and the favicon inside it, so it opens offline, travels as an email attachment, prints cleanly and reads well on a phone.

## Install

```
/plugin marketplace add DefoxxAnalytics/itg-claude-plugins
/plugin install versatex-pages@itg-plugins
```

If you already have the `itg-plugins` marketplace (for `itg-tracker`), only the second line is needed. Start a new session afterwards.

## Use

Ask Claude for a branded page ("make this a Versatex one-pager", "turn these notes into a branded guide I can attach"), or run `/versatex-pages:branded-page`. Claude writes the page from your content, builds it, checks it against the brand rules and gives you the path. Nothing is sent or shared: you attach the file yourself.

Other skills use it too: itg-tracker's `project-brief` builds its brief through this kit.

Needs Python 3.9 or later (`python3` on a Mac). Nothing to install.

## What it checks

`page.py check` fails a page that loads anything from the network, uses yellow as a text colour, uses navy, or lacks a title, a language, a phone viewport or alt text on an image. It warns about a table that will not scroll on a phone, a font other than Roboto, and a page over 2 MB.

## Versions

| Version | What came with it |
|---|---|
| 1.0.0 | The `branded-page` skill: `page.py build` and `check`, the component page, the brand assets |

## For maintainers

- **Run the tests** from the repository root: `python -m pytest plugins/versatex-pages/tests -q`
- **See every component:** `python plugins/versatex-pages/skills/branded-page/page.py build plugins/versatex-pages/skills/branded-page/components.html --title Components --out plugins/versatex-pages/tests/preview/components.html` (the `preview` folder is not committed).
- **The assets** in `skills/branded-page/assets/` are copies from the Versatex brand folder (`versatex-web-assets`): Roboto latin 400/500/700/900 woff2 with its licence (`OFL-LICENSE.txt` must stay with the fonts), `svg/versatex-horizontal-light.svg` and `favicon/favicon.svg`. This plugin is the versioned copy; to refresh them, copy the same files over and run the tests.
- **The CSS** started from the itg-tracker quick start page. Keep components in `versatex-page.css` and show each new one in `components.html`, with a note on when to use it.
- **Release:** raise `version` in `.claude-plugin/plugin.json` and add a line to the table above.
