# API and configuration

## Render text and Markdown

```python
from py_flowtoken import AnimatedMarkdown, AnimatedText

text = AnimatedText('Hello, world!', animation='fadeIn', interval_ms=35)
markdown = AnimatedMarkdown('# Hello\n\nA **streaming** answer.', sep='word')

print(text.render())
print(markdown.render())
```

Both components implement FastHTML's `__ft__` protocol, so they can be placed directly inside `Div`, `Main`, or another FastHTML component. Plain `.render()` returns HTML for other frameworks.

The [framework guides](#framework-setup) register and serve the packaged CSS/JavaScript automatically. For a different Python framework, the existing `asset_path()` and `assets()` functions remain available; they do not require any adapter or CDN.

## Stream updates

```python
from py_flowtoken import TextStream

stream = TextStream()
stream.append('Hello ')
event = stream.append('world')
print(event.sse())

stream.update('Hello, everyone')
```

`append` takes a new chunk. `update` takes the full current text, including transcription corrections. Repeated snapshots do not duplicate words; shortening or replacing the text resets the changed portion. `TextStream.tokens('diff')` returns the accumulated chunks.

In the browser:

```javascript
import { FlowToken } from '/your/static/path/flowtoken.js';

const view = new FlowToken(document.getElementById('answer'), {
  animation: 'fadeIn',
  duration: '0.25s',
  interval: 35,
});

view.setText('Hello');
view.setText('Hello world');
await view.whenIdle();
view.append('!');
```

`setText` accepts an accumulated snapshot. `append` accepts a delta. New words are inserted gradually; previously visible words keep their DOM nodes and do not restart their animations. A revised partial word updates in place. `flush()` reveals pending text immediately; `destroy()` cancels queued animation work and resolves pending `whenIdle()` promises. Reduced-motion settings reveal text immediately. `configure()` changes animation settings; changing the separator retokenizes existing text without replaying it.

`flowtoken:before-render`, `flowtoken:render`, and `flowtoken:idle` events support chat auto-scrolling without forcing users away from older messages.

For Markdown updates, `FlowMarkdown.setRenderedHTML()` accepts the output of `AnimatedMarkdown.render()`. Both renderers use the same browser text engine. Unchanged elements and text retain their DOM nodes, selection, and animation state. Default diff mode animates each appended chunk; use `sep='word'` to pace individual words. Native whitespace preserves line breaks, including inside code blocks.

```javascript
import {mount, unmount} from '/your/static/path/flowtoken.js';

const element = document.getElementById('answer');
const view = mount(element);
view.setRenderedHTML(nextMarkdownHtml);
await view.whenIdle();
unmount(element);
```

`mount()` is idempotent for a live renderer. Calling `mount()` after destruction creates a fresh renderer. `mountAll(root)` includes the root itself and supports HTMX swaps. Initial server content animates by default; set Python `animate_initial=False` or browser `animateInitial: false` to display it immediately. Ship the new CSS and JavaScript together with the Python package when upgrading from 0.2.x.

## Markdown components

```python
from html import escape
from py_flowtoken import AnimatedMarkdown, Component


def badge(component: Component) -> str:
    return '<mark>' + escape(component.content) + '</mark>'


answer = AnimatedMarkdown(
    '```python\nprint("hello")\n```\n\n<badge>Ready</badge>',
    sep='word',
    code_style='monokai',
    img_height='12rem',
    img_width='100%',
    object_fit='contain',
    custom_components={'badge': badge},
)
```

`code_style` accepts a Pygments theme name. Fenced and indented code uses syntax highlighting, a matching background, and a copy button with success/failure feedback. Copying preserves the complete source, including its final newline, while the visual stream is still arriving. The Clipboard API requires a secure browser context, including localhost.

`img_height`, `img_width`, and `object_fit` configure Markdown images. `AnimatedImage` accepts the equivalent `height`, `width`, and `object_fit` options plus animation settings. Images animate when loading succeeds; failed images expose their alt text. Appending text retains loaded image state.

Custom tag callbacks receive a `Component` with `tag`, `attributes`, and raw inner `content`, and return an HTML string. Callback output is sanitized. Registered incomplete tags are withheld until complete; tags inside Markdown code remain literal. Give interactive output a stable `data-ft-key` to preserve its element across updates. Callbacks run on the server; they do not execute Python in the browser or accept React components. Raw Markdown HTML is escaped by default; `trusted_html=True` enables only the same allowlisted HTML, never arbitrary scripts or event handlers.

## Features and compatibility

| Feature | Support |
| --- | --- |
| Word, character, and diff tokenization | Python and browser APIs |
| All 14 named FlowToken animations | Matching public names; adapted keyframes |
| Paragraphs, headings, emphasis, lists, links, fenced code, images | Python Markdown rendering |
| GFM tables, task lists, strikethrough, autolinks | Supported |
| Progressive snapshots and chunk appends | Supported |
| Partial-word corrections, resets, duplicate snapshots | Supported |
| Reduced motion and cancellation | Supported |
| Framework adapters | FastHTML components, Flask/Jinja helpers, Django template tags and static files |
| Custom tags and partial-tag buffering | Python callback registry; sanitized output |
| Syntax highlighting and code-copy feedback | Pygments theme names; secure-context Clipboard API |
| Image dimensions, fit, and load-triggered animation | Supported |
| Timing functions | CSS keywords, `cubic-bezier(...)`, and `steps(...)` |
| Initial animation, explicit unmount, and remount | Supported |
| Raw HTML from Markdown | Escaped by default; allowlisted with `trusted_html=True` |
| React components and theme objects | Use Python callbacks and Pygments themes instead |

`AnimatedText` defaults to word pacing, `fadeIn`, 250 ms fades, and 35 ms word intervals. `AnimatedMarkdown` retains upstream's diff mode, `fadeIn`, one-second duration, and `ease-in-out` defaults. Use `sep='word'` for per-word Markdown animation. Custom animation names are allowed if the application defines the CSS keyframes.

Thirteen animation effects match the reference's computed keyframes. `typewriter` uses clipping to reveal text without animating layout width; incidental DOM wrappers and syntax-highlighter colors differ. Unicode characters are kept intact; the port does not reproduce upstream UTF-16 surrogate splitting or its substring-based diff bug. JavaScript is still required for browser animation.

