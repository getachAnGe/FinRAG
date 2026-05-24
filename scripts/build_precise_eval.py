"""
构建精准评测集：问题指向唯一答案
策略：从每个chunk里的具体数据反推问题，确保一问一答唯一对应
"""
import os, sys, json, re, random
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

chunks_path = os.path.join(PROJECT_ROOT, "data", "chunks", "all_chunks.json")
with open(chunks_path, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"扫描 {len(chunks)} 个chunk...")

# 识别含具体财务数据的chunk
samples = []

# 精确匹配指标及其上下文中的数值
patterns = [
    # (关键词, 问题模板, 数据提取方式)
    (r'(?:营业收入|营业总收入)[：\s]*?(\d[\d,.]+\s*(?:亿元|万元|元))', '营业收入'),
    (r'(?:归属于上市公司股东的净利润|归属于母公司所有者的净利润)[：\s]*?(\d[\d,.]+\s*(?:亿元|万元|元))', '净利润'),
    (r'(?:加权平均净资产收益率|净资产收益率)[：\s]*?(\d[\d,.]+\s*%)', '净资产收益率'),
    (r'(?:基本每股收益|每股收益)[：\s]*?(\d[\d,.]+\s*元)', '每股收益'),
    (r'毛利率[：\s]*?(\d[\d,.]+\s*%)', '毛利率'),
    (r'(?:研发投入|研发费用)[：\s]*?(\d[\d,.]+\s*(?:亿元|万元|元))', '研发投入'),
    (r'总资产[：\s]*?(\d[\d,.]+\s*(?:亿元|万元|元))', '总资产'),
    (r'资产负债率[：\s]*?(\d[\d,.]+\s*%)', '资产负债率'),
]

question_templates = {
    '营业收入': ['在{doc}第{page}页中，{company}的营业收入是多少？（单位：{unit}）'],
    '净利润': ['在{doc}第{page}页中，{company}的净利润是多少？（单位：{unit}）'],
    '净资产收益率': ['在{doc}第{page}页中，{company}的加权平均净资产收益率是多少？'],
    '每股收益': ['在{doc}第{page}页中，{company}的基本每股收益是多少？'],
    '毛利率': ['在{doc}第{page}页中，{company}的毛利率是多少？'],
    '研发投入': ['在{doc}第{page}页中，{company}的研发投入是多少？（单位：{unit}）'],
    '总资产': ['在{doc}第{page}页中，{company}的总资产是多少？（单位：{unit}）'],
    '资产负债率': ['在{doc}第{page}页中，{company}的资产负债率是多少？'],
}

for c in chunks:
    text = c.get('text', '')
    source = c.get('source', '')
    page = c.get('page_num', 0)
    cid = c.get('id', '')
    
    if not text or not source:
        continue
    
    # 提取公司名（从文件名）
    fname = source.replace('.pdf', '')
    parts = fname.split('_')
    if len(parts) >= 3 and parts[0] != 'H3':
        company = parts[1]
    else:
        continue
    
    for pattern, indicator in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            value = m.strip()
            
            # 提取单位
            unit = ''
            for u in ['亿元', '万元', '元', '%']:
                if u in value:
                    unit = u
                    break
            
            # 确定doc简称
            doc_short = source.replace('_同花顺_', ' ').replace('.pdf', '')
            
            templates = question_templates.get(indicator, ['在{doc}第{page}页中，{company}的{indicator}是多少？'])
            question = templates[0].format(
                doc=doc_short, page=page, company=company,
                indicator=indicator, unit=unit
            )
            
            samples.append({
                'query': question,
                'query_type': 'fact',
                'ground_truth_answer': value,
                'ground_truth_chunk_id': cid,
                'source_file': source,
                'page_num': page,
                'company': company,
                'indicator': indicator,
            })
            break  # 一个chunk一个指标只取一次

# 去重：同一公司+同一指标只保留最具体的
seen = set()
unique = []
for s in samples:
    key = (s['source_file'], s['page_num'], s['indicator'])
    if key not in seen:
        seen.add(key)
        unique.append(s)

print(f"找到 {len(unique)} 个精准数据点")

# 按公司分布
by_company = defaultdict(int)
for s in unique:
    by_company[s['company']] += 1

print("\n公司分布:")
for c, n in sorted(by_company.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}条")

# 取前80条
random.seed(42)
random.shuffle(unique)
selected = unique[:80]

# 加一些对比型问题
companies = sorted(set(s['company'] for s in selected))
pair_count = 0
for i in range(0, len(companies)-1, 2):
    if pair_count >= 20:
        break
    c1, c2 = companies[i], companies[i+1]
    selected.append({
        'query': f'根据研报数据，{c1}和{c2}的营业收入哪个更高？',
        'query_type': 'comparison',
        'ground_truth_answer': f'需要分别找出{c1}和{c2}的营业收入数据进行比较',
        'source_file': '',
        'page_num': '',
        'company': f'{c1},{c2}',
        'indicator': '对比',
    })
    pair_count += 1

random.shuffle(selected)
total = len(selected)
fact = sum(1 for s in selected if s['query_type'] == 'fact')
comp = sum(1 for s in selected if s['query_type'] == 'comparison')

print(f"\n最终评测集: 共{total}条 (事实型{fact}, 对比型{comp})")

output_path = os.path.join(PROJECT_ROOT, "data", "eval", "eval_dataset_precise.json")
dataset = {
    'metadata': {
        'total_samples': total, 'fact_samples': fact,
        'comparison_samples': comp,
        'description': '精准评测集：问题指向文档中唯一答案'
    },
    'samples': selected
}
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"\n前5条示例:")
for s in selected[:5]:
    print(f"\n  Q: {s['query']}")
    print(f"  A: {s['ground_truth_answer']}")
    print(f"  来源: {s['source_file']} 第{s['page_num']}页 chunk={s.get('ground_truth_chunk_id','')}")
