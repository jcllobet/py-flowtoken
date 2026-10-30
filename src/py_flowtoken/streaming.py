import json
import re
from dataclasses import dataclass, field


def tokenize(text: str, sep: str = "word") -> list[str]:
    if sep == "word":
        return [part for part in re.split(r"(\s+)", text) if part]
    if sep == "char":
        return list(text)
    if sep == "diff":
        return [text] if text else []
    raise ValueError('sep must be "word", "char", or "diff"')


@dataclass(frozen=True)
class Update:
    text: str
    delta: str
    reset: bool
    revision: int

    def as_dict(self):
        return {
            "text": self.text,
            "delta": self.delta,
            "reset": self.reset,
            "revision": self.revision,
        }

    def sse(self, event: str = "flowtoken") -> str:
        if not re.fullmatch(r"[\w-]+", event):
            raise ValueError("Invalid SSE event name")
        return f"event: {event}\ndata: {json.dumps(self.as_dict(), ensure_ascii=False)}\n\n"


@dataclass
class TextStream:
    text: str = ""
    revision: int = 0
    chunks: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.text and not self.chunks:
            self.chunks = [self.text]

    def update(self, text: str) -> Update:
        reset = not text.startswith(self.text)
        delta = text if reset else text[len(self.text) :]
        if text != self.text:
            self.revision += 1
            self.chunks = (
                ([text] if text else [])
                if reset
                else self.chunks + ([delta] if delta else [])
            )
            self.text = text
        return Update(self.text, delta, reset, self.revision)

    def append(self, delta: str) -> Update:
        return self.update(self.text + delta)

    def tokens(self, sep: str = "diff") -> list[str]:
        return self.chunks.copy() if sep == "diff" else tokenize(self.text, sep)


def encode_event(event: Update | str | bytes) -> str | bytes:
    if isinstance(event, Update):
        return event.sse()
    if isinstance(event, (str, bytes)):
        return event
    raise TypeError("Stream events must be Update, str, or bytes")


def iter_sse(events):
    for event in events:
        yield encode_event(event)


async def aiter_sse(events):
    async for event in events:
        yield encode_event(event)
