# Flask setup

Requires Python 3.10 or newer and Flask 3.1. The `flask` extra installs Flask, without installing Django or FastHTML.

## Install in an existing project

```sh
python -m pip install 'py-flowtoken[flask]'
```

## Register the adapter

```python
from flask import Flask, render_template
from py_flowtoken.adapters.flask import FlowToken

app = Flask(__name__)
FlowToken(app)

@app.get('/')
def index():
    return render_template('chat.html', message='Hello from Flask')
```

In `templates/chat.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Flask streaming</title>
  {{ flowtoken_assets() }}
</head>
<body>
  {{ flowtoken_text(message, id='answer', interval_ms=35) }}
</body>
</html>
```

The extension registers a blueprint serving `/flowtoken/flowtoken.js` and `/flowtoken/flowtoken.css`. It also registers these Jinja helpers:

| Helper | Result |
| --- | --- |
| `flowtoken_assets()` | CSS and module tags |
| `flowtoken_asset_url('flowtoken.js')` | Application-aware asset URL |
| `flowtoken_text(content, **options)` | Escaped animated text |
| `flowtoken_markdown(content, **options)` | Animated Markdown |
| `flowtoken_image(src, alt='', **options)` | Animated image |

These helpers return generated safe markup. Do not add `safe` filters to untrusted source text yourself.

## Application factories and prefixes

```python
flowtoken = FlowToken()

def create_app():
    app = Flask(__name__)
    flowtoken.init_app(app, url_prefix='/assets/flowtoken')
    return app
```

One extension instance can initialize multiple applications. URLs use Flask's `url_for`, including a configured application mount prefix. If only the asset router is needed, `create_blueprint(url_prefix=...)` is also available; it does not register the template helpers.

## Stream content

`py_flowtoken.adapters.flask.event_stream(events)` returns a Flask `Response` with SSE headers and preserves the request context while iterating. Pass a synchronous iterable of `TextStream` updates or SSE strings. Flask's WSGI adapter rejects asynchronous iterators; use a synchronous generator or an ASGI framework for asynchronous producers.

The browser wiring is shown in the [shared streaming guide](streaming.md).

## Run the complete example

```sh
git clone https://github.com/jcllobet/py-flowtoken.git
cd py-flowtoken
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[flask]'
python -m flask --app examples.flask_chat run --host 127.0.0.1 --port 8091
```

Open <http://127.0.0.1:8091>. The [application](../examples/flask_chat.py) and [Jinja template](../examples/templates/flask_chat.html) include a working SSE stream.
