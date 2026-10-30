import time

from django.shortcuts import render

from py_flowtoken import TextStream
from py_flowtoken.adapters.django import event_stream


def index(request):
    return render(request, "chat.html")


def stream(request):
    def chunks():
        state = TextStream()
        for chunk in [
            "Django sends ",
            "chunks. The browser ",
            "reveals their words smoothly.",
        ]:
            yield state.append(chunk)
            time.sleep(0.3)
        yield "event: done\ndata: {}\n\n"

    return event_stream(chunks())
