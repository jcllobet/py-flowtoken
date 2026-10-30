# py-flowtoken

A Python adaptation of [Ephibbs/flowtoken](https://github.com/Ephibbs/flowtoken) for animated text and Markdown streaming. It works with FastHTML and other server-rendered Python applications, without React or a JavaScript package manager in production.

Python renders the components and maintains stream state. A small, dependency-free browser module animates the words. A Python server cannot itself animate a browser's DOM.

## Install

```sh
pip install 'git+https://github.com/jcllobet/py-flowtoken.git@v0.1.1'
```

This project is published as a GitHub repository; it is not currently published on PyPI.

## Render text and Markdown

```python
from py_flowtoken import AnimatedMarkdown, AnimatedText

text = AnimatedText('Hello, world!', animation='fadeIn', interval_ms=35)
markdown = AnimatedMarkdown('# Hello\n\nA **streaming** answer.', sep='word')

print(text.render())
print(markdown.render())
```

Both components implement FastHTML's `__ft__` protocol, so they can be placed directly inside `Div`, `Main`, or another FastHTML component. Plain `.render()` returns HTML for other frameworks.

Serve the two files returned by `asset_path('flowtoken.js')` and `asset_path('flowtoken.css')`. Include them with `assets('/your/static/path')`, or use ordinary stylesheet/script tags. `asset_path` resolves the installed package's files; there is no CDN dependency.

A complete FastHTML/SSE example is in [examples/fasthtml_chat.py](examples/fasthtml_chat.py):

```sh
pip install '.[fasthtml]'
uvicorn examples.fasthtml_chat:app --port 8090
```

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
| FastHTML components | `__ft__` integration; optional FastHTML dependency |
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
pip install '.[dev]'
pytest -q
npm ci --ignore-scripts
npx playwright install chromium
npm test
python -m build --no-isolation
```

The browser suite renders the actual original npm package with React and compares it with the Python/browser port. It checks token splitting, the animation-name map, Markdown semantics, and cumulative updates. Additional checks cover paced word arrival, retained DOM nodes, corrections, Unicode, cancellation, reduced motion, and HTML safety. React and npm are only needed to run these comparison tests.

See [tests/fixtures.json](tests/fixtures.json) for the shared input cases and [tests/browser.mjs](tests/browser.mjs) for the original-versus-port comparisons. This is a tested compatibility surface, not a claim of complete React API or pixel parity.
