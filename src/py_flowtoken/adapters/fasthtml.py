from pathlib import Path

from fasthtml.common import Link, Script
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles

from ..assets import asset_path
from ..streaming import aiter_sse, iter_sse


def asset_tags(url_prefix="/flowtoken"):
    prefix = url_prefix.rstrip("/")
    return (
        Link(rel="stylesheet", href=prefix + "/flowtoken.css"),
        Script(src=prefix + "/flowtoken.js", type="module"),
    )


def mount_assets(app, url_prefix="/flowtoken"):
    app.mount(
        url_prefix.rstrip("/"),
        StaticFiles(directory=str(Path(str(asset_path("flowtoken.js"))).parent)),
        name="py_flowtoken",
    )


def event_stream(events):
    encoded = aiter_sse(events) if hasattr(events, "__aiter__") else iter_sse(events)
    return StreamingResponse(
        encoded,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
