import json

with open('data/eval/eval_dataset_manual.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['id']: c for c in json.load(f)}

samples = data['samples']

# Fix the 2 皖新传媒 entries
for s in samples:
    if s['company'] == '皖新传媒' and s['indicator'] in ['营业收入', '净利润']:
        c = chunks.get(s['ground_truth_chunk_id'])
        s['source_file'] = c['source']

# Add 20 more verified entries from previous dataset (same chunk_id used before, already verified)
additional = [
    ("北方华创", "半导体_北方华创_同花顺_5.pdf", "107", "营业收入", "3,935,311.24万元", "chunk_27844", "北方华创2025年合并报表营业收入是多少"),
    ("北方华创", "半导体_北方华创_同花顺_6.pdf", "2", "净利润", "552,199.30万元", "chunk_28912", "北方华创的净利润是多少"),
    ("北京君正", "半导体_北京君正_同花顺_1.pdf", "3", "营业收入", "155,976.69万元", "chunk_26376", "北京君正的营业收入是多少"),
    ("亿纬锂能", "半导体_亿纬锂能_同花顺_7.pdf", "1", "营业收入", "206.80亿元", "chunk_26332", "亿纬锂能2026年第一季度的营业收入是多少"),
    ("亿纬锂能", "半导体_亿纬锂能_同花顺_7.pdf", "1", "净利润", "14.46亿元", "chunk_26333", "亿纬锂能2026年第一季度的净利润是多少"),
    ("伊利股份", "消费_伊利股份_同花顺_2.pdf", "8", "营业收入", "704.22亿元", "chunk_34902", "伊利股份2025年上半年的营业收入是多少"),
    ("伊利股份", "消费_伊利股份_同花顺_2.pdf", "9", "营业收入", "327.69亿元", "chunk_34905", "伊利股份2025年第三季度的营业收入是多少"),
    ("格力电器", "消费_格力电器_同花顺_6.pdf", "7", "净资产收益率", "20.30%", "chunk_36270", "格力电器的加权平均净资产收益率是多少"),
    ("格力电器", "消费_格力电器_同花顺_6.pdf", "160", "毛利率", "27.68%", "chunk_36481", "格力电器2025年的毛利率是多少"),
    ("欧派家居", "消费_欧派家居_同花顺_7.pdf", "19", "营业收入", "26.20亿元", "chunk_38930", "欧派家居大宗渠道2025年的营业收入是多少"),
    ("古井贡酒", "白酒_古井贡酒_同花顺_4.pdf", "13", "营业收入", "188.32亿元", "chunk_48038", "古井贡酒2025年的营业收入是多少"),
    ("山西汾酒", "白酒_山西汾酒_同花顺_5.pdf", "3", "净资产收益率", "33.48%", "chunk_49678", "山西汾酒的加权平均净资产收益率是多少"),
    ("紫光国微", "半导体_紫光国微_同花顺_7.pdf", "68", "资产负债率", "27.40%", "chunk_31370", "紫光国微的资产负债率是多少"),
    ("紫光国微", "半导体_紫光国微_同花顺_1.pdf", "2", "净资产收益率", "2.40%", "chunk_31135", "紫光国微的加权平均净资产收益率是多少"),
    ("双汇发展", "消费_双汇发展_同花顺_8.pdf", "1", "营业收入", "594.6亿元", "chunk_36992", "双汇发展2025年的营业收入是多少"),
    ("海天味业", "消费_海天味业_同花顺_6.pdf", "6", "净利润", "70.38亿元", "chunk_43248", "海天味业2025年的归母净利润是多少"),
    ("中颖电子", "半导体_中颖电子_同花顺_2.pdf", "2", "净资产收益率", "1.14%", "chunk_24845", "中颖电子的加权平均净资产收益率是多少"),
    ("美的集团", "消费_美的集团_同花顺_5.pdf", "2", "净资产收益率", "5.56%", "chunk_45569", "美的集团的加权平均净资产收益率是多少"),
    ("中国长城", "半导体_中国长城_同花顺_2.pdf", "6", "资产负债率", "61.86%", "chunk_56733", "中国长城的资产负债率是多少"),
    ("歌华有线", "传媒_歌华有线_同花顺_2.pdf", "7", "营业收入", "221,975.46万元", "chunk_23617", "歌华有线的营业收入是多少"),
]

for comp, src, page, indicator, value, cid, q_text in additional:
    c = chunks.get(cid)
    if not c:
        print(f'chunk not found: {cid}')
        continue
    text = c['text']
    val_clean = value.replace(',', '')
    found = val_clean in text.replace(',', '')
    source_ok = src in c['source']
    page_ok = str(c['page_num']) == str(page)
    
    if found and source_ok and page_ok:
        src_short = src.replace('.pdf', '')
        query = f'在{src_short}第{page}页中，{q_text}？'
        samples.append({
            "query": query, "query_type": "fact", "ground_truth_answer": value,
            "ground_truth_chunk_id": cid, "source_file": src,
            "page_num": page, "company": comp, "indicator": indicator
        })
    else:
        print(f'FAILED to add: {comp} {indicator}={value} (found={found}, src={source_ok}, page={page_ok})')

# Final verification
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

print(f'\n总样本: {len(samples)}条, 覆盖{len(company_counts)}家公司')
print(f'全部验证通过: {all_ok}')
for comp, cnt in sorted(company_counts.items()):
    print(f'  {comp}: {cnt}条')

# Save
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
print(f'已保存 {len(samples)}条 到 data/eval/eval_dataset_manual.json')
