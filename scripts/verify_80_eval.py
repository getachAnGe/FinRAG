import json, re

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunk_list = json.load(f)
chunk_map = {c['id']: c for c in chunk_list}

with open('data/eval/eval_dataset_three_type.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)

samples = dataset['samples']

print(f'共 {len(samples)} 条，逐条验证：\n')

facts_ok = facts_fail = comps_ok = comps_fail = summary_ok = summary_fail = 0

for i, s in enumerate(samples, 1):
    qtype = s['query_type']
    comp = s['company']
    ind = s['indicator']
    ans = s['ground_truth_answer']
    cid_str = s['ground_truth_chunk_id']
    src = s['source_file']
    page = s['page_num']
    
    cid_list = [x.strip() for x in cid_str.split(',')]
    
    all_found = True
    for cid in cid_list:
        c = chunk_map.get(cid)
        if not c:
            print(f'  ❌ 第{i}条 [{qtype}] [{comp}]  chunk不存在: {cid}')
            all_found = False
            continue
        
        text = c['text']
        ans_clean = ans.replace(',', '').replace('，', '')
        found = ans_clean in text.replace(',', '')
        
        if not found:
            # For comparison and summary, try to find partial match
            parts = re.findall(r'[\d,]+(?:\.\d+)?', ans)
            found_parts = any(p in text for p in parts if len(p) > 3)
            if not found_parts:
                # Check keywords
                kws = [kw for kw in ans.split('，') if len(kw) > 5]
                found_kw = any(kw in text for kw in kws)
                if not found_kw:
                    print(f'  ❌ 第{i}条 [{qtype}] [{comp}] {ind}')
                    print(f'     答案未在chunk中找到: {ans[:60]}')
                    print(f'     chunk: {c["source"]} 第{c["page_num"]}页')
                    print(f'     文本前150字: {text[:150]}')
                    all_found = False
    
    if all_found:
        if qtype == 'fact': facts_ok += 1
        elif qtype == 'comparison': comps_ok += 1
        elif qtype == 'summary': summary_ok += 1
    else:
        if qtype == 'fact': facts_fail += 1
        elif qtype == 'comparison': comps_fail += 1
        elif qtype == 'summary': summary_fail += 1

print(f'\n{"="*50}')
print('验证结果汇总')
print(f'{"="*50}')
print(f'  事实型:  {facts_ok}✅ / {facts_ok+facts_fail}  ({facts_fail}❌)')
print(f'  对比型:  {comps_ok}✅ / {comps_ok+comps_fail}  ({comps_fail}❌)')
print(f'  汇总型:  {summary_ok}✅ / {summary_ok+summary_fail}  ({summary_fail}❌)')
print(f'  {"="*30}')
print(f'  总计:    {facts_ok+comps_ok+summary_ok}✅ / {len(samples)}')
