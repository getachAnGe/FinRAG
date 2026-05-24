import json

samples = [
    # ============ 北方华创 ============
    {
        "query": "在半导体_北方华创_同花顺_5第11页中，北方华创2025年的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "393.53亿元",
        "ground_truth_chunk_id": "chunk_26916",
        "source_file": "半导体_北方华创_同花顺_5.pdf",
        "page_num": 11,
        "company": "北方华创",
        "indicator": "营业收入"
    },
    {
        "query": "在半导体_北方华创_同花顺_5第11页中，北方华创2025年归属于上市公司股东的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "55.22亿元",
        "ground_truth_chunk_id": "chunk_26917",
        "source_file": "半导体_北方华创_同花顺_5.pdf",
        "page_num": 11,
        "company": "北方华创",
        "indicator": "净利润"
    },
    # ============ 泸州老窖 ============
    {
        "query": "在白酒_泸州老窖_同花顺_2第2页中，泸州老窖2025年的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "257.31亿元",
        "ground_truth_chunk_id": "chunk_50902",
        "source_file": "白酒_泸州老窖_同花顺_2.pdf",
        "page_num": 2,
        "company": "泸州老窖",
        "indicator": "营业收入"
    },
    {
        "query": "在白酒_泸州老窖_同花顺_2第2页中，泸州老窖2025年归属于上市公司股东的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "108.31亿元",
        "ground_truth_chunk_id": "chunk_50903",
        "source_file": "白酒_泸州老窖_同花顺_2.pdf",
        "page_num": 2,
        "company": "泸州老窖",
        "indicator": "净利润"
    },
    # ============ 伊利股份 ============
    {
        "query": "在消费_伊利股份_同花顺_4第35页中，伊利股份的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "1,215亿元",
        "ground_truth_chunk_id": "chunk_35155",
        "source_file": "消费_伊利股份_同花顺_4.pdf",
        "page_num": 35,
        "company": "伊利股份",
        "indicator": "营业收入"
    },
    # ============ 海天味业 ============
    {
        "query": "在消费_海天味业_同花顺_4第2页中，海天味业2026年一季度的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "90.29亿元",
        "ground_truth_chunk_id": "chunk_43214",
        "source_file": "消费_海天味业_同花顺_4.pdf",
        "page_num": 2,
        "company": "海天味业",
        "indicator": "营业收入"
    },
    {
        "query": "在消费_海天味业_同花顺_4第2页中，海天味业2026年一季度的归母净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "24.44亿元",
        "ground_truth_chunk_id": "chunk_43214",
        "source_file": "消费_海天味业_同花顺_4.pdf",
        "page_num": 2,
        "company": "海天味业",
        "indicator": "净利润"
    },
    # ============ 古井贡酒 ============
    {
        "query": "在白酒_古井贡酒_同花顺_2第2页中，古井贡酒的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "14.28%",
        "ground_truth_chunk_id": "chunk_47925",
        "source_file": "白酒_古井贡酒_同花顺_2.pdf",
        "page_num": 2,
        "company": "古井贡酒",
        "indicator": "净资产收益率"
    },
    {
        "query": "在白酒_古井贡酒_同花顺_1第2页中，古井贡酒的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "6.30%",
        "ground_truth_chunk_id": "chunk_47728",
        "source_file": "白酒_古井贡酒_同花顺_1.pdf",
        "page_num": 2,
        "company": "古井贡酒",
        "indicator": "净资产收益率"
    },
    # ============ 今世缘 ============
    {
        "query": "在白酒_今世缘_同花顺_4第11页中，今世缘2025年归属于上市公司股东的扣除非经常性损益的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "25.95亿元",
        "ground_truth_chunk_id": "chunk_46486",
        "source_file": "白酒_今世缘_同花顺_4.pdf",
        "page_num": 11,
        "company": "今世缘",
        "indicator": "净利润"
    },
    # ============ 五粮液 ============
    {
        "query": "在白酒_五粮液_同花顺_3第1页中，五粮液的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "3.26%",
        "ground_truth_chunk_id": "chunk_45821",
        "source_file": "白酒_五粮液_同花顺_3.pdf",
        "page_num": 1,
        "company": "五粮液",
        "indicator": "净资产收益率"
    },
    {
        "query": "在白酒_五粮液_同花顺_6第1页中，五粮液的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "3.41%",
        "ground_truth_chunk_id": "chunk_46200",
        "source_file": "白酒_五粮液_同花顺_6.pdf",
        "page_num": 1,
        "company": "五粮液",
        "indicator": "净资产收益率"
    },
    {
        "query": "在白酒_五粮液_同花顺_4第1页中，五粮液归属于上市公司股东的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "8,062,764,940.78元",
        "ground_truth_chunk_id": "chunk_45928",
        "source_file": "白酒_五粮液_同花顺_4.pdf",
        "page_num": 1,
        "company": "五粮液",
        "indicator": "净利润"
    },
    # ============ 洋河股份 ============
    {
        "query": "在白酒_洋河股份_同花顺_2第2页中，洋河股份的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "5.09%",
        "ground_truth_chunk_id": "chunk_52696",
        "source_file": "白酒_洋河股份_同花顺_2.pdf",
        "page_num": 2,
        "company": "洋河股份",
        "indicator": "净资产收益率"
    },
    # ============ 山西汾酒 ============
    {
        "query": "在白酒_山西汾酒_同花顺_5第3页中，山西汾酒的加权平均净资产收益率是多少？",
        "query_type": "fact",
        "ground_truth_answer": "33.48%",
        "ground_truth_chunk_id": "chunk_49678",
        "source_file": "白酒_山西汾酒_同花顺_5.pdf",
        "page_num": 3,
        "company": "山西汾酒",
        "indicator": "净资产收益率"
    },
    # ============ 泸州老窖_同花顺_4 ============
    {
        "query": "在白酒_泸州老窖_同花顺_4第28页中，泸州老窖2025年的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "257.31亿元",
        "ground_truth_chunk_id": "chunk_51165",
        "source_file": "白酒_泸州老窖_同花顺_4.pdf",
        "page_num": 28,
        "company": "泸州老窖",
        "indicator": "营业收入"
    },
    {
        "query": "在白酒_泸州老窖_同花顺_4第28页中，泸州老窖2025年归属于上市公司股东的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "108.31亿元",
        "ground_truth_chunk_id": "chunk_51165",
        "source_file": "白酒_泸州老窖_同花顺_4.pdf",
        "page_num": 28,
        "company": "泸州老窖",
        "indicator": "净利润"
    },
    # ============ 欧派家居 ============
    {
        "query": "在消费_欧派家居_同花顺_7第19页中，欧派家居大宗渠道2025年的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "26.20亿元",
        "ground_truth_chunk_id": "chunk_38930",
        "source_file": "消费_欧派家居_同花顺_7.pdf",
        "page_num": 19,
        "company": "欧派家居",
        "indicator": "营业收入"
    },
    # ============ 北京君正 ============
    {
        "query": "在半导体_北京君正_同花顺_1第3页中，北京君正的净利润是多少？",
        "query_type": "fact",
        "ground_truth_answer": "31,897.93万元",
        "ground_truth_chunk_id": "chunk_26377",
        "source_file": "半导体_北京君正_同花顺_1.pdf",
        "page_num": 3,
        "company": "北京君正",
        "indicator": "净利润"
    },
    # ============ 亿纬锂能 ============
    {
        "query": "在半导体_亿纬锂能_同花顺_7第1页中，亿纬锂能的营业收入是多少？",
        "query_type": "fact",
        "ground_truth_answer": "206.80亿元",
        "ground_truth_chunk_id": "chunk_26332",
        "source_file": "半导体_亿纬锂能_同花顺_7.pdf",
        "page_num": 1,
        "company": "亿纬锂能",
        "indicator": "营业收入"
    },
]

