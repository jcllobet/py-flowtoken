import time

from flask import Flask, render_template

from py_flowtoken import TextStream
from py_flowtoken.adapters.flask import FlowToken, event_stream

app = Flask(__name__)
FlowToken(app)


@app.get("/")
def index():
    return render_template("flask_chat.html")


@app.get("/stream")
def stream():
    def chunks():
        state = TextStream()
        for chunk in [
            "Flask sends ",
            "chunks. The browser ",
            "reveals their words smoothly.",
        ]:
            yield state.append(chunk)
            time.sleep(0.3)
        yield "event: done\ndata: {}\n\n"

    return event_stream(chunks())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8091)
