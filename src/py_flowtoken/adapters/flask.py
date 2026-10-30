from io import BytesIO
from hashlib import sha256

from flask import Blueprint, Response, abort, send_file, stream_with_context, url_for
from markupsafe import Markup, escape

from ..assets import asset_path
from ..rendering import AnimatedImage, AnimatedMarkdown, AnimatedText
from ..streaming import iter_sse


def create_blueprint(url_prefix="/flowtoken"):
    blueprint = Blueprint("py_flowtoken", __name__, url_prefix=url_prefix)

    @blueprint.get("/<filename>")
    def asset(filename):
        try:
            content = asset_path(filename).read_bytes()
        except ValueError:
            abort(404)
        return send_file(
            BytesIO(content),
            download_name=filename,
            mimetype="text/javascript" if filename.endswith(".js") else "text/css",
            conditional=True,
            etag=sha256(content).hexdigest(),
            max_age=3600,
        )

    return blueprint


def asset_url(filename):
    asset_path(filename)
    return url_for("py_flowtoken.asset", filename=filename)


def asset_tags():
    return Markup(
        '<link rel="stylesheet" href="{}"><script type="module" src="{}"></script>'
    ).format(escape(asset_url("flowtoken.css")), escape(asset_url("flowtoken.js")))


def animated_text(content="", **options):
    return Markup(AnimatedText(content, **options).render())


def animated_markdown(content="", **options):
    return Markup(AnimatedMarkdown(content, **options).render())


def animated_image(src, alt="", **options):
    return Markup(AnimatedImage(src, alt, **options).render())


class FlowToken:
    def __init__(self, app=None, *, url_prefix="/flowtoken"):
        if app is not None:
            self.init_app(app, url_prefix=url_prefix)

    def init_app(self, app, *, url_prefix="/flowtoken"):
        if "py_flowtoken" in app.extensions:
            raise ValueError("py-flowtoken is already registered on this Flask app")
        app.register_blueprint(create_blueprint(url_prefix))
        app.jinja_env.globals.update(
            flowtoken_assets=asset_tags,
            flowtoken_asset_url=asset_url,
            flowtoken_text=animated_text,
            flowtoken_markdown=animated_markdown,
            flowtoken_image=animated_image,
        )
        app.extensions["py_flowtoken"] = self


def event_stream(events):
    if hasattr(events, "__aiter__"):
        raise TypeError("Flask event_stream requires a synchronous iterable")
    return Response(
        stream_with_context(iter_sse(events)),
        content_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
