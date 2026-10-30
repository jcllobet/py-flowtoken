import html
import math
import re
from dataclasses import dataclass

from .policy import SCHEMA

ANIMATIONS = {name: 'ft-'+name for name in SCHEMA['animations']}
DEFAULTS = SCHEMA['defaults']


def valid_easing(value: str) -> bool:
    if value in ('ease', 'ease-in', 'ease-out', 'ease-in-out', 'linear', 'step-start', 'step-end'):
        return True
    match = re.fullmatch(r'cubic-bezier\(\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*\)', value)
    if match:
        points = [float(number) for number in match.groups()]
        return all(math.isfinite(number) for number in points) and 0 <= points[0] <= 1 and 0 <= points[2] <= 1
    match = re.fullmatch(r'steps\(\s*([1-9]\d*)\s*(?:,\s*(start|end|jump-start|jump-end|jump-none|jump-both)\s*)?\)', value)
    return bool(match and (match[2] != 'jump-none' or int(match[1]) > 1))


def dimension(value: str | None) -> str | None:
    if value is not None and value != 'auto' and not re.fullmatch(r'\d+(?:\.\d+)?(?:px|rem|em|%|vh|vw)', value):
        raise ValueError('Invalid image dimension')
    return value


@dataclass(frozen=True)
class Options:
    sep: str = DEFAULTS['sep']
    animation: str | None = DEFAULTS['animation']
    animation_duration: str = DEFAULTS['duration']
    animation_timing_function: str = DEFAULTS['easing']
    interval_ms: int = DEFAULTS['interval']
    animate_initial: bool = DEFAULTS['animateInitial']

    def __post_init__(self):
        if self.sep not in SCHEMA['separators']:
            raise ValueError('Invalid separator')
        if self.animation is not None and not re.fullmatch(r'[a-zA-Z_][\w-]*', self.animation):
            raise ValueError('Invalid animation name')
        if not re.fullmatch(r'(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)', self.animation_duration):
            raise ValueError('Invalid animation duration')
        if not valid_easing(self.animation_timing_function):
            raise ValueError('Invalid animation timing function')
        if not isinstance(self.interval_ms, (int, float)) or not math.isfinite(self.interval_ms) or not 0 <= self.interval_ms <= 1000:
            raise ValueError('interval_ms must be between 0 and 1000')
        if not isinstance(self.animate_initial, bool):
            raise ValueError('animate_initial must be a boolean')

    def attributes(self) -> str:
        values = {'data-sep':self.sep, 'data-animation':self.animation or 'none',
            'data-duration':self.animation_duration, 'data-easing':self.animation_timing_function,
            'data-interval':str(self.interval_ms), 'data-animate-initial':str(self.animate_initial).lower()}
        return ' '.join(f'{key}="{html.escape(value, quote=True)}"' for key, value in values.items())

    def style(self, index: int = 0) -> str:
        name = ANIMATIONS.get(self.animation, self.animation) or 'none'
        return f'animation-name:{name};animation-duration:{self.animation_duration};animation-timing-function:{self.animation_timing_function};animation-iteration-count:1;animation-fill-mode:both'
