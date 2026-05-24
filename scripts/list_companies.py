import json, re, os
from collections import defaultdict

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# 找出所有含中文公司名的文件
source_companies = defaultdict(set)
for c in chunks:
    src = c.get('source', '')
    if src.startswith('H3_') or not src:
        continue
    parts = src.replace('.pdf','').split('_')
    if len(parts) >= 2:
        source_companies[parts[1]].add(src)

print(f"共 {len(source_companies)} 个不同公司\n")
for comp, sources in sorted(source_companies.items())[:30]:
    print(f"{comp}: {len(sources)}个文件")
    for s in sorted(sources)[:5]:
        print(f"  {s}")
    if len(sources) > 5:
        print(f"  ...还有{len(sources)-5}个")
