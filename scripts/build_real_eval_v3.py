"""修复：输出到文件避免终端问题"""
import os, sys, json, re, random
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
random.seed(42)

parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed")

REAL_COMPANIES = [
    "东方明珠", "中南文化", "中国长城", "中颖电子", "五粮液", "亿纬锂能",
    "今世缘", "伊利股份", "北京君正", "北方华创", "华录百纳", "华策影视",
    "华谊兄弟", "华闻集团", "双汇发展", "古井贡酒", "士兰微", "天威视讯",
    "山西汾酒", "景嘉微", "格力电器", "欧派家居", "歌华有线", "泸州老窖",
    "洋河股份", "海天味业", "电广传媒", "皖新传媒", "立讯精密", "紫光国微",
    "绝味食品", "美的集团", "老白干酒",
]

SECTORS = {}
for name in REAL_COMPANIES:
    for sector, companies in [
        ("传媒", ["东方明珠", "中南文化", "华录百纳", "华策影视", "华谊兄弟", "华闻集团", "天威视讯", "歌华有线", "电广传媒", "皖新传媒"]),
        ("白酒", ["五粮液", "古井贡酒", "山西汾酒", "泸州老窖", "老白干酒"]),
        ("消费", ["伊利股份", "双汇发展", "格力电器", "欧派家居", "海天味业", "立讯精密", "绝味食品", "美的集团", "今世缘", "洋河股份"]),
        ("半导体", ["中国长城", "中颖电子", "亿纬锂能", "北京君正", "北方华创", "士兰微", "景嘉微", "紫光国微"]),
    ]:
        if name in companies:
            SECTORS[name] = sector
            break

def extract_company(fname):
    basename = fname.replace('.json', '')
    parts = basename.split('_')
    if len(parts) >= 3 and parts[0] != 'H3':
        return parts[1]
    return None

# 1. 收集公司-文件映射和财务数据
company_files = defaultdict(list)
for fname in os.listdir(parsed_dir):
    if not fname.endswith('.json'):
        continue
    company = extract_company(fname)
    if company and company in REAL_COMPANIES:
        company_files[company].append(fname)

