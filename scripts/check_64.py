import json

with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['id']: c for c in json.load(f)}

with open('data/eval/eval_dataset_manual.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'当前共 {len(data["samples"])} 条')

# Check failures
for s in data['samples']:
    c = chunks.get(s['ground_truth_chunk_id'])
    text = c['text']
    ans = s['ground_truth_answer']
    ans_clean = ans.replace(',', '')
    found = ans_clean in text.replace(',', '')
    source_ok = s['source_file'] in c['source']
    page_ok = str(c['page_num']) == str(s['page_num'])
    if not (found and source_ok and page_ok):
        print(f'FAIL: [{s["company"]}] {s["indicator"]}={ans}')
        print(f'  source_ok={source_ok} (chunk={c["source"]}), page_ok={page_ok} (chunk_page={c["page_num"]})')
