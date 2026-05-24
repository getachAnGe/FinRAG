import json, re
from collections import defaultdict

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Search chunk by source+page, find one with value in text
def find_cid(source, page, value):
    val_clean = value.replace(',', '')
    for c in chunks:
        if source not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        text = c['text']
        if val_clean in text.replace(',', '') or value in text:
            return c['id']
    # Try fallback: just match company name in source
    parts = source.replace('.pdf','').split('_')
    company = parts[1]
    for c in chunks:
        if company not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        text = c['text']
        if val_clean in text.replace(',', ''):
            return c['id']
    return None

samples = []

def add(company, source_file, page, indicator, value, question_text=None):
    cid = find_cid(source_file, page, value)
    if not cid:
        print(f'  ❌ 找不到chunk: [{company}] {source_file} 第{page}页 {indicator}={value}')
        return False
    
    src_short = source_file.replace('.pdf', '')
    if question_text:
        query = f'在{src_short}第{page}页中，{question_text}？'
    else:
        query = f'在{src_short}第{page}页中，{company}的{indicator}是多少？'
    
    samples.append({
        "query": query, "query_type": "fact", "ground_truth_answer": value,
        "ground_truth_chunk_id": cid, "source_file": source_file,
        "page_num": page, "company": company, "indicator": indicator
    })
    return True

