import sys; sys.path.insert(0, '.')
from app.labs.lab1.intent_parser import intent_parser

prompts = [
    'Reduce to 10 weeks',
    'Add 2 more labs and reduce duration to 10 weeks',
    'Change course to 12 weeks',
    'Make it 10 weeks long',
    'Shorten the course to 8 weeks',
    'Add one more programming lab',
    'Increase final project weight by 5 percentage points',
    'reduce to 10 weeks',
    'change to 10 weeks',
    'set duration to 10 weeks',
]
for p in prompts:
    intents = intent_parser.parse(p)
    print(f'  [{len(intents)} intents] "{p}" -> {[i.intent_type for i in intents]}')
