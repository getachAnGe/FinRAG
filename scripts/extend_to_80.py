import json

with open('data/eval/eval_dataset_manual.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
samples = data['samples']

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['id']: c for c in json.load(f)}

# Add more that we know work from the scan_candidates output
more = [
    ("东方明珠", "传媒_东方明珠_同花顺_6.pdf", "41", "营业收入", "74.89亿元", "chunk_1668", "东方明珠2025年的营业收入是多少"),
    ("洋河股份", "白酒_洋河股份_同花顺_2.pdf", "2", "净资产收益率", "5.09%", "chunk_52696", "洋河股份的加权平均净资产收益率是多少"),
    ("天威视讯", "传媒_天威视讯_同花顺_4.pdf", "175", "营业收入", "1,291,703,098.00元", "chunk_17317", "天威视讯2025年的营业收入是多少元"),
    ("伊利股份", "消费_伊利股份_同花顺_4.pdf", "37", "营业收入", "1,159.31亿元", "chunk_35158", "伊利股份2025年的营业收入是多少"),
    ("泸州老窖", "白酒_泸州老窖_同花顺_4.pdf", "10", "营业收入", "257.31亿元", "chunk_51014", "泸州老窖2025年的营业收入是多少"),
    ("泸州老窖", "白酒_泸州老窖_同花顺_4.pdf", "10", "净利润", "108.31亿元", "chunk_51015", "泸州老窖2025年归属于上市公司股东的净利润是多少"),
    ("格力电器", "消费_格力电器_同花顺_2.pdf", "2", "营业收入", "1,711.18亿元", "chunk_35747", "格力电器2025年的营业收入是多少"),
    ("格力电器", "消费_格力电器_同花顺_2.pdf", "2", "净利润", "290.03亿元", "chunk_35749", "格力电器2025年的净利润是多少"),
    ("格力电器", "消费_格力电器_同花顺_2.pdf", "2", "净资产收益率", "20.30%", "chunk_35750", "格力电器的加权平均净资产收益率是多少"),
    ("电广传媒", "传媒_电广传媒_同花顺_4.pdf", "71", "资产负债率", "32.75%", "chunk_19266", "电广传媒的资产负债率是多少"),
    ("华策影视", "传媒_华策影视_同花顺_4.pdf", "2", "净资产收益率", "1.11%", "chunk_10633", "华策影视的加权平均净资产收益率是多少"),
    ("今世缘", "白酒_今世缘_同花顺_2.pdf", "6", "营业收入", "101.82亿元", "chunk_46408", "今世缘2025年的营业收入是多少"),
    ("今世缘", "白酒_今世缘_同花顺_2.pdf", "6", "净利润", "25.95亿元", "chunk_46408", "今世缘2025年的净利润是多少"),
    ("皖新传媒", "传媒_皖新传媒_同花顺_7.pdf", "12", "营业收入", "80.02亿元", "chunk_22556", "皖新传媒2025年的营业收入是多少"),
    ("皖新传媒", "传媒_皖新传媒_同花顺_7.pdf", "12", "净利润", "8.01亿元", "chunk_22557", "皖新传媒2025年的净利润是多少"),
    ("皖新传媒", "传媒_皖新传媒_同花顺_7.pdf", "12", "总资产", "192.01亿元", "chunk_22558", "皖新传媒2025年的总资产是多少"),
]

added = 0
for comp, src, page, indicator, value, cid, q_text in more:
    if added >= 15: break
    c = chunks.get(cid)
    if not c: continue
    
    text = c['text']
    val_clean = value.replace(',', '')
    found = val_clean in text.replace(',', '')
    source_ok = src in c['source']
    page_ok = str(c['page_num']) == str(page)
    
    if found and source_ok and page_ok:
        # Check duplicate
        is_dup = False
        for s in samples:
            if s['company'] == comp and s['indicator'] == indicator and s['ground_truth_answer'] == value:
                is_dup = True
                break
        if not is_dup:
            src_short = src.replace('.pdf', '')
            query = f'在{src_short}第{page}页中，{q_text}？'
            samples.append({
                "query": query, "query_type": "fact", "ground_truth_answer": value,
                "ground_truth_chunk_id": cid, "source_file": src,
                "page_num": page, "company": comp, "indicator": indicator
            })
            added += 1
    else:
        print(f'SKIP: {comp} {indicator}={value} (found={found}, src={source_ok}, page={page_ok})')

print(f'新增: {added}条')
print(f'总样本: {len(samples)}条')

# Verify all
all_ok = True
for s in samples:
    c = chunks.get(s['ground_truth_chunk_id'])
    text = c['text']
    ans = s['ground_truth_answer']
    ans_clean = ans.replace(',', '')
    found = ans_clean in text.replace(',', '')
    source_ok = s['source_file'] in c['source']
    page_ok = str(c['page_num']) == str(s['page_num'])
    if not (found and source_ok and page_ok):
        print(f'FAIL: [{s["company"]}] {s["indicator"]}={ans}')
        all_ok = False

from collections import defaultdict
company_counts = defaultdict(int)
for s in samples:
    company_counts[s['company']] += 1

print(f'全部验证通过: {all_ok}')
for comp, cnt in sorted(company_counts.items()):
    print(f'  {comp}: {cnt}条')

result = {
    'metadata': {
        'total_samples': len(samples),
        'fact_samples': len(samples),
        'description': f'手动验证评测集，{len(samples)}条，{len(company_counts)}家公司'
    },
    'samples': samples
}
with open('data/eval/eval_dataset_manual.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'已保存 {len(samples)}条')
