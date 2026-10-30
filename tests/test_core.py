import json
from html.parser import HTMLParser

import pytest

from py_flowtoken import (
    ANIMATIONS,
    AnimatedImage,
    AnimatedMarkdown,
    AnimatedText,
    Options,
    TextStream,
    asset_path,
    assets,
    tokenize,
)


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def text_of(value):
    parser = Text()
    parser.feed(value)
    return "".join(parser.parts)


@pytest.mark.parametrize(
    "source",
    [
        "Hello world",
        "A  B\nC\tD",
        "café 日本語",
        "👩🏽‍💻 ready",
        "<script>alert(1)</script>",
        "",
    ],
)
@pytest.mark.parametrize("sep", ["word", "char", "diff"])
def test_render_preserves_text(source, sep):
    assert "".join(tokenize(source, sep)) == source
    assert text_of(AnimatedText(source, sep=sep).render()) == source


def test_stream_revisions_and_rewrites():
    stream = TextStream()
    assert stream.update("Hello").delta == "Hello"
    assert stream.update("Hello world").delta == " world"
    assert stream.update("Hello world").revision == 2
    assert stream.tokens() == ["Hello", " world"]
    result = stream.update("Well, hello")
    assert result.reset and result.delta == "Well, hello"
    assert stream.tokens() == ["Well, hello"]
    stream.update("Well")
    assert stream.tokens() == ["Well"]
    assert stream.append(" done").text == "Well done"
    stream.update("")
    assert stream.tokens() == []


def test_stream_event_is_valid_sse():
    update = TextStream().append("hello\n🌊")
    event = update.sse()
    assert json.loads(event.split("data: ", 1)[1]) == update.as_dict()
    assert event.endswith("\n\n")
    with pytest.raises(ValueError):
        update.sse("name\ndata: injected")


def test_all_animation_names_and_assets():
    css = asset_path("flowtoken.css").read_text()
    assert len(ANIMATIONS) == 14
    for name, keyframe in ANIMATIONS.items():
        assert "@keyframes " + keyframe in css
        assert f'data-animation="{name}"' in AnimatedText("hello", animation=name).render()
    assert "flowtoken.js" in assets()
    assert "flowtoken.css" in assets()
    with pytest.raises(ValueError):
        asset_path("../core.py")


@pytest.mark.parametrize(
    "options",
    [
        {"sep": "bad"},
        {"animation": "x;display:none"},
        {"animation_duration": "1s;color:red"},
        {"animation_timing_function": "unsafe"},
        {"interval_ms": -1},
        {"interval_ms": 1001},
        {"animation_timing_function": "steps(1, jump-none)"},
        {"animate_initial": "false"},
    ],
)
def test_bad_options_are_rejected(options):
    with pytest.raises(ValueError):
        Options(**options)


def test_markdown_features_and_escaped_content():
    source = '# Heading\n\n**strong** and *emphasis* and ~~gone~~\n\n- [x] done\n- [ ] next\n\n| A | B |\n|---|---|\n| C | D |\n\n```python\nprint("hello")\n```\n\n[Link](https://example.com)\n\n<script>alert(1)</script>'
    rendered = AnimatedMarkdown(source, sep="word").render()
    for tag in [
        "<h1>",
        "<strong>",
        "<em>",
        "<s>",
        "<table>",
        "<pre>",
        'type="checkbox"',
        'href="https://example.com"',
    ]:
        assert tag in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "print(" in text_of(rendered)
    assert (
        'href="javascript:'
        not in AnimatedMarkdown("[bad](javascript:alert(1))").render()
    )


def test_no_animation_keeps_plain_text():
    rendered = AnimatedText("hello <b>", animation=None).render()
    assert 'class="ft-token"' not in rendered
    assert text_of(rendered) == "hello <b>"


