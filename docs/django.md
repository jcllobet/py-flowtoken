# Django setup

Requires Python 3.10 or newer and Django 5.2 LTS. The `django` extra installs Django, without installing Flask or FastHTML.

## Install in an existing project

```sh
python -m pip install 'py-flowtoken[django] @ git+https://github.com/jcllobet/py-flowtoken.git@v0.2.0'
```

## Enable the template tags and static assets

In `settings.py`, add the adapter:

```python
INSTALLED_APPS += ['py_flowtoken.adapters.django.apps.FlowTokenConfig']
```

Your project must also have `django.contrib.staticfiles` in `INSTALLED_APPS` once, as a standard Django project does. Keep your normal `STATIC_URL` and `STATIC_ROOT` settings.

In a template:

```html
{% load flowtoken %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Django streaming</title>
  {% flowtoken_assets %}
</head>
<body>
  {% flowtoken_text message id='answer' interval_ms=35 %}
</body>
</html>
```

`flowtoken_assets` uses Django's static-file storage by default. The packaged assets are namespaced as `py_flowtoken/flowtoken.js` and `py_flowtoken/flowtoken.css`. Development `runserver` serves them through `staticfiles`. In production, use your usual static-file server or CDN after running:

```sh
python manage.py collectstatic
```

Manifest-hashed static storage is supported because asset URLs are generated through Django's `static()` helper.

## Alternative: serve assets through the adapter's URLs

If you prefer application-served asset routes, set:

```python
FLOWTOKEN_ASSET_MODE = 'route'
```

Then add this to your project `urls.py`:

```python
from django.urls import include, path

urlpatterns += [
    path('flowtoken/', include('py_flowtoken.adapters.django.urls')),
]
```

The template tags resolve the URL namespace automatically. The prefix can be changed without editing the templates. This mode serves only the two allowed asset files and does not require `collectstatic` for them.

## Template tags

| Tag | Result |
| --- | --- |
| `{% flowtoken_assets %}` | CSS and module tags |
| `{% flowtoken_asset_url 'flowtoken.js' as script_url %}` | Asset URL in the selected mode |
| `{% flowtoken_text content id='answer' %}` | Escaped animated text |
| `{% flowtoken_markdown content sep='word' %}` | Animated Markdown |
| `{% flowtoken_image src alt='Example' %}` | Animated image |

The tag output is marked safe only after the library renders and escapes the content. Raw HTML in Markdown is escaped.

## Stream content

`py_flowtoken.adapters.django.event_stream(events)` returns `StreamingHttpResponse`. Pass an iterable of `TextStream` updates or preformatted SSE strings. Both synchronous and asynchronous iterators are supported; match the producer to your deployment: synchronous for WSGI, asynchronous for ASGI.

Keep each stream's `TextStream` instance inside the request/generator. The library does not create a shared global conversation.

The browser wiring is shown in the [shared streaming guide](streaming.md).

## Run the complete example

```sh
git clone https://github.com/jcllobet/py-flowtoken.git
cd py-flowtoken
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[django]'
python examples/django_demo/manage.py runserver 127.0.0.1:8092
```

Open <http://127.0.0.1:8092>. The [demo project](../examples/django_demo/) includes settings, URL routing, a template, and a synchronous SSE endpoint. It uses a public demo-only secret key; it is not a production project configuration.
