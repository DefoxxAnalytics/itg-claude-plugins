import re
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent / "skills" / "branded-page"
sys.path.insert(0, str(SKILL))

import page  # noqa: E402

COMPONENTS = (SKILL / "components.html").read_text(encoding="utf-8")


def built(body="<p>Hello</p>", **options):
    options.setdefault("title", "A page")
    return page.build_page(body, **options)


def with_page_css(css):
    return built(extra_css=css)


def with_inline_style(style):
    return built(f'<p style="{style}">text</p>')


def test_components_page_embeds_fonts_logo_and_favicon():
    html = built(COMPONENTS, title="Components", label="ITG · Page kit")
    faces = re.findall(r"@font-face \{[^}]+\}", html)
    assert len(faces) == 4
    assert all("url(data:font/woff2;base64," in face for face in faces)
    assert re.search(r'<img src="data:image/svg\+xml;base64,[^"]+" alt="Versatex">', html)
    assert '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,' in html


def test_components_page_loads_nothing_from_the_network():
    html = built(COMPONENTS)
    assert not re.search(r'(src|href)="(https?:)?//', html)
    assert page.check_page(html) == ([], [])


def test_title_label_and_description_are_escaped():
    html = built(title="R&D <x>", label='A "label" & <b>', description="Tom & Jerry <3")
    assert "<title>R&amp;D &lt;x&gt;</title>" in html
    assert '<span class="band-label">A &quot;label&quot; &amp; &lt;b&gt;</span>' in html
    assert 'content="Tom &amp; Jerry &lt;3"' in html


def test_no_label_means_no_label_span():
    assert "band-label\">" not in built()


def test_copy_script_only_when_a_copy_button_is_used():
    assert "<script>" not in built("<p>No buttons</p>")
    with_button = built('<div class="cmd"><pre id="c">x</pre><button class="copy" data-copy="c">Copy</button></div>')
    assert with_button.count("<script>") == 1


def test_width_overrides_the_default():
    assert ":root { --width: 820px; }" in built(width=820)
    assert "--width: 820px" not in built()


def test_comments_are_removed_from_the_body():
    html = built("<!-- note for the author: <html> -->\n<p>Kept</p>")
    assert "note for the author" not in html
    assert "<p>Kept</p>" in html


@pytest.mark.parametrize("body", ["<html><p>x</p></html>", "<body>x</body>", "<p>x</p><script>alert(1)</script>",
                                  "<HEAD></HEAD>"])
def test_whole_documents_and_scripts_are_refused(body):
    with pytest.raises(page.BodyError):
        built(body)


def test_an_empty_title_is_refused():
    with pytest.raises(page.BodyError):
        built(title="  ")


def errors_of(html):
    return page.check_page(html)[0]


def warnings_of(html):
    return page.check_page(html)[1]


@pytest.mark.parametrize("snippet", [
    '<script src="https://example.com/x.js"></script>',
    '<link rel="stylesheet" href="https://fonts.example.com/css">',
    '<img src="//example.com/logo.png" alt="Logo">',
    '<iframe src="https://example.com"></iframe>',
])
def test_check_fails_on_external_files(snippet):
    html = built().replace("</main>", snippet + "\n</main>")
    assert any("external" in error for error in errors_of(html))


def test_check_fails_on_css_that_loads_from_the_network():
    assert errors_of(with_page_css('@import url("https://example.com/x.css");'))
    assert errors_of(with_page_css('.x { background: url(https://example.com/a.png); }'))


@pytest.mark.parametrize("css", ["color: #FDC00F", "color:var(--yellow)", "color: rgb(253, 192, 15)"])
def test_check_fails_on_yellow_text(css):
    assert any("Yellow" in error for error in errors_of(with_inline_style(css)))
    assert any("Yellow" in error for error in errors_of(with_page_css(f".x {{ {css}; }}")))


@pytest.mark.parametrize("css", ["background-color: var(--yellow)", "border-top: 6px solid var(--yellow)",
                                 "border-color: #FDC00F", "background: #fdc00f; color: var(--black)"])
def test_check_allows_yellow_fills_rules_and_markers(css):
    assert errors_of(with_inline_style(css)) == []


def test_check_ignores_the_kits_own_css():
    assert errors_of(built()) == []


def test_check_fails_on_navy():
    assert any("Navy" in error for error in errors_of(with_page_css(".x { background: #1e3a8a; }")))


def test_check_fails_on_an_image_without_alt():
    html = built('<img src="data:image/png;base64,AAAA">')
    assert any("alt" in error for error in errors_of(html))
    assert errors_of(built('<img src="data:image/png;base64,AAAA" alt="">')) == []


def test_check_fails_without_title_lang_or_viewport():
    errors = errors_of("<!doctype html><html><head></head><body></body></html>")
    assert len(errors) == 3


def test_check_warns_on_a_table_outside_table_wrap():
    assert warnings_of(built("<table><tr><td>x</td></tr></table>"))
    assert warnings_of(built('<div class="table-wrap"><table><tr><td>x</td></tr></table></div>')) == []


def test_check_warns_on_other_fonts():
    assert warnings_of(with_page_css(".x { font-family: Barlow, sans-serif; }"))
    assert warnings_of(with_page_css(".x { font-family: var(--mono); }")) == []


def test_command_line_build_and_check(tmp_path, capsys):
    body = tmp_path / "body.html"
    body.write_text("<p>Hello</p>", encoding="utf-8")
    out = tmp_path / "out" / "page.html"
    assert page.main(["build", str(body), "--title", "Hello", "--out", str(out)]) == 0
    assert out.exists()
    assert page.main(["check", str(out)]) == 0
    assert "OK" in capsys.readouterr().out


def test_command_line_reports_a_refused_body(tmp_path, capsys):
    body = tmp_path / "body.html"
    body.write_text("<html></html>", encoding="utf-8")
    assert page.main(["build", str(body), "--title", "x", "--out", str(tmp_path / "x.html")]) == 2
    assert "fragment" in capsys.readouterr().err


def test_command_line_check_fails_with_exit_1(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text(built('<p style="color: #FDC00F">x</p>'), encoding="utf-8")
    assert page.main(["check", str(bad)]) == 1