# All candidates to try
candidates = [
    # (company, source, page, indicator, value, question)
    ('北方华创', '半导体_北方华创_同花顺_5.pdf', 11, '营业收入', '393.53亿元', '北方华创2025年的营业收入是多少'),
    ('北方华创', '半导体_北方华创_同花顺_5.pdf', 11, '净利润', '55.22亿元', '北方华创2025年归属于上市公司股东的净利润是多少'),
    ('北方华创', '半导体_北方华创_同花顺_5.pdf', 11, '研发投入', '54.35亿元', '北方华创2025年计入当期损益的研发费用是多少'),
    ('北方华创', '半导体_北方华创_同花顺_1.pdf', 2, '营业收入', '103.23亿元', None),
    ('北方华创', '半导体_北方华创_同花顺_1.pdf', 2, '净利润', '16.35亿元', None),
    ('北方华创', '半导体_北方华创_同花顺_1.pdf', 1, '净资产收益率', '4.25%', None),
    ('泸州老窖', '白酒_泸州老窖_同花顺_2.pdf', 2, '营业收入', '257.31亿元', '泸州老窖2025年的营业收入是多少'),
    ('泸州老窖', '白酒_泸州老窖_同花顺_2.pdf', 2, '净利润', '108.31亿元', '泸州老窖2025年归属于上市公司股东的净利润是多少'),
    ('泸州老窖', '白酒_泸州老窖_同花顺_4.pdf', 28, '营业收入', '257.31亿元', '泸州老窖2025年的营业收入是多少'),
    ('泸州老窖', '白酒_泸州老窖_同花顺_4.pdf', 28, '净利润', '108.31亿元', '泸州老窖2025年归属于上市公司股东的净利润是多少'),
    ('泸州老窖', '白酒_泸州老窖_同花顺_1.pdf', 2, '净资产收益率', '7.32%', None),
    ('泸州老窖', '白酒_泸州老窖_同花顺_4.pdf', 70, '资产负债率', '23.00%', None),
    ('古井贡酒', '白酒_古井贡酒_同花顺_2.pdf', 2, '净资产收益率', '14.28%', None),
    ('古井贡酒', '白酒_古井贡酒_同花顺_1.pdf', 2, '净资产收益率', '6.30%', None),
    ('古井贡酒', '白酒_古井贡酒_同花顺_4.pdf', 13, '营业收入', '188.32亿元', '古井贡酒2025年的营业收入是多少'),
    ('古井贡酒', '白酒_古井贡酒_同花顺_4.pdf', 13, '净利润', '35.49亿元', '古井贡酒2025年的净利润是多少'),
    ('五粮液', '白酒_五粮液_同花顺_3.pdf', 1, '净资产收益率', '3.26%', None),
    ('五粮液', '白酒_五粮液_同花顺_6.pdf', 1, '净资产收益率', '3.41%', None),
    ('五粮液', '白酒_五粮液_同花顺_4.pdf', 1, '净资产收益率', '6.50%', None),
    ('五粮液', '白酒_五粮液_同花顺_5.pdf', 1, '净资产收益率', '1.31%', None),
    ('五粮液', '白酒_五粮液_同花顺_7.pdf', 3, '净资产收益率', '6.89%', None),
    ('伊利股份', '消费_伊利股份_同花顺_4.pdf', 35, '营业收入', '1,215亿元', '伊利股份的营业收入是多少'),
    ('伊利股份', '消费_伊利股份_同花顺_4.pdf', 14, '营业收入', '1,159.31亿元', None),
    ('伊利股份', '消费_伊利股份_同花顺_4.pdf', 14, '净利润', '115.14亿元', None),
    ('伊利股份', '消费_伊利股份_同花顺_4.pdf', 15, '营业收入', '327.69亿元', None),
    ('伊利股份', '消费_伊利股份_同花顺_4.pdf', 17, '营业收入', '98.22亿元', None),
    ('格力电器', '消费_格力电器_同花顺_2.pdf', 2, '营业收入', '1,711.18亿元', None),
    ('格力电器', '消费_格力电器_同花顺_2.pdf', 2, '净利润', '290.03亿元', None),
    ('格力电器', '消费_格力电器_同花顺_2.pdf', 2, '净资产收益率', '20.30%', None),
    ('格力电器', '消费_格力电器_同花顺_1.pdf', 2, '净资产收益率', '4.07%', None),
    ('格力电器', '消费_格力电器_同花顺_6.pdf', 10, '营业收入', '1,711.18亿元', None),
    ('紫光国微', '半导体_紫光国微_同花顺_4.pdf', 1, '营业收入', '61.46亿元', None),
    ('紫光国微', '半导体_紫光国微_同花顺_4.pdf', 2, '净利润', '3.34亿元', None),
    ('紫光国微', '半导体_紫光国微_同花顺_7.pdf', 68, '资产负债率', '27.40%', None),
    ('紫光国微', '半导体_紫光国微_同花顺_5.pdf', 2, '净资产收益率', '11.10%', None),
    ('紫光国微', '半导体_紫光国微_同花顺_1.pdf', 2, '净资产收益率', '2.40%', None),
    ('紫光国微', '半导体_紫光国微_同花顺_5.pdf', 5, '资产负债率', '27.40%', None),
    ('欧派家居', '消费_欧派家居_同花顺_7.pdf', 16, '营业收入', '172.32亿元', None),
    ('欧派家居', '消费_欧派家居_同花顺_7.pdf', 16, '毛利率', '36.24%', None),
    ('欧派家居', '消费_欧派家居_同花顺_7.pdf', 17, '营业收入', '127.21亿元', None),
    ('欧派家居', '消费_欧派家居_同花顺_7.pdf', 19, '营业收入', '26.20亿元', None),
    ('亿纬锂能', '半导体_亿纬锂能_同花顺_7.pdf', 1, '营业收入', '206.80亿元', None),
    ('亿纬锂能', '半导体_亿纬锂能_同花顺_7.pdf', 1, '净利润', '14.46亿元', None),
    ('亿纬锂能', '半导体_亿纬锂能_同花顺_4.pdf', 1, '净资产收益率', '3.35%', None),
    ('海天味业', '消费_海天味业_同花顺_4.pdf', 2, '营业收入', '90.29亿元', None),
    ('海天味业', '消费_海天味业_同花顺_4.pdf', 2, '净利润', '24.44亿元', None),
    ('海天味业', '消费_海天味业_同花顺_6.pdf', 6, '净利润', '70.38亿元', None),
    ('双汇发展', '消费_双汇发展_同花顺_8.pdf', 1, '营业收入', '594.6亿元', None),
    ('双汇发展', '消费_双汇发展_同花顺_8.pdf', 1, '净利润', '51亿元', None),
    ('双汇发展', '消费_双汇发展_同花顺_1.pdf', 3, '净利润', '12.92亿元', None),
    ('今世缘', '白酒_今世缘_同花顺_4.pdf', 11, '营业收入', '101.82亿元', None),
    ('今世缘', '白酒_今世缘_同花顺_4.pdf', 11, '净利润', '25.95亿元', '今世缘2025年扣非净利润是多少'),
    ('今世缘', '白酒_今世缘_同花顺_1.pdf', 2, '净资产收益率', '8.03%', None),
    ('东方明珠', '传媒_东方明珠_同花顺_3.pdf', 9, '营业收入', '74.89亿元', None),
    ('东方明珠', '传媒_东方明珠_同花顺_3.pdf', 9, '净利润', '6.17亿元', None),
    ('洋河股份', '白酒_洋河股份_同花顺_2.pdf', 2, '净资产收益率', '5.09%', None),
    ('山西汾酒', '白酒_山西汾酒_同花顺_5.pdf', 3, '净资产收益率', '33.48%', None),
    ('皖新传媒', '传媒_皖新传媒_同花顺_2.pdf', 6, '营业收入', '80.02亿元', None),
    ('皖新传媒', '传媒_皖新传媒_同花顺_2.pdf', 6, '净利润', '8.01亿元', None),
    ('皖新传媒', '传媒_皖新传媒_同花顺_2.pdf', 6, '总资产', '192.01亿元', None),
    ('绝味食品', '消费_绝味食品_同花顺_6.pdf', 146, '毛利率', '25.93%', None),
    ('华策影视', '传媒_华策影视_同花顺_7.pdf', 10, '营业收入', '28.28亿元', None),
    ('华策影视', '传媒_华策影视_同花顺_7.pdf', 10, '净利润', '1.91亿元', None),
    ('中颖电子', '半导体_中颖电子_同花顺_2.pdf', 2, '净资产收益率', '1.14%', None),
    ('中颖电子', '半导体_中颖电子_同花顺_2.pdf', 5, '毛利率', '31.73%', None),
    ('景嘉微', '半导体_景嘉微_同花顺_5.pdf', 34, '研发投入', '103,951.57万元', None),
    ('美的集团', '消费_美的集团_同花顺_5.pdf', 2, '净资产收益率', '5.56%', None),
    ('中国长城', '半导体_中国长城_同花顺_2.pdf', 6, '资产负债率', '61.86%', None),
    ('北京君正', '半导体_北京君正_同花顺_1.pdf', 3, '净利润', '31,897.93万元', None),
    ('歌华有线', '传媒_歌华有线_同花顺_2.pdf', 7, '营业收入', '221,975.46万元', None),
    ('天威视讯', '传媒_天威视讯_同花顺_4.pdf', 17, '营业收入', '129,170.31万元', None),
    ('电广传媒', '传媒_电广传媒_同花顺_2.pdf', 8, '营业收入', '43.37亿元', None),
    ('电广传媒', '传媒_电广传媒_同花顺_4.pdf', 17, '营业收入', '5.47亿元', None),
    ('中南文化', '传媒_中南文化_同花顺_5.pdf', 13, '每股收益', '0.03元', None),
]

