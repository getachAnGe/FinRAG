import json

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

chunk_map = {c['id']: c for c in chunks}

# 查看关键chunk的完整文本
targets = [
    'chunk_26916',  # 北方华创 第11页 营收393.53亿元
    'chunk_26917',  # 北方华创 第11页 净利润55.22亿元
    'chunk_27844',  # 北方华创 第104页 营收3,935,311.24万元
    'chunk_26376',  # 北京君正 第3页 营收155,976.69万元 净利润31,897.93万元
    'chunk_35155',  # 伊利股份 第35页 营收1,215亿元
    'chunk_34905',  # 伊利股份 第9页 营收327.69亿元
    'chunk_35004',  # 伊利股份 第15页 营收327.69亿元
    'chunk_34902',  # 伊利股份 第8页 营收1,159.31亿元
    'chunk_33400',  # 今世缘 第6页 营收101.82亿元 净利润25.95亿元
    'chunk_26332',  # 亿纬锂能 第1页 营收206.80亿元
    'chunk_26333',  # 亿纬锂能 第1页 净利润14.46亿元
]

for tid in targets:
    c = chunk_map.get(tid)
    if c:
        print(f'\n{"="*70}')
        print(f'chunk: {tid}')
        print(f'文件: {c["source"]}')
        print(f'页码: {c["page_num"]}')
        print(f'{"="*70}')
        print(c['text'][:600])
