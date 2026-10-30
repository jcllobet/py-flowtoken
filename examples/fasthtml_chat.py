import asyncio
from pathlib import Path

from fasthtml.common import FastHTML, H1, Link, Main, P, Script
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles

from py_flowtoken import AnimatedText, TextStream, asset_path

app = FastHTML(
    default_hdrs=False,
    sess_cls=None,
    hdrs=(
        Link(rel="stylesheet", href="/flowtoken/flowtoken.css"),
        Script(src="/flowtoken/flowtoken.js", type="module"),
    ),
)
app.mount(
    "/flowtoken",
    StaticFiles(directory=str(Path(str(asset_path("flowtoken.js"))).parent)),
    name="flowtoken",
)


@app.get("/")
def index():
    return Main(
        H1("Smooth streaming from Python"),
        P("One paragraph, progressively revealed words, no React."),
        AnimatedText("", id="answer", animation="fadeIn", interval_ms=40),
        Script(
            """
            import {mount} from '/flowtoken/flowtoken.js';
            const view = mount(document.getElementById('answer'));
            const source = new EventSource('/stream');
            source.addEventListener('flowtoken', event => view.setText(JSON.parse(event.data).text));
            source.addEventListener('done', () => source.close());
            window.addEventListener('pagehide', () => {source.close(); view.destroy();}, {once:true});
        """,
            type="module",
        ),
    )


async def stream(request):
    async def chunks():
        state = TextStream()
        for chunk in [
            "Python sends ",
            "chunks. The browser ",
            "reveals their words smoothly, ",
            "without repeating the text already on screen.",
        ]:
            yield state.append(chunk).sse()
            await asyncio.sleep(0.5)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        chunks(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


app.router.add_route("/stream", stream)
