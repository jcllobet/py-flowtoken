import json
from pathlib import Path

from py_flowtoken import AnimatedMarkdown

fixtures = json.loads(Path("tests/fixtures.json").read_text())
print(
    json.dumps(
        [AnimatedMarkdown(value, sep="word").render() for value in fixtures["markdown"]]
    )
)
