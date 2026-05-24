import json, re
from collections import defaultdict

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Find summary-type material: industry trends, policy changes, market analysis
industry_texts = []
for c in chunks:
    src = c.get('source','')
    if src.startswith('H3_') or not src: continue
    text = c['text']
    keywords = ['行业发展', '行业政策', '市场趋势', '宏观', '监管政策', '行业格局',
                '行业调整', '行业竞争', '市场规模', '行业增速', '行业集中度',
                '政策变化', '政策环境', '行业面临', '机遇与挑战', '行业发展趋势',
                '市场情况', '行业概况']
    for kw in keywords:
        if kw in text and len(text) > 100:
            parts = src.replace('.pdf','').split('_')
            company = parts[1] if len(parts) >= 2 else ''
            industry_texts.append({
                'chunk_id': c['id'],
                'source': src, 'page': c['page_num'],
                'company': company, 'keyword': kw,
                'preview': text[:300]
            })
            break

# Group by file name prefix (industry)
industry_groups = defaultdict(list)
for t in industry_texts:
    parts = t['source'].replace('.pdf','').split('_')
    industry = parts[0] if len(parts) >= 1 else ''
    industry_groups[industry].append(t)

print(f'Total summary-type candidates: {len(industry_texts)}')
for ind, items in sorted(industry_groups.items()):
    print(f'\n=== {ind} ({len(items)} items) ===')
    for item in items[:4]:
        print(f'  [{item["company"]}] p{item["page"]} keyword={item["keyword"]}')
        print(f'    {item["preview"][:120]}')
    if len(items) > 4:
        print(f'    ... {len(items)-4} more')

# Also find comparison pairs - companies with same metric
print('\n\n=== Comparison candidates (same metric across companies) ===')
metrics_per_company = defaultdict(lambda: defaultdict(list))
for c in chunks:
    src = c.get('source','')
    if src.startswith('H3_'): continue
    parts = src.replace('.pdf','').split('_')
    if len(parts) < 2: continue
    company = parts[1]
    text = c['text'][:500]
    for pattern, name in [(r'营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入'),
                          (r'净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '净利润'),
                          (r'毛利率[：\s]*?([\d,]+(?:\.\d+)?)%', '毛利率')]:
        m = re.search(pattern, text)
        if m:
            metrics_per_company[company][name].append((c['id'], c['source'], c['page_num'], m.group(1)))

for metric_name in ['营业收入', '净利润', '毛利率']:
    companies_with = [(c, v) for c, v in metrics_per_company.items() if metric_name in v]
    if len(companies_with) >= 2:
        print(f'\n{metric_name}: {len(companies_with)} companies available')
        for c, v in companies_with[:6]:
            vals = v[metric_name]
            val_strs = [x[3] for x in vals[:2]]
            print(f'  {c}: {", ".join(val_strs)}')
