import json

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Find correct chunk_ids for 格力电器
targets = [
    ("消费_格力电器_同花顺_2.pdf", "2", "1,711.18"),
    ("消费_格力电器_同花顺_2.pdf", "2", "290.03"),
    ("消费_格力电器_同花顺_2.pdf", "2", "20.30"),
    ("消费_格力电器_同花顺_1.pdf", "2", "4.07"),
    ("消费_格力电器_同花顺_6.pdf", "160", "27.68"),
    ("半导体_紫光国微_同花顺_7.pdf", "68", "27.40"),
    ("半导体_中国长城_同花顺_2.pdf", "6", "61.86"),
    ("传媒_皖新传媒_同花顺_2.pdf", "6", "80.02"),
    ("传媒_皖新传媒_同花顺_2.pdf", "6", "8.01"),
    ("传媒_东方明珠_同花顺_6.pdf", "11", "16万亿"),
    ("传媒_东方明珠_同花顺_3.pdf", "3", "4.08亿"),
    ("传媒_中南文化_同花顺_5.pdf", "11", "518.32"),
    ("半导体_北方华创_同花顺_5.pdf", "11", "国产化替代"),
    ("消费_欧派家居_同花顺_7.pdf", "19", "26.20"),
    ("消费_欧派家居_同花顺_7.pdf", "16", "大家居"),
    ("传媒_中南文化_同花顺_5.pdf", "11", "2,677"),
    ("传媒_东方明珠_同花顺_6.pdf", "12", "IPTV"),
    ("白酒_泸州老窖_同花顺_4.pdf", "28", "量减质升"),
    ("消费_海天味业_同花顺_4.pdf", "2", "90.29"),
    ("半导体_中国长城_同花顺_4.pdf", "12", "市场牵引"),
    ("消费_伊利股份_同花顺_4.pdf", "14", "1,159.31"),
    ("半导体_亿纬锂能_同花顺_7.pdf", "1", "206.80"),
]

for src, page, val in targets:
    val_clean = val.replace(',', '')
    found = False
    for c in chunks:
        if src not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        if val_clean in c['text'].replace(',', ''):
            print(f'{src}|{page}|{val} -> {c["id"]}')
            found = True
            break
    if not found:
        print(f'{src}|{page}|{val} -> NOT FOUND')
