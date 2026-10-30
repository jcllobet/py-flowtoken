import html
from collections.abc import Callable, Mapping

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Text
from pygments.util import ClassNotFound

from .components import Component, extract_components
from .options import Options, dimension
from .policy import SCHEMA, safe_url, sanitize_html


class Renderable:
    def __html__(self):
        return self.render()

    def __ft__(self):
        from fastcore.xml import NotStr
        return NotStr(self.render())


def identity(value):
    return f' id="{html.escape(value, quote=True)}"' if value else ''


class AnimatedText(Renderable):
    def __init__(self, content: str = '', *, id: str | None = None, **options):
        self.content, self.id = content, id
        self.options = Options(**options)

    def render(self) -> str:
        return f'<span class="ft-text" data-flowtoken="text" {self.options.attributes()}{identity(self.id)}>{html.escape(self.content)}</span>'


class AnimatedMarkdown(Renderable):
    def __init__(self, content: str = '', *, id: str | None = None, code_style: str = 'default',
                 img_height: str = '20rem', img_width: str | None = None, object_fit: str = 'contain',
                 custom_components: Mapping[str, Callable[[Component], str]] | None = None,
                 trusted_html: bool = False, **options):
        for key, value in SCHEMA['markdownDefaults'].items():
            argument = {'duration':'animation_duration','easing':'animation_timing_function'}.get(key, key)
            options.setdefault(argument, value)
        self.options = Options(**options)
        self.content, self.id = content, id
        self.formatter = HtmlFormatter(style=code_style, nowrap=True, noclasses=True)
        self.code_style = code_style
        self.img_height, self.img_width = dimension(img_height), dimension(img_width)
        if object_fit not in ('cover','contain','fill','none','scale-down'):
            raise ValueError('Invalid image fit')
        self.object_fit, self.custom_components, self.trusted_html = object_fit, custom_components or {}, trusted_html

    def render(self) -> str:
        source, components = extract_components(self.content, self.custom_components)
        engine = MarkdownIt('commonmark', {'html': self.trusted_html, 'linkify':True}).enable(['table','strikethrough','linkify'])
        engine.use(tasklists_plugin)

        def render_fence(tokens, index, options, env):
            token = tokens[index]
            language = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ''
            try:
                lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False) if language else TextLexer(stripnl=False, ensurenl=False)
            except ClassNotFound:
                lexer = TextLexer(stripnl=False, ensurenl=False)
            body = highlight(token.content, lexer, self.formatter)
            language_class = f' class="language-{html.escape(language, quote=True)}"' if language else ''
            background = html.escape(self.formatter.style.background_color, quote=True)
            foreground = self.formatter.style.style_for_token(Text)['color'] or '000000'
            return f'<div class="ft-code" data-ft-code data-ft-source="{html.escape(token.content, quote=True)}" data-ft-theme="{html.escape(self.code_style, quote=True)}" style="background-color:{background};color:#{foreground}"><button type="button" data-ft-copy aria-label="Copy code">Copy code</button><pre><code{language_class}>{body}</code></pre></div>\n'

        def render_image(tokens, index, options, env):
            token = tokens[index]
            source = token.attrGet('src') or ''
            if safe_url(source) is None:
                return html.escape(token.content)
            image = AnimatedImage(source, token.content, height=self.img_height, width=self.img_width, object_fit=self.object_fit, animation=self.options.animation, animation_duration=self.options.animation_duration, animation_timing_function=self.options.animation_timing_function)
            return image.render()

        def render_link(tokens, index, options, env):
            token = tokens[index]
            target = safe_url(token.attrGet('href') or '')
            if target is None:
                token.attrs.pop('href', None)
            token.attrSet('target', '_blank')
            token.attrSet('rel', 'noopener noreferrer')
            return engine.renderer.renderToken(tokens, index, options, env)

        engine.renderer.rules.update(fence=render_fence, code_block=render_fence, image=render_image, link_open=render_link)
        rendered = engine.render(source)
        for marker, component in components.items():
            rendered = rendered.replace(f"<p>{marker}</p>", component).replace(marker, component)
        body = sanitize_html(rendered)
        return f'<div class="ft-markdown" data-flowtoken="markdown" {self.options.attributes()}{identity(self.id)}>{body}</div>'


class AnimatedImage(Renderable):
    def __init__(self, src: str, alt: str = '', *, height: str | None = '20rem', width: str | None = None,
                 object_fit: str = 'contain', animation: str | None = 'fadeIn',
                 animation_duration: str = '0.25s', animation_timing_function: str = 'ease-out'):
        if safe_url(src) is None:
            raise ValueError('Unsafe image source')
        if object_fit not in ('cover','contain','fill','none','scale-down'):
            raise ValueError('Invalid image fit')
        self.src, self.alt = src, alt
        self.height, self.width, self.object_fit = dimension(height), dimension(width), object_fit
        self.options = Options(animation=animation, animation_duration=animation_duration,
                               animation_timing_function=animation_timing_function)

    def render(self):
        sizing = ';'.join(f'{key}:{value}' for key, value in [('height',self.height),('width',self.width),('max-width','100%'),('object-fit',self.object_fit)] if value)
        return f'<img class="ft-image" data-ft-image {self.options.attributes()} src="{html.escape(self.src, quote=True)}" alt="{html.escape(self.alt, quote=True)}" style="{sizing}">'
