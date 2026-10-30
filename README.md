# py-flowtoken

Smooth, word-by-word text and Markdown streaming for **FastHTML, Flask, and Django**. Python 3.10+. No React or Node runtime required.

## Install

```sh
pip install py-flowtoken
```

Choose your framework to install its dependencies and follow the setup guide:

| Framework | Install | Setup |
| --- | --- | --- |
| FastHTML | `pip install "py-flowtoken[fasthtml]"` | [FastHTML guide](https://github.com/jcllobet/py-flowtoken/blob/main/docs/fasthtml.md) |
| Flask | `pip install "py-flowtoken[flask]"` | [Flask guide](https://github.com/jcllobet/py-flowtoken/blob/main/docs/flask.md) |
| Django | `pip install "py-flowtoken[django]"` | [Django guide](https://github.com/jcllobet/py-flowtoken/blob/main/docs/django.md) |

![FlowToken animation demo](https://nextjs-omega-five-46.vercel.app/demo.gif)

*Demo from [FlowToken](https://github.com/Ephibbs/flowtoken), the original library this package adapts.*

## Try it with FastHTML

Install the FastHTML extra above, then save this as `demo.py`:

```python
from fasthtml.common import FastHTML
from py_flowtoken import AnimatedText
from py_flowtoken.adapters.fasthtml import asset_tags, mount_assets

app = FastHTML(hdrs=asset_tags())
mount_assets(app)

@app.get('/')
def home():
    return AnimatedText('Hello from Python, one word at a time.', id='answer')
```

Run `uvicorn demo:app --reload` and open **http://127.0.0.1:8000**. The text animates as the page loads.

## Stream updates

Connect incoming text to the browser renderer:

```javascript
import {mount} from '/flowtoken/flowtoken.js';

const view = mount(document.getElementById('answer'));
view.setText('Hello');
view.setText('Hello world');
```

Use `setText(snapshot)` for the full current text, or `append(chunk)` for new text only. Existing words stay in place; corrections update the changed portion. The [streaming guide](https://github.com/jcllobet/py-flowtoken/blob/main/docs/streaming.md) connects a Python generator to the browser with SSE.

## Configure text or Markdown

```python
from py_flowtoken import AnimatedMarkdown

answer = AnimatedMarkdown(
    '**Hello**, world!',
    id='answer',
    sep='word',
    animation='fadeIn',
    animation_duration='0.25s',
    interval_ms=35,
    code_style='monokai',
)
```

Use `sep='word'` for word-by-word animation, `'char'` for characters, or `'diff'` for appended chunks. Text defaults to word mode; Markdown defaults to diff mode. Set `animation=None` to disable animation. Reduced-motion preferences are respected automatically.

Markdown includes tables, task lists, syntax highlighting, code-copy buttons, images, and Python custom tags. See the [API and configuration reference](https://github.com/jcllobet/py-flowtoken/blob/main/docs/api.md) for animation names, image sizing, custom components, and lifecycle methods.

[MIT license](https://github.com/jcllobet/py-flowtoken/blob/main/LICENSE). An independent Python adaptation of [Ephibbs/flowtoken](https://github.com/Ephibbs/flowtoken), not an official release from its maintainers.
