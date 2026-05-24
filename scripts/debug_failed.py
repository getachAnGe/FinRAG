import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

def find_chunks(source, page, value=None):
    matches = []
    for c in chunks:
        if source in c['source'] and str(c['page_num']) == str(page):
            if value:
                val_clean = value.replace(',', '').replace('亿元','').replace('万元','').replace('%','').replace('元','')
                if val_clean in c['text'].replace(',', ''):
                    matches.append((c['id'], c['source'], c['page_num'], c['text'][:200]))
            else:
                matches.append((c['id'], c['source'], c['page_num'], c['text'][:200]))
    return matches

# 检查失败的
fails = [
    ('紫光国微', '半导体_紫光国微_同花顺_4.pdf', 1, '61.46亿元', '营业收入'),
    ('紫光国微', '半导体_紫光国微_同花顺_4.pdf', 2, '3.34亿元', '净利润'),
    ('亿纬锂能', '半导体_亿纬锂能_同花顺_7.pdf', 1, '206.80亿元', '营业收入'),
    ('双汇发展', '消费_双汇发展_同花顺_8.pdf', 1, '594.6亿元', '营业收入'),
    ('山西汾酒', '白酒_山西汾酒_同花顺_5.pdf', 3, '33.48%', '净资产收益率'),
    ('皖新传媒', '传媒_皖新传媒_同花顺_2.pdf', 6, '80.02亿元', '营业收入'),
]

for comp, src, page, val, ind in fails:
    print(f'\n=== {comp} | {src} 第{page}页 | {ind}={val} ===')
    matches = find_chunks(src, page, val)
    if matches:
        for cid, cs, cp, ct in matches:
            print(f'  ✅ {cid} ({cs} 第{cp}页)')
    else:
        print(f'  ❌ 未找到匹配，显示该页所有chunk:')
        all_on_page = find_chunks(src, page)
        for cid, cs, cp, ct in all_on_page[:3]:
            print(f'  chunk={cid}: {ct[:150]}')
        if not all_on_page:
            # 搜索公司+指标
            for c in chunks:
                if comp.replace('股份','') in c['source'] and str(c['page_num']) == str(page):
                    print(f'  替代文件: {c["source"]} 第{c["page_num"]}页: {c["text"][:150]}')
                    break
