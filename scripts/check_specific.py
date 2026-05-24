import json, os

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

chunk_map = {c['id']: c for c in chunks}

# Check failed ones specifically
checklist = [
    ('chunk_31296', '紫光国微', '61.46亿元'),
    ('chunk_31302', '紫光国微', '3.34亿元'),
    ('chunk_26332', '亿纬锂能', '206.80亿元'),
    ('chunk_36992', '双汇发展', '594.6亿元'),
    ('chunk_49676', '山西汾酒', '33.48%'),
    ('chunk_22284', '皖新传媒', '80.02亿元'),
]

for cid, company, val in checklist:
    c = chunk_map.get(cid)
    if not c:
        print(f'{company}: {cid} not found')
        continue
    text = c['text']
    val_clean = val.replace(',', '').replace('亿元','').replace('%','').replace('万元','').replace('元','')
    found = val_clean in text.replace(',', '')
    print(f'{company}: val={val} found={found} in {c["source"]} page={c["page_num"]}')
    if not found:
        # find what's actually in text
        import re
        nums = re.findall(r'[\d.]+', text)
        print(f'  numbers in text: {nums[:10]}')
