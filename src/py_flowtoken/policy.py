import html
import json
import re
from html.parser import HTMLParser
from importlib.resources import files
from urllib.parse import unquote, urlsplit

SCHEMA = json.loads(files('py_flowtoken').joinpath('schema.json').read_text())


def safe_url(value: str) -> str | None:
    value = value.strip()
    if re.search(r'[\x00-\x20\x7f]', value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.scheme.lower() not in SCHEMA['protocols']:
            return None
        if parsed.scheme in ('http', 'https') or value.startswith('//'):
            if not parsed.hostname or re.search(r'[\s%\[\]<>]', unquote(parsed.hostname)):
                return None
            parsed.port
    except ValueError:
        return None
    return value


def safe_style(value: str) -> str:
    result = []
    for declaration in value.split(';'):
        name, separator, content = declaration.partition(':')
        name, content = name.strip().lower(), content.strip()
        if separator and name in SCHEMA['styles'] and re.fullmatch(r'[\w\s#.,()%/-]+', content) and not re.search(r'url|expression|javascript', content, re.I):
            result.append(f'{name}:{content}')
    return ';'.join(result)


class SemanticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in SCHEMA['tags']:
            return
        values = {}
        for name, value in attrs:
            if name == 'style':
                clean = safe_style(value or '')
                if clean:
                    values[name] = clean
            elif name in SCHEMA['attributes']:
                if name in ('href', 'src'):
                    value = safe_url(value or '')
                    if value is None:
                        continue
                values[name] = value
        if tag == 'input':
            values.update(type='checkbox', disabled=None)
        if tag == 'button':
            values['type'] = 'button'
        if tag == 'a' and values.get('target') == '_blank':
            values['rel'] = 'noopener noreferrer'
        attributes = ''.join(f' {name}' if value is None else f' {name}="{html.escape(value, quote=True)}"' for name, value in values.items())
        self.output.append(f'<{tag}{attributes}>')
        if tag not in SCHEMA['voidTags']:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack:
                opened = self.stack.pop()
                self.output.append(f'</{opened}>')
                if opened == tag:
                    break

    def handle_data(self, data):
        self.output.append(html.escape(data))


def sanitize_html(value: str) -> str:
    parser = SemanticHTML()
    parser.feed(value)
    parser.close()
    for tag in reversed(parser.stack):
        parser.output.append(f'</{tag}>')
    return ''.join(parser.output)
