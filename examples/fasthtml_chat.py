import asyncio

from fasthtml.common import FastHTML, H1, Main, P, Script

from py_flowtoken import AnimatedText, TextStream
from py_flowtoken.adapters.fasthtml import asset_tags, event_stream, mount_assets

app = FastHTML(default_hdrs=False, sess_cls=None, hdrs=asset_tags())
mount_assets(app)


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
            yield state.append(chunk)
            await asyncio.sleep(0.5)
        yield "event: done\ndata: {}\n\n"

    return event_stream(chunks())


app.router.add_route("/stream", stream)
