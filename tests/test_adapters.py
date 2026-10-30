import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from py_flowtoken import AnimatedText, TextStream, asset_path
from py_flowtoken.core import AnimatedText as LegacyAnimatedText


ROOT = Path(__file__).resolve().parents[1]


def test_core_is_framework_independent():
    code = "import py_flowtoken,sys; print(any(x in sys.modules for x in ['flask','django','fasthtml']))"
    output = subprocess.check_output(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        text=True,
    )
    assert output.strip() == "False"
    assert AnimatedText is LegacyAnimatedText


def test_flask_factory_assets_templates_and_stream():
    flask = pytest.importorskip("flask")
    from py_flowtoken.adapters.flask import FlowToken, event_stream

    extension = FlowToken()
    app = flask.Flask(__name__)
    extension.init_app(app, url_prefix="/widgets/flowtoken")

    @app.get("/")
    def index():
        return flask.render_template_string(
            '{{ flowtoken_assets() }}{{ flowtoken_text(value, id="answer") }}{{ flowtoken_markdown("**bold**") }}{{ flowtoken_image("/image.png", "Example") }}',
            value="<script>alert(1)</script>",
        )

    @app.get("/stream")
    def stream():
        state = TextStream()
        return event_stream(
            iter(
                [
                    state.append("Hello "),
                    state.append("world"),
                    "event: done\ndata: {}\n\n",
                ]
            )
        )

    client = app.test_client()
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert "/widgets/flowtoken/flowtoken.js" in body
    assert 'data-flowtoken="text"' in body
    assert "<strong>" in body
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body
    for name, mime in [("flowtoken.js", "javascript"), ("flowtoken.css", "text/css")]:
        response = client.get("/widgets/flowtoken/" + name)
        assert response.status_code == 200
        assert response.data == asset_path(name).read_bytes()
        assert mime in response.content_type
        assert client.head("/widgets/flowtoken/" + name).status_code == 200
        assert (
            client.get(
                "/widgets/flowtoken/" + name,
                headers={"If-None-Match": response.headers["ETag"]},
            ).status_code
            == 304
        )
    assert client.get("/widgets/flowtoken/core.py").status_code == 404
    assert client.post("/widgets/flowtoken/flowtoken.js").status_code == 405
    response = client.get("/stream")
    assert response.mimetype == "text/event-stream"
    assert '"text": "Hello world"' in response.get_data(as_text=True)
    assert response.headers["X-Accel-Buffering"] == "no"
    with pytest.raises(ValueError):
        extension.init_app(app)
    second = flask.Flask("second")
    extension.init_app(second, url_prefix="/other")
    assert second.test_client().get("/other/flowtoken.css").status_code == 200


def test_flask_prefix_and_async_rejection():
    flask = pytest.importorskip("flask")
    from py_flowtoken.adapters.flask import FlowToken, event_stream

    app = flask.Flask("prefix")
    FlowToken(app)
    with app.test_request_context(environ_overrides={"SCRIPT_NAME": "/mounted"}):
        assert "/mounted/flowtoken/flowtoken.js" in str(
            app.jinja_env.globals["flowtoken_assets"]()
        )

        async def events():
            yield TextStream().append("Hello")

        with pytest.raises(TypeError, match="synchronous"):
            event_stream(events())


@pytest.fixture(scope="module")
def django_ready():
    django = pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            SECRET_KEY="test-only",
            ROOT_URLCONF="django_urls",
            STATIC_URL="/static/",
            INSTALLED_APPS=[
                "django.contrib.staticfiles",
                "py_flowtoken.adapters.django.apps.FlowTokenConfig",
            ],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                }
            ],
        )
        django.setup()
    return django


