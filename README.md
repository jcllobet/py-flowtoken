# py-flowtoken

A Python adaptation of [Ephibbs/flowtoken](https://github.com/Ephibbs/flowtoken) for animated text and Markdown streaming. It works with FastHTML, Flask, and Django, without React or a JavaScript package manager in production.

Python renders the components and maintains stream state. A small, dependency-free browser module animates the words. A Python server cannot itself animate a browser's DOM.

## Install

```sh
pip install 'git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
```

This project is published as a GitHub repository; it is not currently published on PyPI.

## Framework setup

Install the extra for your framework. Each adapter uses the same renderer, stream state, and browser module; installing one extra does not install the other frameworks.

| Framework | Adapter | Complete installation guide |
| --- | --- | --- |
| FastHTML | `py_flowtoken.adapters.fasthtml` | [FastHTML setup](docs/fasthtml.md) |
| Flask 3.1 | `py_flowtoken.adapters.flask` | [Flask setup](docs/flask.md) |
| Django 5.2 LTS | `py_flowtoken.adapters.django` | [Django setup](docs/django.md) |

```sh
python -m pip install 'py-flowtoken[fasthtml] @ git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
python -m pip install 'py-flowtoken[flask] @ git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
python -m pip install 'py-flowtoken[django] @ git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
```

Choose the line for your framework. The guides cover asset routing, template helpers, live streaming, and runnable examples. Django supports both normal `collectstatic` deployment and an optional included asset router. See the [shared streaming contract](docs/streaming.md) for the update format and browser connection.

## Package layout

```text
py_flowtoken/
  rendering.py       HTML text, Markdown, and image components
  streaming.py       Snapshot/delta state and SSE encoding
  options.py         Animation settings and tokenization options
  assets.py          Framework-independent packaged asset lookup
  core.py            Backward-compatible public imports
  adapters/
    fasthtml.py      ASGI asset mount and streaming response
    flask.py         Blueprint, Jinja helpers, and streaming response
    django/          AppConfig, template tags, URLs, and streaming response
  static/
    py_flowtoken/    One shared browser module and stylesheet
```

The core never imports a web framework. Existing top-level imports and `py_flowtoken.core` imports remain compatible with 0.1.x, including `asset_path()`.

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

`setText` accepts an accumulated snapshot. `append` accepts a delta. New words are inserted gradually; previously visible words keep their DOM nodes and do not restart their animations. A revised partial word updates in place. `flush()` reveals pending text immediately; `destroy()` cancels queued animation work. Reduced-motion settings reveal text immediately.

`flowtoken:before-render`, `flowtoken:render`, and `flowtoken:idle` events support chat auto-scrolling without forcing users away from older messages.

For server-rendered Markdown updates, `FlowMarkdown.setRenderedHTML()` accepts the output of `AnimatedMarkdown.render()`. It preserves Markdown structure and animates the newly changed suffix. Plain-text pacing inserts words into the DOM; Markdown updates use CSS delays within the server-rendered structure. They are intentionally separate APIs.

## Features and compatibility

| Feature | Support |
| --- | --- |
| Word, character, and diff tokenization | Python and browser APIs |
| All 14 named FlowToken animations | Matching public names; independently written CSS |
| Paragraphs, headings, emphasis, lists, links, fenced code, images | Python Markdown rendering |
| GFM tables, task lists, strikethrough, autolinks | Supported |
| Progressive snapshots and chunk appends | Supported |
| Partial-word corrections, resets, duplicate snapshots | Supported |
| Reduced motion and cancellation | Supported |
| Framework adapters | FastHTML components, Flask/Jinja helpers, Django template tags and static files |
| Arbitrary React custom components | Not portable; not supported |
| React syntax-highlighter themes | Not supported; code remains escaped and readable |
| Raw HTML from Markdown | Escaped for safety; differs from upstream's `rehype-raw` behavior |

`AnimatedText` defaults to word pacing, `fadeIn`, 250 ms fades, and 35 ms word intervals. `AnimatedMarkdown` retains upstream's diff mode, `fadeIn`, one-second duration, and `ease-in-out` defaults. Use `sep='word'` for per-word Markdown animation. Custom animation names are allowed if the application defines the CSS keyframes.

The animation styles preserve FlowToken's named effects, not every original pixel or incidental DOM wrapper. Unicode characters are kept intact; the port does not reproduce upstream UTF-16 surrogate splitting or its substring-based diff bug. JavaScript is still required for browser animation.

## Provenance and attribution

This is an independent adaptation of FlowToken by **Ephibbs and contributors**, not an official Python release or an affiliation with its maintainers. The reference implementation for compatibility tests is the published npm package **`flowtoken@1.0.40`**. The original project provides the design and API inspiration; this repository implements Python rendering, stream state, and a browser runtime independently.

The npm package declares **ISC** in its package metadata, while the upstream README says **MIT**. No upstream React implementation or stylesheet is bundled in this package. This repository's own implementation is distributed under the [ISC license](LICENSE). The original npm package is installed only as a development test oracle.

## Verification

```sh
pip install '.[dev,fasthtml,flask,django]'
pytest -q
npm ci --ignore-scripts
npx playwright install chromium
npm test
python -m build --no-isolation
```

The framework suite starts real FastHTML, Flask, and Django servers and checks their templates, assets, SSE responses, and word-by-word rendering in Chrome. Python tests additionally verify Django `collectstatic`, safe template output, application prefixes, and synchronous/asynchronous stream handling.

The parity suite renders the actual original npm package with React and compares it with the Python/browser port. It checks token splitting, the animation-name map, Markdown semantics, and cumulative updates. Additional checks cover paced word arrival, retained DOM nodes, corrections, Unicode, cancellation, reduced motion, and HTML safety. React and npm are only needed to run these comparison tests.

See [tests/fixtures.json](tests/fixtures.json) for the shared input cases and [tests/browser.mjs](tests/browser.mjs) for the original-versus-port comparisons. This is a tested compatibility surface, not a claim of complete React API or pixel parity.
