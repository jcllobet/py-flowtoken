import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Mapping

from markdown_it import MarkdownIt
from markdown_it.rules_inline import backtick


def mask_code(source: str) -> str:
    engine = MarkdownIt('commonmark')
    ranges = []
    offsets = [0]
    for match in re.finditer('\n', source):
        offsets.append(match.end())
    offsets.append(len(source))
    for token in engine.parse(source):
        if token.type in ('fence', 'code_block'):
            start, end = token.map
            ranges.append((offsets[start], offsets[end]))
    def capture_backticks(state, silent):
        start, count = state.pos, len(state.tokens)
        matched = backtick(state, silent)
        if len(state.tokens) > count and state.tokens[-1].type == 'code_inline':
            ranges.append((start, state.pos))
        return matched

    engine.inline.ruler.at('backticks', capture_backticks)
    engine.inline.parse(source, engine, {}, [])
    masked = list(source)
    for start, end in ranges:
        masked[start:end] = ['\n' if char == '\n' else ' ' for char in source[start:end]]
    return ''.join(masked)


@dataclass(frozen=True)
class Component:
    tag: str
    attributes: Mapping[str, str | None]
    content: str


class ComponentParser(HTMLParser):
    def __init__(self, source: str, renderers: Mapping[str, Callable[[Component], str]]):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.renderers = {key.lower(): value for key, value in renderers.items()}
        self.offsets = [0]
        for match in re.finditer('\n', source):
            self.offsets.append(match.end())
        self.active = None
        self.depth = 0
        self.replacements = []

    def position(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if self.active and tag == self.active[0]:
            self.depth += 1
        elif not self.active and tag in self.renderers:
            start = self.position()
            self.active = (tag, dict(attrs), start, start + len(self.get_starttag_text()))
            self.depth = 1

    def handle_endtag(self, tag):
        if self.active and tag == self.active[0]:
            self.depth -= 1
            if self.depth == 0:
                name, attrs, start, content_start = self.active
                end_start = self.position()
                end = self.source.find('>', end_start) + 1
                rendered = self.renderers[name](Component(name, attrs, self.source[content_start:end_start]))
                if not isinstance(rendered, str):
                    raise TypeError('Custom component renderers must return HTML strings')
                self.replacements.append((start, end, rendered))
                self.active = None

    def handle_startendtag(self, tag, attrs):
        if not self.active and tag in self.renderers:
            start = self.position()
            rendered = self.renderers[tag](Component(tag, dict(attrs), ''))
            if not isinstance(rendered, str):
                raise TypeError('Custom component renderers must return HTML strings')
            self.replacements.append((start, start + len(self.get_starttag_text()), rendered))


def extract_components(source: str, renderers: Mapping[str, Callable[[Component], str]]):
    if not renderers:
        return source, {}
    for name in renderers:
        if not re.fullmatch(r'[a-zA-Z][\w-]*', name):
            raise ValueError('Invalid custom component tag')
    parser = ComponentParser(source, renderers)
    masked = mask_code(source)
    parser.feed(masked)
    limit = parser.active[2] if parser.active else len(source)
    tail = masked.rfind('<', 0, limit)
    if tail >= 0 and '>' not in masked[tail:limit]:
        partial = masked[tail + 1:limit].lstrip('/').lower()
        if any(name.lower().startswith(partial) or re.match(re.escape(name.lower())+r'\s', partial) for name in renderers):
            limit = tail
    output, rendered, cursor = [], {}, 0
    prefix = 'PYFLOWTOKENCOMPONENT'
    while prefix in source:
        prefix += 'X'
    for start, end, value in parser.replacements:
        if end > limit:
            break
        marker = f'{prefix}{len(rendered)}END'
        output.extend([source[cursor:start], marker])
        rendered[marker] = value
        cursor = end
    output.append(source[cursor:limit])
    return ''.join(output), rendered
