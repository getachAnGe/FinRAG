import json
from collections import Counter

with open('data/eval/eval_dataset_three_type.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data['samples']:
    if s.get('ground_truth_chunk_id') == 'chunk_38214':
        s['page_num'] = 160
        s['query'] = s['query'].replace('第159页', '第160页')

data['samples'].append({
    'query': '根据传媒_东方明珠_同花顺_6.pdf第10页的内容，东方明珠拥有哪些竞争优势？',
    'query_type': 'summary',
    'ground_truth_answer': '拥有国内领先的全渠道视频集成与分发平台，运营上海地区广电5G网络服务，拥有上海地区独具特色的文化消费资源',
    'ground_truth_chunk_id': 'chunk_1309',
    'source_file': '传媒_东方明珠_同花顺_6.pdf',
    'page_num': 10,
    'company': '东方明珠',
    'indicator': '竞争优势'
})

data['samples'].append({
    'query': '根据消费_今世缘_同花顺_2第8页的内容，今世缘所处白酒行业的发展情况如何？',
    'query_type': 'summary',
    'ground_truth_answer': '白酒行业整体步入量减质升的新一轮调整周期',
    'ground_truth_chunk_id': 'chunk_33398',
    'source_file': '消费_今世缘_同花顺_2.pdf',
    'page_num': 8,
    'company': '今世缘',
    'indicator': '行业趋势'
})

data['metadata']['total_samples'] = len(data['samples'])
data['metadata']['summary_samples'] = 20

with open('data/eval/eval_dataset_three_type.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

tc = Counter(s['query_type'] for s in data['samples'])
print(f'total: {len(data["samples"])}')
print(f'  fact: {tc["fact"]}')
print(f'  comparison: {tc["comparison"]}')
print(f'  summary: {tc["summary"]}')
