import json, re
from collections import defaultdict

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Find more summary-worthy chunks (long narrative text about industry)
print("=== SUMMARY CANDIDATES ===")
found = 0
for c in chunks:
    src = c.get('source','')
    if src.startswith('H3_'): continue
    text = c['text']
    if len(text) < 300: continue
    
    keywords_found = []
    for kw in ['报告期内', '行业发展', '行业格局', '政策', '市场', '趋势', '公司实现', '同比增长']:
        if kw in text: keywords_found.append(kw)
    
    if len(keywords_found) >= 3 and not text.startswith('['):
        parts = src.replace('.pdf','').split('_')
        company = parts[1] if len(parts) >= 2 else ''
        if company in ['东方明珠', '中南文化', '中国长城', '五粮液', '泸州老窖', '格力电器', '伊利股份', '北方华创', '今世缘', '欧派家居', '海天味业']:
            print(f'chunk_id={c["id"]}, company={company}, source={c["source"]}, page={c["page_num"]}')
            print(f'  {text[:200]}')
            print()
            found += 1
            if found >= 25: break
