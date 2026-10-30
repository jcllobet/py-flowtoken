# FastHTML setup

Requires Python 3.10 or newer.

## Install in an existing project

```sh
python -m pip install 'py-flowtoken[fasthtml] @ git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
```

## Add the assets and components

```python
from fasthtml.common import FastHTML, H1, Main
from py_flowtoken import AnimatedText
from py_flowtoken.adapters.fasthtml import asset_tags, mount_assets

app = FastHTML(default_hdrs=False, hdrs=asset_tags())
mount_assets(app)

@app.get('/')
def index():
    return Main(H1('Streaming text'), AnimatedText('Hello from Python', id='answer'))
```

`asset_tags()` adds the CSS and browser module. `mount_assets(app)` serves those two packaged files under `/flowtoken/`. The components implement FastHTML's `__ft__` protocol, so no manual HTML escaping or raw-string wrapper is needed.

For a different prefix, pass the same value to both helpers:

```python
app = FastHTML(hdrs=asset_tags('/assets/flowtoken'))
mount_assets(app, '/assets/flowtoken')
```

## Stream content

`py_flowtoken.adapters.fasthtml.event_stream(events)` returns a Starlette streaming response. It accepts a synchronous or asynchronous iterable of `TextStream` updates or preformatted SSE strings.

The browser should mount `#answer` and call `view.setText(JSON.parse(event.data).text)` when each `flowtoken` event arrives. The [shared streaming guide](streaming.md) contains the browser code.

## Run the complete example

```sh
git clone https://github.com/jcllobet/py-flowtoken.git
cd py-flowtoken
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[fasthtml]'
uvicorn examples.fasthtml_chat:app --host 127.0.0.1 --port 8090
```

Open <http://127.0.0.1:8090>. [The example](../examples/fasthtml_chat.py) includes the component, asset routes, asynchronous SSE endpoint, and browser connection.