def test_django_route_templates_and_stream(django_ready):
    from django.template import Context, Template
    from django.test import Client, override_settings
    from py_flowtoken.adapters.django import event_stream

    with override_settings(FLOWTOKEN_ASSET_MODE="route"):
        rendered = Template(
            '{% load flowtoken %}{% flowtoken_assets %}{% flowtoken_text value id="answer" %}{% flowtoken_markdown "**bold**" %}{% flowtoken_image "/image.png" "Example" %}'
        ).render(Context({"value": "<script>alert(1)</script>"}))
        assert "/widgets/flowtoken/flowtoken.js" in rendered
        assert 'data-flowtoken="text"' in rendered
        assert "<strong>" in rendered
        assert "<script>alert(1)</script>" not in rendered
        assert "&lt;script&gt;" in rendered
    client = Client()
    for name, mime in [("flowtoken.js", "javascript"), ("flowtoken.css", "text/css")]:
        response = client.get("/widgets/flowtoken/" + name)
        assert response.status_code == 200
        assert mime in response.headers["Content-Type"]
        assert response.content == asset_path(name).read_bytes()
        assert client.head("/widgets/flowtoken/" + name).status_code == 200
    assert client.get("/widgets/flowtoken/core.py").status_code == 404
    assert client.post("/widgets/flowtoken/flowtoken.js").status_code == 405
    response = event_stream(iter([TextStream().append("Hello")]))
    assert b'"text": "Hello"' in b"".join(response.streaming_content)
    assert response.headers["X-Accel-Buffering"] == "no"


def test_django_collectstatic(django_ready, tmp_path):
    from django.core.management import call_command
    from django.template import Context, Template
    from django.test import override_settings

    with override_settings(STATIC_ROOT=str(tmp_path), FLOWTOKEN_ASSET_MODE="static"):
        call_command("collectstatic", interactive=False, verbosity=0)
        for name in ["flowtoken.js", "flowtoken.css"]:
            assert (tmp_path / "py_flowtoken" / name).read_bytes() == asset_path(
                name
            ).read_bytes()
        rendered = Template("{% load flowtoken %}{% flowtoken_assets %}").render(
            Context()
        )
        assert "/static/py_flowtoken/flowtoken.js" in rendered
        assert "/static/py_flowtoken/flowtoken.css" in rendered


def test_django_async_stream(django_ready):
    from py_flowtoken.adapters.django import event_stream

    async def run():
        async def events():
            state = TextStream()
            yield state.append("one ")
            yield state.append("two")

        response = event_stream(events())
        assert response.is_async
        parts = [part async for part in response.streaming_content]
        assert b'"text": "one two"' in b"".join(parts)

    asyncio.run(run())


def test_fasthtml_mount_and_stream():
    pytest.importorskip("fasthtml")
    from fasthtml.common import FastHTML, Main
    from starlette.testclient import TestClient
    from py_flowtoken.adapters.fasthtml import asset_tags, event_stream, mount_assets

    app = FastHTML(
        default_hdrs=False, sess_cls=None, hdrs=asset_tags("/widgets/flowtoken")
    )
    mount_assets(app, "/widgets/flowtoken")

    @app.get("/")
    def index():
        return Main(AnimatedText("<script>alert(1)</script>"))

    async def stream(request):
        async def events():
            yield TextStream().append("Hello from FastHTML")

        return event_stream(events())

    app.router.add_route("/stream", stream)
    with TestClient(app) as client:
        response = client.get("/")
        assert "/widgets/flowtoken/flowtoken.js" in response.text
        assert "<script>alert(1)</script>" not in response.text
        assert "&lt;script&gt;" in response.text
        for name in ["flowtoken.js", "flowtoken.css"]:
            assert (
                client.get("/widgets/flowtoken/" + name).content
                == asset_path(name).read_bytes()
            )
        assert client.get("/widgets/flowtoken/core.py").status_code == 404
        response = client.get("/stream")
        assert "text/event-stream" in response.headers["content-type"]
        assert "Hello from FastHTML" in response.text


def test_django_manifest_static_storage(django_ready, tmp_path):
    from django.core.management import call_command
    from django.template import Context, Template
    from django.test import override_settings

    with override_settings(
        STATIC_ROOT=str(tmp_path),
        FLOWTOKEN_ASSET_MODE="static",
        DEBUG=False,
        STORAGES={
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
            }
        },
    ):
        call_command("collectstatic", interactive=False, verbosity=0)
        rendered = Template("{% load flowtoken %}{% flowtoken_assets %}").render(
            Context()
        )
        assert "/static/py_flowtoken/flowtoken." in rendered
        assert "/static/py_flowtoken/flowtoken.js" not in rendered
        assert "/static/py_flowtoken/flowtoken.css" not in rendered
        assert (tmp_path / "staticfiles.json").exists()
