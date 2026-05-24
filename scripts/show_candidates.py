import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunk_map = {c['id']: c for c in chunks}

# 找到所有包含清晰财务指标的chunk
# 只看包含中文公司名的文件
candidates = []

for c in chunks:
    src = c['source']
    if src.startswith('H3_'):
        continue
    
    text = c['text'][:500]
    company_parts = src.replace('.pdf','').split('_')
    if len(company_parts) < 2:
        continue
    company = company_parts[1]
    
    # 找清晰的模式：营业收入XX亿元
    patterns = [
        (r'(?:公司|报告期内|本期)[^。]*?营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入', '亿元'),
        (r'(?:公司|报告期内|本期)[^。]*?归属于上市公司股东的净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润', '亿元'),
        (r'(?:公司|报告期内|本期)[^。]*?净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润', '亿元'),
        (r'(?:加权平均净资产收益率|净资产收益率)[：\s]*?([\d,]+(?:\.\d+)?)', '净资产收益率', '%'),
    ]
    
    for pat, name, unit in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            candidates.append({
                'chunk_id': c['id'],
                'source': src,
                'page': c['page_num'],
                'company': company,
                'indicator': name,
                'value': val + unit,
                'text_prefix': text[:200]
            })

# 输出去重的结果
seen = set()
for cand in candidates:
    key = (cand['chunk_id'], cand['indicator'])
    if key not in seen:
        seen.add(key)
        print(f'chunk_id={cand["chunk_id"]}')
        print(f'source={cand["source"]}')
        print(f'page={cand["page"]}')
        print(f'company={cand["company"]} | {cand["indicator"]}={cand["value"]}')
        print(f'text={cand["text_prefix"]}')
        print()