success = 0
for cand in candidates:
    if add(*cand):
        success += 1

company_counts = defaultdict(int)
for s in samples:
    company_counts[s['company']] += 1

print(f'\n成功: {success}/{len(candidates)}条, 覆盖{len(company_counts)}家公司')
for comp, cnt in sorted(company_counts.items()):
    print(f'  {comp}: {cnt}条')

# Final verification
chunk_map = {c['id']: c for c in chunks}
all_ok = True
for s in samples:
    c = chunk_map.get(s['ground_truth_chunk_id'])
    text = c['text']
    ans = s['ground_truth_answer']
    ans_clean = ans.replace(',', '')
    found = ans_clean in text.replace(',', '')
    page_ok = str(c['page_num']) == str(s['page_num'])
    source_ok = s['source_file'] in c['source']
    if not (found and page_ok and source_ok):
        print(f'❌ [{s["company"]}] {s["indicator"]}={ans} (found={found})')
        all_ok = False

print(f'\n全部验证: {all_ok}')

# Save
result = {
    'metadata': {
        'total_samples': len(samples),
        'fact_samples': len(samples),
        'description': f'自动搜索验证评测集，{len(samples)}条，{len(company_counts)}家公司'
    },
    'samples': samples
}
with open('data/eval/eval_dataset_manual.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'已保存 {len(samples)}条')
