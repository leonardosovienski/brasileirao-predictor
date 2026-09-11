"""Extract only user-visible messages from this exact task's local history."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
source = Path('C:/Users/leona/.codex/sessions/2026/09/09/rollout-2026-09-09T21-05-07-01a088a1-e7c6-7e93-9ae6-dacd3b43b2a5.jsonl')
raw = source.read_bytes()
messages = []
for number, line in enumerate(raw.splitlines(), 1):
    row = json.loads(line)
    payload = row.get('payload', {})
    if row.get('type') != 'response_item' or payload.get('type') != 'message':
        continue
    if payload.get('role') not in {'user', 'assistant'} or payload.get('channel') in {'analysis', 'summary'}:
        continue
    text = '\n'.join(item['text'] for item in payload.get('content', []) if item.get('type') in {'input_text', 'output_text', 'text'} and 'text' in item)
    if not text:
        continue
    # No tool outputs, internal reasoning, system or developer instructions are exported.
    text = re.sub(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{30,}', '[REDACTED_TOKEN]', text)
    messages.append(dict(source_line=number, timestamp=row.get('timestamp'), role=payload['role'], phase=payload.get('phase'), text=text))
(root / 'chat-messages.json').write_text(json.dumps(messages, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
text = '\n\n'.join(f'[{i + 1:03}] {m["role"]} / {m["phase"]} / linha {m["source_line"]}\n{m["text"]}' for i, m in enumerate(messages))
(root / 'chat-messages.txt').write_text(text, encoding='utf-8')
meta = dict(source=str(source), source_snapshot_bytes=len(raw), source_snapshot_sha256=hashlib.sha256(raw).hexdigest(),
            messages=len(messages), visible_text_characters=len(text),
            app_tool_limitation='8 turns, but 5 returned with no items; local exact-thread record used for missing messages',
            excluded='tool payloads, system/developer content and internal reasoning')
(root / 'chat-recovery.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(meta, ensure_ascii=False))
print(text[:24000])
