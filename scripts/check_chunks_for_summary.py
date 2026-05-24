import json

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['id']: c for c in json.load(f)}

# Show some example chunks for summary questions
cids = ['chunk_1171', 'chunk_56482', 'chunk_33398', 'chunk_3748', 'chunk_56494', 'chunk_26376', 'chunk_1185', 'chunk_26153']
for cid in cids:
    c = chunks.get(cid)
    if c:
        print(f'=== {cid} ({c["source"]} p{c["page_num"]}) ===')
        print(c['text'][:400])
        print()
