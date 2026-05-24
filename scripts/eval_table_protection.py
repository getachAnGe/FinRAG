"""第二步：新chunker切块后，重建评测集chunk_id映射，跑BM25 Recall"""
import os, sys, json, re, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.chunker import SemanticChunker
from core.retriever.bm25_search import BM25Retriever

PARSED_DIR = "data/parsed"
EVAL_FILE = "data/eval/eval_dataset_three_type.json"
NEW_CHUNKS_FILE = "data/chunks/all_chunks_table_protection.json"

print("=" * 70)
print("第二步：表格保护 - 重建评测集 + BM25 Recall")
print("=" * 70)

# 1. 新chunker切块
print("\n[1/4] 新chunker切块...")
chunker = SemanticChunker(chunk_size=512, chunk_overlap=100)
all_chunks = []
for fpath in sorted(os.listdir(PARSED_DIR)):
    if not fpath.endswith('.json') or fpath.startswith('H3_'): continue
    try:
        with open(os.path.join(PARSED_DIR, fpath), 'r', encoding='utf-8') as f:
            parsed = json.load(f)
        source = parsed.get("source", fpath.replace(".json", ".pdf"))
        pages = parsed.get("pages", [])
        chunks = chunker.chunk_parsed_document({"pages": pages}, source_file=source)
        all_chunks.extend(chunks)
    except Exception as e:
        print(f"  跳过 {fpath}: {e}")

total = len(all_chunks)
tables = sum(1 for c in all_chunks if c.chunk_type == "table")
avg_len = sum(len(c.text) for c in all_chunks) / total if total else 0
print(f"  总chunk数: {total}, 表格chunk: {tables}, 平均长度: {avg_len:.0f}")

# 保存
os.makedirs(os.path.dirname(NEW_CHUNKS_FILE), exist_ok=True)
with open(NEW_CHUNKS_FILE, 'w', encoding='utf-8') as f:
    json.dump([c.to_dict() for c in all_chunks], f, ensure_ascii=False)
print(f"  已保存到 {NEW_CHUNKS_FILE}")

