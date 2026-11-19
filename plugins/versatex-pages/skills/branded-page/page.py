"""Build and check Versatex-branded standalone HTML pages.

    python page.py build BODY.html --title T --out OUT.html [--label L] [--description D] [--width 820] [--css extra.css]
    python page.py check OUT.html

`build` wraps a body fragment in one self-contained page: the Roboto fonts, the logo and
the favicon are embedded, so the file works offline, as an attachment and in print.
`check` exits 1 when the page breaks a brand or self-containment rule.
"""
import argparse
import base64
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
KIT_CSS = HERE / "versatex-page.css"
FONT_WEIGHTS = (400, 500, 700, 900)
MAX_BYTES = 2 * 1024 * 1024
KIT_STYLE_ID = "versatex-kit"

HTML_COMMENT = re.compile(r"<!--.*?-->[ \t]*\n?", re.S)
WHOLE_DOCUMENT_TAG = re.compile(r"<\s*/?\s*(html|head|body|script)\b", re.I)
YELLOW_TEXT = re.compile(
    r"(?<![\w-])color\s*:\s*(#fdc00f\b|#fdc00fff\b|var\(\s*--yellow\s*\)|rgba?\(\s*253\s*,\s*192\s*,\s*15\b)", re.I)
NAVY = re.compile(r"#1e3a8a\b", re.I)
CSS_IMPORT = re.compile(r"@import\b", re.I)
CSS_REMOTE_URL = re.compile(r"url\(\s*['\"]?\s*(https?:)?//", re.I)
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)
ALLOWED_FONTS = ("roboto", "var(--font)", "var(--mono)", "monospace", "inherit")

COPY_SCRIPT = """<script>
function copyWithSelection(text) {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const copied = document.execCommand("copy");
  area.remove();
  return copied;
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const text = document.getElementById(button.dataset.copy).textContent;
    let copied;
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (clipboardUnavailable) {
      copied = copyWithSelection(text);
    }
    button.textContent = copied ? "Copied" : "Select and copy";
    setTimeout(() => { button.textContent = "Copy"; }, 1600);
  });
});
</script>
"""


class BodyError(ValueError):
    pass


def data_uri(path, mime):
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def font_faces():
    return "\n".join(
        f'@font-face {{ font-family: "Roboto"; font-style: normal; font-weight: {weight}; font-display: swap; '
        f'src: url({data_uri(ASSETS / f"roboto-latin-{weight}-normal.woff2", "font/woff2")}) format("woff2"); }}'
        for weight in FONT_WEIGHTS)


def build_page(body, title, label="", description="", width=None, extra_css=""):
    if not title.strip():
        raise BodyError("A page needs a title.")
    body = HTML_COMMENT.sub("", body)
    found = WHOLE_DOCUMENT_TAG.search(body)
    if found:
        raise BodyError(f"The body must be a fragment: it contains <{found.group(1).lower()}>. "
                        "Give only what goes inside <main>; the kit adds the page around it.")

    head = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="light">',
        f"<title>{html.escape(title.strip())}</title>",
    ]
    if description.strip():
        head.append(f'<meta name="description" content="{html.escape(description.strip())}">')
    head.append(f'<link rel="icon" type="image/svg+xml" href="{data_uri(ASSETS / "favicon.svg", "image/svg+xml")}">')

    kit_css = KIT_CSS.read_text(encoding="utf-8").strip()
    if width:
        kit_css += f"\n:root {{ --width: {int(width)}px; }}"
    head.append(f'<style id="{KIT_STYLE_ID}">\n{font_faces()}\n\n{kit_css}\n</style>')
    if extra_css.strip():
        head.append(f"<style>\n{extra_css.strip()}\n</style>")
    head.append("</head>")

    label_html = f'\n    <span class="band-label">{html.escape(label.strip())}</span>' if label.strip() else ""
    page = head + [
        "<body>",
        "",
        '<header class="band">',
        '  <div class="band-inner">',
        f'    <img src="{data_uri(ASSETS / "versatex-horizontal-light.svg", "image/svg+xml")}" alt="Versatex">{label_html}',
        "  </div>",
        "</header>",
        "",
        '<main class="page">',
        body.strip("\n"),
        "</main>",
        "",
    ]
    if "data-copy" in body:
        page.append(COPY_SCRIPT)
    page += ["</body>", "</html>", ""]
    return "\n".join(page)


class PageReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.open = []
        self.lang = None
        self.title = None
        self.in_title = False
        self.viewport = False
        self.page_css = []
        self.kit_css = []
        self.style_target = None
        self.inline_styles = []
        self.problems = []
        self.warnings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "title":
            self.in_title = True
            self.title = ""
        elif tag == "meta" and (attrs.get("name") or "").lower() == "viewport":
            self.viewport = True
        elif tag == "style":
            self.style_target = self.kit_css if attrs.get("id") == KIT_STYLE_ID else self.page_css
        elif tag == "script" and attrs.get("src"):
            self.problems.append(f"An external script is loaded: {attrs['src']}")
        elif tag == "link" and remote(attrs.get("href")):
            self.problems.append(f"An external file is loaded: {attrs['href']}")
        elif tag == "img" and "alt" not in attrs:
            self.problems.append(f"An image has no alt text: {short(attrs.get('src'))}")
        elif tag == "table" and not any("table-wrap" in parent for parent in self.open):
            self.warnings.append("A table is not inside <div class=\"table-wrap\">, so it will not scroll on a phone.")
        if tag in ("img", "source", "video", "audio", "iframe", "embed", "track") and remote(attrs.get("src")):
            self.problems.append(f"An external file is loaded: {attrs['src']}")
        if attrs.get("style"):
            self.inline_styles.append(attrs["style"])
        if tag not in VOID_TAGS:
            self.open.append(classes)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "style":
            self.style_target = None
        if tag not in VOID_TAGS and self.open:
            self.open.pop()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.style_target is not None:
            self.style_target.append(data)


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def remote(url):
    return bool(url) and re.match(r"\s*(https?:)?//", url, re.I) is not None


def short(text, length=60):
    text = text or ""
    return text if len(text) <= length else text[:length] + "…"


def check_page(text):
    """Return (errors, warnings) for a built page."""
    reader = PageReader()
    reader.feed(text)
    errors, warnings = list(reader.problems), list(reader.warnings)

    if not (reader.title or "").strip():
        errors.append("The page has no <title>.")
    if not reader.lang:
        errors.append("The <html> element has no lang.")
    if not reader.viewport:
        errors.append("The page has no viewport meta tag, so it will not fit a phone.")

    all_css = "\n".join(reader.kit_css + reader.page_css + reader.inline_styles)
    if CSS_IMPORT.search(all_css):
        errors.append("The CSS uses @import, which loads a file from elsewhere.")
    if CSS_REMOTE_URL.search(all_css):
        errors.append("The CSS loads a file from the network through url(…).")

    own_css = "\n".join(reader.page_css + reader.inline_styles)
    if YELLOW_TEXT.search(own_css):
        errors.append("Yellow is used as a text colour. Yellow is for fills, rules and markers only.")
    if NAVY.search(own_css):
        errors.append("Navy #1e3a8a is used. It is not a Versatex colour.")
    for family in FONT_FAMILY.findall(own_css):
        if not any(allowed in family.lower() for allowed in ALLOWED_FONTS):
            warnings.append(f"A font other than Roboto is set: {family.strip()}")

    size = len(text.encode("utf-8"))
    if size > MAX_BYTES:
        warnings.append(f"The page is {size / 1024 / 1024:.1f} MB, which is large for an attachment.")
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build and check Versatex-branded standalone HTML pages.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="wrap a body fragment in a branded, self-contained page")
    build.add_argument("body", type=Path)
    build.add_argument("--title", required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--label", default="", help="text on the right of the black band")
    build.add_argument("--description", default="")
    build.add_argument("--width", type=int, help="content width in px (default 960)")
    build.add_argument("--css", type=Path, help="extra CSS for this page only")

    check = commands.add_parser("check", help="check a built page against the brand rules")
    check.add_argument("page", type=Path)

    args = parser.parse_args(argv)

    if args.command == "build":
        extra_css = args.css.read_text(encoding="utf-8") if args.css else ""
        try:
            page = build_page(args.body.read_text(encoding="utf-8"), args.title, args.label,
                              args.description, args.width, extra_css)
        except BodyError as problem:
            print(f"error: {problem}", file=sys.stderr)
            return 2
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(page, encoding="utf-8", newline="\n")
        print(f"{args.out} ({len(page.encode('utf-8')) / 1024:.0f} KB)")
        return 0

    errors, warnings = check_page(args.page.read_text(encoding="utf-8"))
    for line in errors:
        print(f"error: {line}")
    for line in warnings:
        print(f"warning: {line}")
    if errors:
        return 1
    print(f"OK: {args.page}" + (f" ({len(warnings)} warning{'s' if len(warnings) != 1 else ''})" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
