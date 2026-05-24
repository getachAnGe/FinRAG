"""BM25 Recall on table protection chunks using reconstructed eval"""
import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.retriever.bm25_search import BM25Retriever

with open('data/chunks/all_chunks_table_protection.json', 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open('data/eval/eval_dataset_table_protection.json', 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
samples = eval_data['samples']

print(f"评测集: {len(samples)}条")
from collections import Counter
tc = Counter(s['query_type'] for s in samples)
print(f"  fact={tc.get('fact',0)}, comparison={tc.get('comparison',0)}, summary={tc.get('summary',0)}")

# Build BM25
bm25 = BM25Retriever(k1=1.5, b=0.75)
docs = [{"id": c['id'], "text": c['text'], "source": c['source'], "page_num": c['page_num']} for c in new_chunks]
bm25.add_documents([c['id'] for c in new_chunks], docs)
print(f"BM25: {len(new_chunks)}个chunk")

# Calc Recall
def calc(samples_lst, k, search_k=200):
    hits = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    totals = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    for s in samples_lst:
        qt = s['query_type']
        totals[qt] += 1
        tids = [x.strip() for x in s['ground_truth_chunk_id'].split(',') if x.strip()]
        rids = [r.get("id","") for r in bm25.search(s['query'], top_k=search_k)[:k]]
        if any(t in rids for t in tids):
            hits[qt] += 1
    total_h = sum(hits.values())
    total_a = sum(totals.values())
    return hits, totals, total_h/total_a*100

results = {k: calc(samples, k) for k in [3, 5, 10]}

print(f"\n{'='*70}")
print(f"{'指标':>10} | {'事实型':>8} | {'对比型':>8} | {'汇总型':>8} | {'总体':>8}")
print(f"{'-'*50}")
for k in [3, 5, 10]:
    hits, totals, overall = results[k]
    f_pct = hits['fact']/totals['fact']*100 if totals['fact'] else 0
    c_pct = hits['comparison']/totals['comparison']*100 if totals['comparison'] else 0
    s_pct = hits['summary']/totals['summary']*100 if totals['summary'] else 0
    print(f"{'R@'+str(k):>10} | {f_pct:>7.1f}% | {c_pct:>7.1f}% | {s_pct:>7.1f}% | {overall:>7.1f}%")

old_r5 = 41.2
new_r5 = results[5][2]
print(f"\n{'='*70}")
print(f"新旧Recall@5对比")
print(f"{'='*70}")
print(f"{'方案':>18} | {'chunk数':>8} | {'表格chunk':>10} | {'平均长度':>8} | {'BM25 R@5':>10}")
print(f"{'旧(合并切)':>18} | {'62330':>8} | {'0':>10} | {'455':>8} | {'41.2%':>10}")
print(f"{'新(表格独立)':>18} | {len(new_chunks):>8} | {sum(1 for c in new_chunks if c.get('chunk_type')=='table'):>10} | {sum(len(c['text']) for c in new_chunks)/len(new_chunks):>8.0f} | {new_r5:>9.1f}%")

diff = new_r5 - old_r5
if diff > 0:
    print(f"\n✅ 提升 {diff:.1f} 个百分点")
elif diff < 0:
    print(f"\n❌ 下降 {abs(diff):.1f} 个百分点")
else:
    print(f"\n↔️ 持平")
