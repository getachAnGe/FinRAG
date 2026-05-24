import json

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f'总切片数: {len(chunks)}')
print()
print('前5个切片内容预览:')
for i, chunk in enumerate(chunks[:5]):
    print(f'--- 切片 {i+1} ---')
    print(f"来源: {chunk['source']} 第{chunk['page_num']}页")
    print(f"内容: {chunk['text'][:300]}...")
    print()
