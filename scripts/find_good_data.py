import json
import re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# 只看含中文公司名的文件
target_files = sorted(set(c['source'] for c in chunks if not c['source'].startswith('H3_')))

# 挑不同行业的公司
companies = ['格力电器', '伊利股份', '北方华创', '紫光国微', '泸州老窖', 
             '五粮液', '古井贡酒', '欧派家居', '亿纬锂能', '北京君正',
             '洋河股份', '今世缘', '双汇发展', '海天味业', '景嘉微']
pages_to_check = {}

for tf in target_files:
    for comp in companies:
        if comp in tf:
            file_chunks = [c for c in chunks if c['source'] == tf]
            for c in file_chunks:
                text = c['text']
                page = c['page_num']
                hid = c['id']
                
                # 提取清晰的财务指标 - 格式如 "营业收入XX亿元" 或 "净利润XX亿元"
                patterns = [
                    (r'(?:营业收入|营业总收入)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '营业收入'),
                    (r'(?:归属于上市公司股东的净利润|归属于母公司所有者的净利润|净利润)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '净利润'),
                    (r'(?:加权平均净资产收益率|净资产收益率)[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '净资产收益率'),
                    (r'(?:基本每股收益|每股收益)[：:\s]*?([\d,]+(?:\.\d+)?)\s*元', '每股收益'),
                    (r'毛利率[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '毛利率'),
                    (r'(?:研发投入|研发费用)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '研发投入'),
                    (r'总资产[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '总资产'),
                    (r'资产负债率[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '资产负债率'),
                ]
                
                found = []
                for pat, name in patterns:
                    matches = re.findall(pat, text[:500])
                    for m in matches:
                        if isinstance(m, tuple):
                            v = m[0] + m[1]
                        else:
                            v = m
                        found.append(f'{name}={v}')
                
                if found:
                    key = (comp, tf.replace('.pdf',''))
                    if key not in pages_to_check:
                        pages_to_check[key] = []
                    pages_to_check[key].append({
                        'page': page,
                        'chunk_id': hid,
                        'indicators': found,
                        'text_preview': text[:300]
                    })

# 输出结果
for (comp, source), items in sorted(pages_to_check.items()):
    print(f'\n{"="*60}')
    print(f'{source}')
    print(f'{comp}')
    print(f'{"="*60}')
    for item in items:
        print(f'  第{item["page"]}页 (chunk_{item["chunk_id"]})')
        for ind in item['indicators']:
            print(f'    {ind}')