def test_image_safety_and_escaping():
    rendered = AnimatedImage("https://example.com/a.png", 'a "test"').render()
    assert 'alt="a &quot;test&quot;"' in rendered
    with pytest.raises(ValueError):
        AnimatedImage("javascript:alert(1)")
    with pytest.raises(ValueError):
        AnimatedImage("/image.png", height="1px;display:none")


def test_semantic_rendering_and_safe_urls():
    rendered = AnimatedText('one\ntwo').render()
    assert 'ft-token' not in rendered
    assert text_of(rendered) == 'one\ntwo'
    for source in ['[broken](http://[)', '[bad](http://example.com:bad)', '![alt](http://[)']:
        rendered = AnimatedMarkdown(source).render()
        assert 'href="http:' not in rendered
        assert 'src="http:' not in rendered


def test_append_has_a_delta_fast_path():
    stream = TextStream()
    chunks = stream.chunks
    stream.update = lambda value: (_ for _ in ()).throw(AssertionError('append used full snapshot path'))
    for value in ['a', ' ', 'b']:
        stream.append(value)
    assert stream.chunks is chunks
    assert stream.text == 'a b'
    assert stream.tokens() == ['a', ' ', 'b']


def test_custom_components_and_partial_tags():
    import html
    from py_flowtoken import Component
    seen = []
    def badge(component: Component):
        seen.append(component)
        return '<mark data-ft-key="badge">'+html.escape(component.content)+'</mark>'
    for value in ['before <', 'before <bad', 'before <badge title="x"', 'before <badge\ntitle="x"', 'before <badge>unfinished']:
        rendered = AnimatedMarkdown(value, custom_components={'badge':badge}).render()
        assert 'unfinished' not in rendered
        assert '<bad' not in text_of(rendered)
    rendered = AnimatedMarkdown('before <badge title="name">Hello</badge> after', custom_components={'badge':badge}).render()
    assert '<mark data-ft-key="badge">Hello</mark>' in rendered
    assert seen[-1].attributes['title'] == 'name'
    assert 'before' in text_of(rendered) and 'after' in text_of(rendered)
    default = AnimatedMarkdown('<mark>literal</mark>').render()
    assert '&lt;mark&gt;' in default
    trusted = AnimatedMarkdown('<mark onclick="evil()">safe</mark><script>evil()</script>', trusted_html=True).render()
    assert '<mark>safe</mark>' in trusted
    assert 'onclick' not in trusted and '<script>' not in trusted


def test_code_and_image_options():
    code = AnimatedMarkdown('```python\nvalue = 42\n```', code_style='monokai').render()
    assert 'data-ft-copy' in code and 'data-ft-source="value = 42\n"' in code
    assert 'color:' in code and 'data-ft-theme="monokai"' in code
    image = AnimatedMarkdown('![alt](/image.png)', img_height='7rem', img_width='50%', object_fit='cover').render()
    assert 'height:7rem' in image and 'width:50%' in image and 'object-fit:cover' in image
    assert 'data-ft-image' in image
    assert 'cubic-bezier' in AnimatedText('hello',animation_timing_function='cubic-bezier(0.2,0,0.4,1)').render()
    assert 'steps(4, end)' in AnimatedText('hello',animation_timing_function='steps(4, end)').render()


def test_custom_components_preserve_markdown_code():
    calls = []
    def badge(component):
        calls.append(component)
        return '<mark>rendered</mark>'
    for source in ['`<badge>literal</badge>`', '```html\n<badge>literal</badge>\n```', '    <badge>literal</badge>\n', '`<bad`']:
        output = AnimatedMarkdown(source, custom_components={'badge':badge}).render()
        assert '<mark>' not in output
        assert '<bad' in text_of(output)
    assert not calls
    output = AnimatedMarkdown('`example` <badge>real</badge>', custom_components={'badge':badge}).render()
    assert '<mark>rendered</mark>' in output
    with pytest.raises(TypeError, match='HTML strings'):
        AnimatedMarkdown('<badge/>', custom_components={'badge':lambda component:None}).render()
