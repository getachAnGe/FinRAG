import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Search for chunks mentioning "行业发展" or "行业格局" with substantial text
found = 0
for c in chunks:
    src = c.get('source','')
    if src.startswith('H3_'): continue
    text = c['text']
    if ('行业发展' in text or '行业格局和趋势' in text or '公司所处行业情况' in text) and len(text) > 300:
        print(f'=== {c["id"]} ({c["source"]} p{c["page_num"]}) ===')
        print(text[:500])
        print()
        found += 1
        if found >= 8:
            break
