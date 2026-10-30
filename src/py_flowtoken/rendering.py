import html
import re

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

from .options import Options
from .streaming import tokenize


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
