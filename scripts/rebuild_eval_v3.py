"""直接搜索方式：事实型=答案值，对比型=拆分为2个事实型分别搜，汇总型=答案值"""
import json, re
from collections import Counter

with open('data/chunks/all_chunks_table_protection.json', 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open('data/eval/eval_dataset_three_type.json', 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
old_samples = eval_data['samples']

def find_cids(source, page, search_vals):
    results = []
    for c in new_chunks:
        if source not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        text = c['text'].replace(',', '')
        for sv in search_vals:
            sv_clean = sv.replace(',', '')
            if sv_clean in text:
                results.append(c['id'])
                break
    return results

def find_by_company(company, page, search_vals):
    for c in new_chunks:
        if company not in c['source']: continue
        if str(c['page_num']) != str(page): continue
        for sv in search_vals:
            if sv.replace(',', '') in c['text'].replace(',', ''):
                return [c['id']]
    return []

new_samples = []
errors = []

for s in old_samples:
    qt = s['query_type']
    ans = s['ground_truth_answer']
    
    if qt == 'fact':
        src = s['source_file']; page = s['page_num']
        vals = re.findall(r'[\d,.]+', ans)
        cids = find_cids(src, page, vals) or find_by_company(s['company'], page, vals)
        if cids:
            ns = s.copy(); ns['ground_truth_chunk_id'] = cids[0]; new_samples.append(ns)
        else:
            errors.append(f'FACT: {s["company"]} {src} p{page}')
    
    elif qt == 'comparison':
        # Use old chunk_ids to find what source+page they refer to, then search in new
        # Or just hardcode: search each company's chunk separately
        q = s['query']
        # Split by "和" to get two parts
        parts_question = q.split('和')
        if len(parts_question) >= 2:
            all_cids = []
            for idx in range(2):
                part = parts_question[idx]
                # Extract source and page from each part
                # Format like: "在白酒_古井贡酒_同花顺_2第2页"
                m = re.search(r'(\S+?)第(\d+)页', part)
                if m:
                    src_base = m.group(1)
                    pg = m.group(2)
                    src = src_base + '.pdf'
                    # Get the number from answer for this company
                    nums = re.findall(r'[\d,.]+', ans.split('高于')[idx]) if '高于' in ans else re.findall(r'[\d,.]+', ans)
                    cids = find_cids(src, pg, nums) or find_by_company(src_base.split('_')[1], pg, nums)
                    if cids:
                        all_cids.append(cids[0])
            if len(all_cids) >= 2:
                ns = s.copy(); ns['ground_truth_chunk_id'] = ','.join(all_cids[:2]); new_samples.append(ns)
            else:
                errors.append(f'COMP: {s["company"]}')
        else:
            errors.append(f'COMP split fail: {q[:40]}')
    
    elif qt == 'summary':
        src = s['source_file']; page = s['page_num']
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = kws[:1] if kws else [ans[:8]]
        cids = find_cids(src, page, vals) or find_by_company(s['company'], page, vals)
        if cids:
            ns = s.copy(); ns['ground_truth_chunk_id'] = cids[0]; new_samples.append(ns)
        else:
            errors.append(f'SUM: {s["company"]} {src} p{page}')

tc = Counter(s['query_type'] for s in new_samples)
print(f'Reconstructed: {len(new_samples)}/{len(old_samples)}')
print(f'  fact: {tc.get("fact",0)}/40, comparison: {tc.get("comparison",0)}/20, summary: {tc.get("summary",0)}/20')

if errors:
    print(f'\nErrors ({len(errors)}):')
    for e in errors[:20]:
        print(f'  {e}')

new_eval = {'metadata': {'total_samples': len(new_samples)}, 'samples': new_samples}
with open('data/eval/eval_dataset_table_protection.json', 'w', encoding='utf-8') as f:
    json.dump(new_eval, f, ensure_ascii=False, indent=2)
print(f'\nSaved: eval_dataset_table_protection.json ({len(new_samples)} samples)')
