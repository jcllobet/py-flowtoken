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
        assert keyframe in AnimatedText("hello", animation=name).render()
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