indicator_samples = defaultdict(list)
for company, files in company_files.items():
    for fname in files:
        filepath = os.path.join(parsed_dir, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        source = data.get('source', fname)
        for page in data.get('pages', []):
            page_num = page.get('page_num', 0)
            all_text = ""
            for block in page.get('text_blocks', []):
                all_text += block.get('text', '') + "\n"
            for tbl in page.get('tables', []):
                all_text += tbl.get('markdown', '') + "\n"
            if not all_text.strip():
                continue
            checks = {
                '营业收入': ['营业收入', '营业总收入'],
                '净利润': ['净利润', '归属于上市公司股东的净利润'],
                '毛利率': ['毛利率'],
                '净资产收益率': ['净资产收益率'],
                '每股收益': ['每股收益'],
                '研发投入': ['研发投入'],
                '总资产': ['总资产'],
                '资产负债率': ['资产负债率'],
                '经营活动现金流': ['经营活动产生的现金流量净额'],
            }
            for indicator, keywords in checks.items():
                for kw in keywords:
                    if kw in all_text:
                        idx = all_text.find(kw)
                        context = all_text[max(0,idx-5):idx+80].replace('\n', ' ').strip()
                        indicator_samples[indicator].append({
                            'company': company, 'source': source,
                            'page_num': page_num, 'context': context, 'file': fname,
                        })
                        break

# 2. 每家公司每个指标选最佳
company_indicator_best = {}
for indicator, items in indicator_samples.items():
    by_company = defaultdict(list)
    for s in items:
        by_company[s['company']].append(s)
    for company, items_list in by_company.items():
        best = max(items_list, key=lambda x: len(x['context']))
        company_indicator_best[(company, indicator)] = best

# 3. 生成问题
samples = []
used_pairs = set()

fact_templates = {
    '营业收入': ['{company}的营业收入是多少？'],
    '净利润': ['{company}的净利润是多少？'],
    '毛利率': ['{company}的毛利率是多少？'],
    '净资产收益率': ['{company}的净资产收益率(ROE)是多少？'],
    '每股收益': ['{company}的每股收益是多少？'],
    '研发投入': ['{company}的研发投入是多少？'],
    '总资产': ['{company}的总资产是多少？'],
    '资产负债率': ['{company}的资产负债率是多少？'],
    '经营活动现金流': ['{company}的经营性现金流是多少？'],
}

for (company, indicator), best in sorted(company_indicator_best.items()):
    if (company, indicator) in used_pairs:
        continue
    used_pairs.add((company, indicator))
    templates = fact_templates.get(indicator, ['{company}的{indicator}是多少？'])
    question = random.choice(templates).format(company=company, indicator=indicator)
    samples.append({
        'query': question, 'query_type': 'fact',
        'ground_truth_answer': best['context'],
        'source_file': best['source'], 'page_num': best['page_num'],
        'company': company, 'indicator': indicator,
    })

# 对比型
companies_with_data = list(set(k[0] for k in company_indicator_best.keys()))
random.shuffle(companies_with_data)
for i in range(min(20, len(companies_with_data) // 2)):
    c1, c2 = random.sample(companies_with_data, 2)
    inds1 = set(k[1] for k in company_indicator_best if k[0] == c1)
    inds2 = set(k[1] for k in company_indicator_best if k[0] == c2)
    common = inds1 & inds2
    if not common:
        continue
    ind = random.choice(list(common))
    best1 = company_indicator_best.get((c1, ind), {})
    best2 = company_indicator_best.get((c2, ind), {})
    samples.append({
        'query': f'{c1}和{c2}的{ind}对比如何？',
        'query_type': 'comparison',
        'ground_truth_answer': f'{c1}: {best1.get("context","")}\n{c2}: {best2.get("context","")}',
        'source_file': f"{best1.get('source','')}; {best2.get('source','')}",
        'page_num': '', 'company': f'{c1},{c2}', 'indicator': ind,
    })

# 行业汇总型
sector_groups = defaultdict(list)
for company in companies_with_data:
    sector = SECTORS.get(company, '其他')
    sector_groups[sector].append(company)
for sector, companies in sector_groups.items():
    if len(companies) < 2:
        continue
    texts = []
    for company in companies[:3]:
        for ind in ['营业收入', '净利润', '毛利率']:
            best = company_indicator_best.get((company, ind))
            if best:
                texts.append(f'{company}: {best["context"]}')
                break
    samples.append({
        'query': f'{sector}行业的发展趋势如何？',
        'query_type': 'summary',
        'ground_truth_answer': '\n'.join(texts) if texts else f'{sector}行业相关数据',
        'source_file': '', 'page_num': '',
        'company': sector, 'indicator': '行业分析',
    })

random.shuffle(samples)
samples = samples[:120]
for i, s in enumerate(samples):
    s['query_id'] = f'q_{i+1:04d}'

fact = sum(1 for s in samples if s['query_type'] == 'fact')
comp = sum(1 for s in samples if s['query_type'] == 'comparison')
summ = sum(1 for s in samples if s['query_type'] == 'summary')

# 写结果到文件
output_path = os.path.join(PROJECT_ROOT, 'data', 'eval', 'eval_dataset_real_v2.json')
result = {
    'metadata': {
        'total_samples': len(samples), 'fact_samples': fact,
        'comparison_samples': comp, 'summary_samples': summ,
        'description': '基于真实研报内容构建的评测集，每个问题都有实际文档支撑',
    },
    'samples': samples
}
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'OK 总数={len(samples)} 事实型={fact} 对比型={comp} 汇总型={summ}')
print(f'Saved to {output_path}')

# 打印前几个例子
for s in samples[:5]:
    print(f"[{s['query_id']}] [{s['query_type']}] {s['query']}")
    print(f"  答案: {s['ground_truth_answer'][:100]}")
