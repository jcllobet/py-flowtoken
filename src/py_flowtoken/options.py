import html
import re
from dataclasses import dataclass

from .streaming import tokenize

ANIMATIONS = {
    name: f"ft-{name}"
    for name in (
        "fadeIn",
        "slideUp",
        "wave",
        "elastic",
        "bounceIn",
        "rotateIn",
        "colorTransition",
        "fadeAndScale",
        "slideInFromLeft",
        "blurIn",
        "typewriter",
        "highlight",
        "blurAndSharpen",
        "dropIn",
    )
}


@dataclass(frozen=True)
class Options:
    sep: str = "word"
    animation: str | None = "fadeIn"
    animation_duration: str = "0.25s"
    animation_timing_function: str = "ease-out"
    interval_ms: int = 35

    def __post_init__(self):
        tokenize("", self.sep)
        if self.animation is not None and not re.fullmatch(
            r"[a-zA-Z_][\w-]*", self.animation
        ):
            raise ValueError("Invalid animation name")
        if not re.fullmatch(
            r"(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)", self.animation_duration
        ):
            raise ValueError("Invalid animation duration")
        if self.animation_timing_function not in {
            "ease",
            "ease-in",
            "ease-out",
            "ease-in-out",
            "linear",
        }:
            raise ValueError("Invalid animation timing function")
        if not 0 <= self.interval_ms <= 1000:
            raise ValueError("interval_ms must be between 0 and 1000")

    def attributes(self) -> str:
        values = {
            "data-sep": self.sep,
            "data-animation": self.animation or "none",
            "data-duration": self.animation_duration,
            "data-easing": self.animation_timing_function,
            "data-interval": str(self.interval_ms),
        }
        return " ".join(
            f'{key}="{html.escape(value, quote=True)}"' for key, value in values.items()
        )

    def style(self, index: int = 0) -> str:
        name = ANIMATIONS.get(self.animation, self.animation) or "none"
        return f"animation-name:{name};animation-duration:{self.animation_duration};animation-timing-function:{self.animation_timing_function};animation-delay:{index * self.interval_ms}ms;animation-iteration-count:1;animation-fill-mode:both"
