import json, sys

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunk_map = {c['id']: c for c in chunks}

target_chunks = {
    # 北方华创相关
    'chunk_26916': '半导体_北方华创_同花顺_5',
    'chunk_27844': '半导体_北方华创_同花顺_5',
    # 伊利股份
    'chunk_34902': '消费_伊利股份_同花顺_2',
    'chunk_34905': '消费_伊利股份_同花顺_2',
    'chunk_35155': '消费_伊利股份_同花顺_4',
    'chunk_35004': '消费_伊利股份_同花顺_4',
    # 今世缘
    'chunk_33400': '消费_今世缘_同花顺_2',
    # 亿纬锂能
    'chunk_26332': '半导体_亿纬锂能_同花顺_7',
    # 北京君正
    'chunk_26376': '半导体_北京君正_同花顺_1',
}

for cid, expected in target_chunks.items():
    c = chunk_map.get(cid)
    if not c:
        print(f'[{cid}] 不存在!')
        continue
    src = c['source'].replace('.pdf','')
    if expected not in src:
        print(f'[{cid}] 文件不匹配: {src} (期望包含: {expected})')
    else:
        print(f'[{cid}] ✅ {src} 第{c["page_num"]}页')
