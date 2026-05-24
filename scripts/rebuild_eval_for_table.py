"""直接在new_chunks中搜索，绕过编码问题"""
import json, re
from collections import Counter

with open('data/chunks/all_chunks_table_protection.json', 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open('data/eval/eval_dataset_three_type.json', 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
old_samples = eval_data['samples']

def find_cids(source, page, search_vals):
    """Find chunk_ids in new_chunks matching source+page+any of search_vals"""
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

new_samples = []
errors = []

for s in old_samples:
    qt = s['query_type']
    ans = s['ground_truth_answer']
    
    if qt == 'fact':
        src = s['source_file']
        page = s['page_num']
        # search by answer value
        vals = re.findall(r'[\d,.]+', ans)
        if not vals: vals = [ans[:10]]
        cids = find_cids(src, page, vals)
        if cids:
            ns = s.copy()
            ns['ground_truth_chunk_id'] = cids[0]
            new_samples.append(ns)
        else:
            errors.append(f'FACT: {s["company"]} {src} p{page}')
    
    elif qt == 'comparison':
        q = s['query']
        # Parse sources and pages from question
        parts = re.findall(r'(\w+_\w+_同花顺_\d+)第(\d+)页', q)
        if len(parts) >= 2:
            all_cids = []
            for idx, (src_base, pg) in enumerate(parts):
                src = src_base + '.pdf'
                # Get the number for this source from answer
                nums = re.findall(r'[\d,.]+', ans.split('高于')[idx] if '高于' in ans else ans)
                if nums:
                    cids = find_cids(src, pg, nums)
                    if cids:
                        all_cids.append(cids[0])
            if len(all_cids) >= 2:
                ns = s.copy()
                ns['ground_truth_chunk_id'] = ','.join(all_cids[:2])
                new_samples.append(ns)
            else:
                errors.append(f'COMP: {s["company"]}')
        else:
            errors.append(f'COMP parse fail: {q[:40]}')
    
    elif qt == 'summary':
        src = s['source_file']
        page = s['page_num']
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            # Use first keyword
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = [kws[0]] if kws else [ans[:8]]
        cids = find_cids(src, page, vals)
        if cids:
            ns = s.copy()
            ns['ground_truth_chunk_id'] = cids[0]
            new_samples.append(ns)
        else:
            errors.append(f'SUM: {s["company"]} {src} p{page}')

tc = Counter(s['query_type'] for s in new_samples)
print(f'重建: {len(new_samples)}/{len(old_samples)}条')
print(f'  事实型: {tc.get("fact",0)}/40, 对比型: {tc.get("comparison",0)}/20, 汇总型: {tc.get("summary",0)}/20')
if errors:
    print(f'\n错误 ({len(errors)}个):')
    for e in errors[:15]:
        print(f'  {e}')

# Save
new_eval = {
    'metadata': {'total_samples': len(new_samples), 'fact_samples': tc.get('fact',0),
                 'comparison_samples': tc.get('comparison',0), 'summary_samples': tc.get('summary',0)},
    'samples': new_samples
}
with open('data/eval/eval_dataset_table_protection.json', 'w', encoding='utf-8') as f:
    json.dump(new_eval, f, ensure_ascii=False, indent=2)
print(f'\n已保存: eval_dataset_table_protection.json')
