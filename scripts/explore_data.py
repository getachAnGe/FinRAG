import json
import re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# 只看含中文公司名的文件
target_files = sorted(set(c['source'] for c in chunks if not c['source'].startswith('H3_')))

# 挑几个常用的公司看
test_files = [f for f in target_files if '东方明珠' in f or '天威视讯' in f or '格力电器' in f or '北方华创' in f or '伊利股份' in f or '歌华有线' in f]
test_files = test_files[:15]

for tf in test_files:
    file_chunks = [c for c in chunks if c['source'] == tf]
    print(f'\n{"="*60}')
    print(f'文件: {tf}  ({len(file_chunks)} chunks)')
    print(f'{"="*60}')
    
    for c in file_chunks:
        text = c['text']
        page = c['page_num']
        hid = c['id']
        
        # 检查是否含有财务指标
        indicators = []
        if re.search(r'营业收入[：:\s]*?[\d,]+', text):
            indicators.append('营业收入')
        if re.search(r'净利润[：:\s]*?[\d,]+', text):
            indicators.append('净利润')
        if re.search(r'净资产收益率[：:\s]*?[\d,]+', text):
            indicators.append('净资产收益率')
        if re.search(r'毛利率[：:\s]*?[\d,]+', text):
            indicators.append('毛利率')
        if re.search(r'总资产[：:\s]*?[\d,]+', text):
            indicators.append('总资产')
        if re.search(r'每股收益[：:\s]*?[\d,]+', text):
            indicators.append('每股收益')
        
        if indicators:
            print(f'  第{page}页 (chunk_{hid}) - 指标: {", ".join(indicators)}')
            print(f'  预览: {text[:150]}')
            print()
