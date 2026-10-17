"""Run after a frontend build; fail if evaluation-only prompts enter product files."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cases = json.loads(Path(__file__).with_name('cases.json').read_text())
files = [path for folder in ('src', 'public', 'dist') for path in (root / 'frontend' / folder).rglob('*') if path.is_file()]
assert (root / 'frontend' / 'dist' / 'index.html').exists(), 'Build frontend before checking isolation'
for case in cases:
    for message in case['messages']:
        content = message['content']
        variants = [content, json.dumps(content)[1:-1]]
        for path in files:
            text = path.read_text(errors='ignore')
            assert not any(value in text for value in variants), f"Held-out prompt leaked: {case['case_id']} in {path.relative_to(root)}"
print(f'PASS: {len(cases)} evaluation-only cases absent from frontend source, public files and built bundle')
