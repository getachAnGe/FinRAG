import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

CLEAR_PATTERNS = [
    # 营业收入模式
    (r'(?:2025年|报告期内|本期|公司)[^。]{0,30}?营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入'),
    (r'营业总收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入'),
    (r'实现营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入'),
    (r'营业收入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '营业收入'),
    (r'营业收入合计[=为：]{1,2}\s*([\d,]+(?:\.\d+)?)\s*亿', '营业收入'),
    # 净利润模式
    (r'(?:2025年|报告期内|本期|公司)[^。]{0,30}?归属于上市公司股东的净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润'),
    (r'(?:2025年|报告期内|本期|公司)[^。]{0,30}?净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润'),
    (r'实现归属于上市公司股东的净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润'),
    (r'归属于上市公司股东的净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润'),
    (r'归母净利润[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '净利润'),
    # ROE模式
    (r'加权平均净资产收益率[：\s]*?([\d,]+(?:\.\d+)?)%', '净资产收益率'),
    (r'加权平均净资产收益率[：\s]*?([\d,]+(?:\.\d+)?)', '净资产收益率'),
    # 每股收益
    (r'(?:基本每股收益|每股收益)[：\s]*?([\d,]+(?:\.\d+)?)\s*元', '每股收益'),
    # 毛利率
    (r'毛利率[：\s]*?([\d,]+(?:\.\d+)?)%', '毛利率'),
    # 总资产
    (r'总资产[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '总资产'),
    (r'资产总额[：\s]*?([\d,]+(?:\.\d+)?)\s*亿元', '总资产'),
    # 研发投入
    (r'研发投入[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '研发投入'),
    (r'研发费用[：\s]*?([\d,]+(?:\.\d+)?)\s*亿', '研发投入'),
    # 资产负债率
    (r'资产负债率[：\s]*?([\d,]+(?:\.\d+)?)%', '资产负债率'),
]

all_candidates = []
searched_companies = set()

for c in chunks:
    src = c.get('source', '')
    if src.startswith('H3_') or not src:
        continue
    parts = src.replace('.pdf','').split('_')
    if len(parts) < 2:
        continue
    company = parts[1]
    
    text = c.get('text', '')[:800]
    
    for pat, indicator in CLEAR_PATTERNS:
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            # Determine unit
            unit = ''
            if indicator == '营业收入' or indicator == '净利润' or indicator == '研发投入' or indicator == '总资产':
                if '亿' in text[m.start():m.end()+5]:
                    unit = '亿元'
                elif '万' in text[m.start():m.end()+5]:
                    unit = '万元'
                elif '元' in text[m.start():m.end()+5]:
                    unit = '元'
            elif indicator == '净资产收益率':
                unit = '%'
            elif indicator == '毛利率':
                unit = '%'
            elif indicator == '资产负债率':
                unit = '%'
            elif indicator == '每股收益':
                unit = '元'
            
            full_val = val + unit if unit else val
            
            # Avoid duplicates from the same chunk
            key = (c['id'], indicator)
            
            all_candidates.append({
                'chunk_id': c['id'],
                'source': src,
                'page': c['page_num'],
                'company': company,
                'indicator': indicator,
                'value': full_val,
                'text_preview': text[:200]
            })

# Deduplicate
seen = set()
unique_candidates = []
for cand in all_candidates:
    key = (cand['chunk_id'], cand['indicator'])
    if key not in seen:
        seen.add(key)
        unique_candidates.append(cand)

print(f"候选总数: {len(unique_candidates)}\n")

# 按公司分组显示
from collections import defaultdict
by_company = defaultdict(list)
for cand in unique_candidates:
    by_company[cand['company']].append(cand)

for comp, items in sorted(by_company.items()):
    print(f"\n=== {comp} ({len(items)}条候选) ===")
    for item in items:
        print(f"  [{item['source']}] 第{item['page']}页: {item['indicator']}={item['value']}")