# ===== 验证 =====
with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunk_map = {c['id']: c for c in chunks}

print(f'手动构建评测集 ({len(samples)}条)\n')

verified = 0
for s in samples:
    cid = s['ground_truth_chunk_id']
    c = chunk_map.get(cid)
    text = c['text']
    answer = s['ground_truth_answer']
    
    # 宽松匹配：去掉逗号和单位后对比数字
    import re
    ans_nums = re.findall(r'[\d,.]+', answer)
    found_any = False
    for an in ans_nums:
        an_clean = an.replace(',', '')
        if an_clean in text.replace(',', ''):
            found_any = True
            break
    
    page_ok = str(c['page_num']) == str(s['page_num'])
    source_ok = s['source_file'] in c['source']
    
    if found_any and page_ok and source_ok:
        status = '✅'
        verified += 1
    else:
        status = f'❌ (found={found_any}, page={page_ok}, source={source_ok})'
    
    print(f'{status} [{s["company"]}] {s["indicator"]}: {answer}')

print(f'\n通过: {verified}/{len(samples)}')

# 保存
result = {
    'metadata': {
        'total_samples': len(samples),
        'fact_samples': len(samples),
        'description': '手动逐条验证的评测集'
    },
    'samples': samples
}
with open('data/eval/eval_dataset_manual.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'已保存到 data/eval/eval_dataset_manual.json')
