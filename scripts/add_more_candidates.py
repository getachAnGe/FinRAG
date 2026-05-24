import json, os, re
from collections import defaultdict

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

with open('data/eval/eval_dataset_manual.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)
existing_samples = existing['samples']

existing_set = set()
for s in existing_samples:
    existing_set.add((s['company'], s['indicator'], s['ground_truth_answer']))

# Find good candidates that are not in existing set
candidates = []
for c in chunks:
    src = c['source']
    if src.startswith('H3_'): continue
    parts = src.replace('.pdf','').split('_')
    if len(parts) < 2: continue
    company = parts[1]
    
    text = c['text'][:600]
    page = c['page_num']
    
    # Try to extract value with unit
    patterns = [
        (r'营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入', '亿元'),
        (r'净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '净利润', '亿元'),
        (r'归属于上市公司股东的净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '净利润', '亿元'),
        (r'加权平均净资产收益率[：\s]*?([\d,]+(?:\.\d+)?)%', '净资产收益率', '%'),
        (r'资产负债率[：\s]*?([\d,]+(?:\.\d+)?)%', '资产负债率', '%'),
        (r'毛利率[：\s]*?([\d,]+(?:\.\d+)?)%', '毛利率', '%'),
        (r'研发投入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '研发投入', '亿元'),
        (r'总资产[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '总资产', '亿元'),
        (r'基本每股收益[：\s]*?([\d,]+(?:\.\d+)?)\s*元', '每股收益', '元'),
    ]
    
    for pat, indicator, unit in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1) + unit
            key = (company, indicator, val)
            if key not in existing_set:
                candidates.append({
                    'company': company, 'source': src, 'page': page,
                    'indicator': indicator, 'value': val, 'chunk_id': c['id'],
                    'text_preview': text[:150]
                })
                existing_set.add(key)
                break

print(f'新增候选: {len(candidates)}\n')

# Verify each candidate
added = 0
for cand in candidates:
    if added >= 12: break
    cid = cand['chunk_id']
    c = next(x for x in chunks if x['id'] == cid)
    text = c['text']
    val_clean = cand['value'].replace(',', '')
    found = val_clean in text.replace(',', '')
    
    if found:
        src_short = cand['source'].replace('.pdf', '')
        query = f'在{src_short}第{cand["page"]}页中，{cand["company"]}的{cand["indicator"]}是多少？'
        existing_samples.append({
            "query": query, "query_type": "fact",
            "ground_truth_answer": cand['value'],
            "ground_truth_chunk_id": cid,
            "source_file": cand['source'],
            "page_num": cand['page'],
            "company": cand['company'],
            "indicator": cand['indicator']
        })
        added += 1
        print(f'  ✅ [{cand["company"]}] {cand["indicator"]}={cand["value"]} ({cand["source"]} 第{cand["page"]}页)')

print(f'\n新增: {added}条')
print(f'总计: {len(existing_samples)}条')

# Save result
company_counts = defaultdict(int)
for s in existing_samples:
    company_counts[s['company']] += 1

result = {
    'metadata': {
        'total_samples': len(existing_samples),
        'fact_samples': len(existing_samples),
        'description': f'手动验证评测集，{len(existing_samples)}条，{len(company_counts)}家公司'
    },
    'samples': existing_samples
}
with open('data/eval/eval_dataset_manual.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'已保存 {len(existing_samples)}条')

for comp, cnt in sorted(company_counts.items()):
    print(f'  {comp}: {cnt}条')
