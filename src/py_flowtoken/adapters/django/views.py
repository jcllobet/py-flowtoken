from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe

from ...assets import asset_path
from ...streaming import aiter_sse, iter_sse


@require_safe
@cache_control(public=True, max_age=3600)
def asset(request, filename):
    try:
        content = asset_path(filename).read_bytes()
    except ValueError as error:
        raise Http404("Unknown FlowToken asset") from error
    return HttpResponse(
        content,
        content_type="text/javascript" if filename.endswith(".js") else "text/css",
    )


def event_stream(events):
    encoded = aiter_sse(events) if hasattr(events, "__aiter__") else iter_sse(events)
    response = StreamingHttpResponse(
        encoded, content_type="text/event-stream; charset=utf-8"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
