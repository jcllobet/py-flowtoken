import html
import json
import re
from dataclasses import dataclass, field
from importlib.resources import files

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

ANIMATIONS = {
    name: f"ft-{name}"
    for name in (
        "fadeIn",
        "slideUp",
        "wave",
        "elastic",
        "bounceIn",
        "rotateIn",
        "colorTransition",
        "fadeAndScale",
        "slideInFromLeft",
        "blurIn",
        "typewriter",
        "highlight",
        "blurAndSharpen",
        "dropIn",
    )
}


def tokenize(text: str, sep: str = "word") -> list[str]:
    if sep == "word":
        return [part for part in re.split(r"(\s+)", text) if part]
    if sep == "char":
        return list(text)
    if sep == "diff":
        return [text] if text else []
    raise ValueError('sep must be "word", "char", or "diff"')


@dataclass(frozen=True)
class Update:
    text: str
    delta: str
    reset: bool
    revision: int

    def as_dict(self):
        return {
            "text": self.text,
            "delta": self.delta,
            "reset": self.reset,
            "revision": self.revision,
        }

    def sse(self, event: str = "flowtoken") -> str:
        if not re.fullmatch(r"[\w-]+", event):
            raise ValueError("Invalid SSE event name")
        return f"event: {event}\ndata: {json.dumps(self.as_dict(), ensure_ascii=False)}\n\n"


@dataclass
class TextStream:
    text: str = ""
    revision: int = 0
    chunks: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.text and not self.chunks:
            self.chunks = [self.text]

    def update(self, text: str) -> Update:
        reset = not text.startswith(self.text)
        delta = text if reset else text[len(self.text) :]
        if text != self.text:
            self.revision += 1
            self.chunks = (
                ([text] if text else [])
                if reset
                else self.chunks + ([delta] if delta else [])
            )
            self.text = text
        return Update(self.text, delta, reset, self.revision)

    def append(self, delta: str) -> Update:
        return self.update(self.text + delta)

    def tokens(self, sep: str = "diff") -> list[str]:
        return self.chunks.copy() if sep == "diff" else tokenize(self.text, sep)


@dataclass(frozen=True)
class Options:
    sep: str = "word"
    animation: str | None = "fadeIn"
    animation_duration: str = "0.25s"
    animation_timing_function: str = "ease-out"
    interval_ms: int = 35

    def __post_init__(self):
        tokenize("", self.sep)
        if self.animation is not None and not re.fullmatch(
            r"[a-zA-Z_][\w-]*", self.animation
        ):
            raise ValueError("Invalid animation name")
        if not re.fullmatch(
            r"(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)", self.animation_duration
        ):
            raise ValueError("Invalid animation duration")
        if self.animation_timing_function not in {
            "ease",
            "ease-in",
            "ease-out",
            "ease-in-out",
            "linear",
        }:
            raise ValueError("Invalid animation timing function")
        if not 0 <= self.interval_ms <= 1000:
            raise ValueError("interval_ms must be between 0 and 1000")

    def attributes(self) -> str:
        values = {
            "data-sep": self.sep,
            "data-animation": self.animation or "none",
            "data-duration": self.animation_duration,
            "data-easing": self.animation_timing_function,
            "data-interval": str(self.interval_ms),
        }
        return " ".join(
            f'{key}="{html.escape(value, quote=True)}"' for key, value in values.items()
        )

    def style(self, index: int = 0) -> str:
        name = ANIMATIONS.get(self.animation, self.animation) or "none"
        return f"animation-name:{name};animation-duration:{self.animation_duration};animation-timing-function:{self.animation_timing_function};animation-delay:{index * self.interval_ms}ms;animation-iteration-count:1;animation-fill-mode:both"


def _spans(text: str, options: Options, offset: int = 0) -> str:
    if options.animation in (None, "none"):
        return html.escape(text)
    return "".join(
        f'<span class="ft-token" data-ft-token="{index + offset}" style="{options.style(index + offset)}">{html.escape(token)}</span>'
        for index, token in enumerate(tokenize(text, options.sep))
    )


class AnimatedText:
    def __init__(self, content: str = "", *, id: str | None = None, **options):
        self.content, self.id = content, id
        self.options = Options(**options)

    def render(self) -> str:
        identity = f' id="{html.escape(self.id, quote=True)}"' if self.id else ""
        return f'<span class="ft-text" data-flowtoken="text" {self.options.attributes()}{identity}>{_spans(self.content, self.options)}</span>'

    def __html__(self):
        return self.render()

    def __ft__(self):
        from fastcore.xml import NotStr

        return NotStr(self.render())


class AnimatedMarkdown(AnimatedText):
    def __init__(self, content: str = "", **options):
        options.setdefault("sep", "diff")
        options.setdefault("animation_duration", "1s")
        options.setdefault("animation_timing_function", "ease-in-out")
        super().__init__(content, **options)

    def render(self) -> str:
        engine = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable(
            ["table", "strikethrough", "linkify"]
        )
        engine.use(tasklists_plugin)
        count = 0

        def render_text(tokens, index, options, env):
            nonlocal count
            text = tokens[index].content
            result = _spans(text, self.options, count)
            count += len(tokenize(text, self.options.sep))
            return result

        def render_inline_code(tokens, index, options, env):
            return "<code>" + render_text(tokens, index, options, env) + "</code>"

        def render_fence(tokens, index, options, env):
            language = (
                tokens[index].info.strip().split(maxsplit=1)[0]
                if tokens[index].info.strip()
                else ""
            )
            attribute = (
                f' class="language-{html.escape(language, quote=True)}"'
                if language
                else ""
            )
            return (
                f"<pre><code{attribute}>"
                + render_text(tokens, index, options, env)
                + "</code></pre>\n"
            )

        engine.renderer.rules.update(
            text=render_text,
            code_inline=render_inline_code,
            fence=render_fence,
            code_block=render_fence,
        )
        identity = f' id="{html.escape(self.id, quote=True)}"' if self.id else ""
        return f'<div class="ft-markdown" data-flowtoken="markdown" {self.options.attributes()}{identity}>{engine.render(self.content)}</div>'


class AnimatedImage:
    def __init__(
        self,
        src: str,
        alt: str = "",
        *,
        height: str = "20rem",
        animation: str = "fadeIn",
    ):
        if re.match(r"\s*(?:javascript|vbscript|data):", src, re.I):
            raise ValueError("Unsafe image source")
        if not re.fullmatch(r"\d+(?:\.\d+)?(?:px|rem|em|%|vh|vw)", height):
            raise ValueError("Invalid image height")
        self.src, self.alt, self.height = src, alt, height
        self.options = Options(animation=animation)

    def render(self):
        return f'<img class="ft-image" src="{html.escape(self.src, quote=True)}" alt="{html.escape(self.alt, quote=True)}" style="height:{self.height};max-width:100%;object-fit:contain;{self.options.style()}">'

    def __ft__(self):
        from fastcore.xml import NotStr

        return NotStr(self.render())


def asset_path(name: str):
    if name not in {"flowtoken.js", "flowtoken.css"}:
        raise ValueError("Unknown asset")
    return files("py_flowtoken").joinpath("static", name)


def assets(base_url: str = "/static/flowtoken") -> str:
    base_url = html.escape(base_url.rstrip("/"), quote=True)
    return f'<link rel="stylesheet" href="{base_url}/flowtoken.css"><script type="module" src="{base_url}/flowtoken.js"></script>'
