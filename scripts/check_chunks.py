import json

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

target = [c for c in chunks if '华录百纳' in c.get('source','') and '同花顺_8' in c.get('source','')]
print(f'华录百纳_同花顺_8 chunks: {len(target)}')
for c in target[:5]:
    print(f'  id={c["id"]}, page={c["page_num"]}, text_preview={c["text"][:80]}')

target2 = [c for c in chunks if '华策影视' in c.get('source','') and '同花顺_5' in c.get('source','') and c.get('page_num') == '2']
print(f'\n华策影视_同花顺_5 第2页 chunks: {len(target2)}')
for c in target2[:3]:
    print(f'  id={c["id"]}, page={c["page_num"]}, text_preview={c["text"][:80]}')
