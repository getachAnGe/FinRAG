import json
with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['id']: c for c in json.load(f)}

for cid in ['chunk_46486', 'chunk_45928', 'chunk_49678']:
    c = chunks.get(cid)
    if c:
        print(f'{"="*60}')
        print(f'chunk: {cid}')
        print(f'source: {c["source"]}, page: {c["page_num"]}')
        print(f'{"="*60}')
        print(c['text'][:500])
        print()