# 2. 加载旧评测集，找新chunk中对应的id
print("\n[2/4] 在新chunk中搜索对应chunk_id...")
with open(EVAL_FILE, 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
old_samples = eval_data['samples']

new_chunk_map = {}
for c in all_chunks:
    new_chunk_map[c.id] = c

# 搜索函数：在新chunk中按source+page+value找到对应的chunk_id
def find_in_new_chunks(source, page, value):
    val_clean = value.replace(',', '')
    for c in all_chunks:
        if source not in c.source: continue
        if str(c.page_num) != str(page): continue
        if val_clean in c.text.replace(',', ''):
            return c.id
    # fallback: just company
    parts = source.replace('.pdf','').split('_')
    if len(parts) >= 2:
        company = parts[1]
        for c in all_chunks:
            if company not in c.source: continue
            if str(c.page_num) != str(page): continue
            if val_clean in c.text.replace(',', ''):
                return c.id
    return None

# 对每个sample重新搜索chunk_id
new_samples = []
errors = []
for s in old_samples:
    qt = s['query_type']
    ans = s['ground_truth_answer']
    
    if qt == 'fact':
        src = s['source_file']
        page = s['page_num']
        cid = find_in_new_chunks(src, page, ans)
        if not cid:
            errors.append(f"  ❌ [{s['company']}] {src} p{page} - 找不到chunk")
            continue
        # 验证
        c = new_chunk_map.get(cid)
        if not (c and src in c.source and str(c.page_num) == str(page)):
            errors.append(f"  ⚠️ [{s['company']}] {src} p{page} -> chunk不匹配: {c.source} p{c.page_num}")
            continue
        new_s = s.copy()
        new_s['ground_truth_chunk_id'] = cid
        new_samples.append(new_s)
    
    elif qt == 'comparison':
        # 对比型需要分别搜两个value
        # 从原问题提取页码对
        pairs = re.findall(r'_同花顺_\d+第\d+页', s['query'])
        # 从答案提取关键数字
        nums = re.findall(r'[\d.]+(?=%)|[\d,]+(?=亿元|万元)', ans)
        if len(nums) >= 2:
            # 尝试从question解析来源
            q = s['query']
            srcs_found = re.findall(r'(\w+_\w+_同花顺_\d+第(\d+)页)', q)
            if len(srcs_found) >= 2:
                all_ok = True
                cids = []
                for idx, (full_match, pg) in enumerate(srcs_found):
                    src_name = full_match.rsplit('第', 1)[0] + '.pdf'
                    num = nums[idx] if idx < len(nums) else nums[0]
                    cid = find_in_new_chunks(src_name, pg, num)
                    if cid:
                        cids.append(cid)
                    else:
                        all_ok = False
                        errors.append(f"  ❌ 对比型[{s['company']}] {src_name} p{pg} - 找不到chunk")
                if all_ok and len(cids) >= 2:
                    new_s = s.copy()
                    new_s['ground_truth_chunk_id'] = ','.join(cids[:2])
                    new_samples.append(new_s)
                else:
                    continue
            else:
                errors.append(f"  ❌ 对比型[{s['company']}] - 无法解析来源")
                continue
        else:
            errors.append(f"  ❌ 对比型[{s['company']}] - 无法提取数字")
            continue
    
    elif qt == 'summary':
        src = s['source_file']
        page = s['page_num']
        # 取答案中的关键数字/词来搜索
        nums = re.findall(r'[\d.]+(?=亿|万|%)|[\d,]+', ans)
        found = False
        for num in nums:
            if len(num) > 2:
                cid = find_in_new_chunks(src, page, num)
                if cid:
                    new_s = s.copy()
                    new_s['ground_truth_chunk_id'] = cid
                    new_samples.append(new_s)
                    found = True
                    break
        if not found:
            # 尝试取第一个长关键词
            kws = [kw for kw in ans.split('，') if len(kw) > 6]
            if kws:
                for kw in kws[:3]:
                    for c in all_chunks:
                        if src in c.source and str(c.page_num) == str(page) and kw in c.text:
                            new_s = s.copy()
                            new_s['ground_truth_chunk_id'] = c.id
                            new_samples.append(new_s)
                            found = True
                            break
                    if found: break
            if not found:
                errors.append(f"  ❌ 汇总型[{s['company']}] {src} p{page} - 找不到chunk")

if errors:
    print(f"  错误: {len(errors)}")
    for e in errors[:10]:
        print(e)
else:
    print(f"  全部成功!")

print(f"  重建: {len(new_samples)}/{len(old_samples)}条")

from collections import Counter
tc = Counter(s['query_type'] for s in new_samples)
print(f"  事实型: {tc.get('fact',0)}, 对比型: {tc.get('comparison',0)}, 汇总型: {tc.get('summary',0)}")

# 3. 建BM25
print("\n[3/4] 建BM25索引...")
bm25 = BM25Retriever(k1=1.5, b=0.75)
# Only use new chunks that are referenced in eval
ref_ids = set()
for s in new_samples:
    for cid in s['ground_truth_chunk_id'].split(','):
        ref_ids.add(cid.strip())

documents = []
for c in all_chunks:
    documents.append({"id": c.id, "text": c.text, "source": c.source, "page_num": c.page_num})
bm25.add_documents([c.id for c in all_chunks], documents)
print(f"  BM25索引包含: {len(all_chunks)}个chunk")

# 4. 跑Recall@3/5/10 (BM25, top_k=200)
print("\n[4/4] 跑BM25 Recall（top_k=200）...")
def calc_recall(samples_lst, k, search_k=200):
    hits = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    totals = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    for s in samples_lst:
        qt = s['query_type']
        totals[qt] += 1
        target_ids = [x.strip() for x in s['ground_truth_chunk_id'].split(',') if x.strip()]
        results = bm25.search(s['query'], top_k=search_k)
        retrieved_ids = [r.get("id", "") for r in results[:k]]
        if any(tid in retrieved_ids for tid in target_ids):
            hits[qt] += 1
    total_hits = sum(hits.values())
    total_all = sum(totals.values())
    return hits, totals, total_hits/total_all*100

results = {}
for k in [3, 5, 10]:
    results[k] = calc_recall(new_samples, k)

print(f"\n{'='*70}")
print(f"{'指标':>10} | {'事实型':>8} | {'对比型':>8} | {'汇总型':>8} | {'总体':>8}")
print(f"{'-'*50}")
for k in [3, 5, 10]:
    r_label = f"R@{k}"
    hits, totals, overall = results[k]
    f_pct = hits['fact']/totals['fact']*100 if totals['fact'] else 0
    c_pct = hits['comparison']/totals['comparison']*100 if totals['comparison'] else 0
    s_pct = hits['summary']/totals['summary']*100 if totals['summary'] else 0
    print(f"{r_label:>10} | {f_pct:>7.1f}% | {c_pct:>7.1f}% | {s_pct:>7.1f}% | {overall:>7.1f}%")

# 对照旧数据
print(f"\n{'='*70}")
print("新旧对比")
print(f"{'='*70}")
print(f"{'方案':>18} | {'chunk数':>8} | {'表格chunk':>10} | {'平均长度':>8} | {'R@3':>6} | {'R@5':>6} | {'R@10':>6}")
print(f"{'旧方案(合并切)':>18} | {'62330':>8} | {'0':>10} | {'455':>8} | {'35.0%':>6} | {'41.2%':>6} | {'54.0%':>6}")
new_r3 = results[3][2]
new_r5 = results[5][2]
new_r10 = results[10][2]
print(f"{'新方案(表格独立)':>18} | {total:>8} | {tables:>10} | {avg_len:>8.0f} | {new_r3:>5.1f}% | {new_r5:>5.1f}% | {new_r10:>5.1f}%")

old_r5 = 41.2
if new_r5 > old_r5:
    print(f"\n✅ 表格保护策略 Recall@5 提升 {new_r5 - old_r5:.1f} 个百分点")
elif new_r5 < old_r5:
    print(f"\n⚠️ 表格保护策略 Recall@5 下降 {old_r5 - new_r5:.1f} 个百分点")
else:
    print(f"\n↔️ 表格保护策略 Recall@5 持平")

# 保存新评测集
new_eval = {
    'metadata': {
        'total_samples': len(new_samples),
        'fact_samples': tc.get('fact', 0),
        'comparison_samples': tc.get('comparison', 0),
        'summary_samples': tc.get('summary', 0),
    },
    'samples': new_samples
}
with open('data/eval/eval_dataset_table_protection.json', 'w', encoding='utf-8') as f:
    json.dump(new_eval, f, ensure_ascii=False, indent=2)
print(f"\n新评测集已保存到 data/eval/eval_dataset_table_protection.json")
