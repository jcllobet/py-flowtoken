import html
import json
from pathlib import Path

from py_flowtoken import AnimatedImage, AnimatedMarkdown, AnimatedText

fixtures = json.loads(Path('tests/fixtures.json').read_text())
cases = {
    'diffBefore': AnimatedMarkdown('Hello').render(),
    'diffAfter': AnimatedMarkdown('Hello world').render(),
    'structuredBefore': AnimatedMarkdown('**Hello** world').render(),
    'structuredAfter': AnimatedMarkdown('**Hello** world again').render(),
    'table': AnimatedMarkdown('| Left | Right |\n|:---|---:|\n| one | two |').render(),
    'badLink': AnimatedMarkdown('[broken](http://[)').render(),
    'multilineCode': AnimatedMarkdown('```python\nfirst = 1\nsecond = 2\n```', code_style='monokai').render(),
    'image': AnimatedMarkdown('![alt](/delayed.png)', img_height='7rem').render(),
    'imageAfter': AnimatedMarkdown('![alt](/delayed.png)\n\nMore text', img_height='7rem').render(),
    'standaloneImage': AnimatedImage('/delayed.png', height='7rem').render(),
    'initial': AnimatedText('Hello initial animation', animation_duration='2s', interval_ms=0).render(),
    'disabled': AnimatedMarkdown('Hello world again',animation=None).render(),
    'custom': AnimatedMarkdown('<badge>Hello</badge>',custom_components={'badge':lambda node:'<mark data-ft-key="badge">'+html.escape(node.content)+'</mark>'}).render(),
    'customAfter': AnimatedMarkdown('<badge>Hello</badge>\n\nMore',custom_components={'badge':lambda node:'<mark data-ft-key="badge">'+html.escape(node.content)+'</mark>'}).render(),
}
print(json.dumps({'markdown':[AnimatedMarkdown(value,sep='word').render() for value in fixtures['markdown']],'cases':cases}))
