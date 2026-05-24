import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

failures = [
    ("半导体_紫光国微_同花顺_4.pdf", "1", "61.46"),
    ("半导体_亿纬锂能_同花顺_7.pdf", "1", "206.80"),
    ("消费_双汇发展_同花顺_8.pdf", "1", "594.6"),
    ("白酒_山西汾酒_同花顺_5.pdf", "3", "33.48"),
    ("传媒_东方明珠_同花顺_3.pdf", "3", "4.08亿"),
    ("传媒_中南文化_同花顺_5.pdf", "11", "518.32"),
    ("传媒_欧派家居_同花顺_7.pdf", "16", "1,250"),
    ("传媒_中南文化_同花顺_5.pdf", "11", "2,677亿"),
    ("传媒_东方明珠_同花顺_6.pdf", "12", "IPTV"),
    ("白酒_泸州老窖_同花顺_4.pdf", "28", "量减质升"),
    ("半导体_中国长城_同花顺_4.pdf", "12", "市场牵引"),
]

for src, page, val in failures:
    val_clean = val.replace(',', '')
    found = False
    for c in chunks:
        if src not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        text = c['text']
        if val_clean in text.replace(',', ''):
            print(f'  ✅ {src} p{page}: "{val}" found in {c["id"]}')
            found = True
            break
    if not found:
        print(f'  ❌ {src} p{page}: "{val}" NOT FOUND')
        # Show the page's chunks
        for c in chunks:
            if src not in c['source']: continue
            if str(c['page_num']) != str(page): continue
            print(f'     existing chunk: {c["id"]} text[:200]={c["text"][:200]}')
            break
