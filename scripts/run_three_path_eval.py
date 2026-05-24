"""三种召回方案对比评估（新chunk + 重建评测集）"""
import os, sys, json, re, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from utils.file_helper import load_config

config = load_config("config/config.yaml")
SEARCH_TOP_K = 200
RRF_K = 40

# Load models
embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

# Load new chunks + rebuild eval
with open("data/chunks/all_chunks.json", 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
old_samples = eval_data['samples']

# Rebuild: find new chunk_ids
def find_cid(source, page, search_vals):
    for c in new_chunks:
        if source not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        text = c.get('text','').replace(',','')
        for sv in search_vals:
            if sv.replace(',','') in text:
                return c['id']
    return None

def find_cid_by_company(company, page, search_vals):
    for c in new_chunks:
        if company not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        text = c.get('text','').replace(',','')
        for sv in search_vals:
            if sv.replace(',','') in text:
                return c['id']
    return None

new_samples = []
for s in old_samples:
    qt = s['query_type']
    ans = s['ground_truth_answer']
    
    if qt == 'fact':
        src, page = s['source_file'], s['page_num']
        vals = re.findall(r'[\d,.]+', ans)
        cid = find_cid(src, page, vals) or find_cid_by_company(s['company'], page, vals)
        if cid:
            ns = s.copy(); ns['ground_truth_chunk_id'] = cid; new_samples.append(ns)
    
    elif qt == 'comparison':
        parts = s['query'].split('和')
        if len(parts) >= 2:
            all_cids = []
            for idx in range(2):
                m = re.search(r'(\S+?)第(\d+)页', parts[idx])
                if m:
                    src_base, pg = m.group(1), m.group(2)
                    src = src_base + '.pdf'
                    nums = re.findall(r'[\d,.]+', ans.split('高于')[idx]) if '高于' in ans else re.findall(r'[\d,.]+', ans)
                    cid = find_cid(src, pg, nums) or find_cid_by_company(src_base.split('_')[1], pg, nums)
                    if cid: all_cids.append(cid)
            if len(all_cids) >= 2:
                ns = s.copy(); ns['ground_truth_chunk_id'] = ','.join(all_cids[:2]); new_samples.append(ns)
    
    elif qt == 'summary':
        src, page = s['source_file'], s['page_num']
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = kws[:1] if kws else [ans[:8]]
        cid = find_cid(src, page, vals) or find_cid_by_company(s['company'], page, vals)
        if cid:
            ns = s.copy(); ns['ground_truth_chunk_id'] = cid; new_samples.append(ns)

from collections import Counter
tc = Counter(s['query_type'] for s in new_samples)
print(f"评测集: {len(new_samples)}条 (fact={tc.get('fact',0)} comparison={tc.get('comparison',0)} summary={tc.get('summary',0)})")

def get_target_ids(s):
    return [x.strip() for x in s.get('ground_truth_chunk_id','').split(',') if x.strip()]

def calc_recall_by_chunk_id(results_list, samples_list, k):
    hits = {'fact':0,'comparison':0,'summary':0}
    totals = {'fact':0,'comparison':0,'summary':0}
    for results, s in zip(results_list, samples_list):
        qt = s['query_type']; totals[qt] += 1
        tids = get_target_ids(s)
        rids = [r.get("id","") for r in results[:k]]
        if any(t in rids for t in tids):
            hits[qt] += 1
    total_h = sum(hits.values()); total_a = sum(totals.values())
    return hits, totals, total_h/total_a*100 if total_a else 0

def rrf(vr, br, k=RRF_K, top_n=10):
    scores = {}; docs = {}
    for rank, r in enumerate(vr):
        rid = r.get("id","")
        scores[rid] = scores.get(rid,0) + 1.0/(k+rank+1); docs[rid] = r
    for rank, r in enumerate(br):
        rid = r.get("id","")
        scores[rid] = scores.get(rid,0) + 1.0/(k+rank+1)
        if rid not in docs: docs[rid] = r
    sids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [docs[rid] for rid in sids[:top_n]]

print("=" * 70)
print("三种召回方案对比评测（新chunk: 表格保护+512/100）")
print("=" * 70)

# 1. 纯向量
print("\n[1/3] 纯向量检索 ...")
v_results = []
for s in new_samples:
    qv = embedder.encode_single(s['query'])
    v_results.append(vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else [])

# 2. 纯BM25
print("\n[2/3] 纯BM25检索 ...")
b_results = []
for s in new_samples:
    b_results.append(bm25_retriever.search(s['query'], top_k=SEARCH_TOP_K))

# 3. 混合
print("\n[3/3] 混合召回（向量+BM25，RRF融合）...")
h_results = []
for s in new_samples:
    qv = embedder.encode_single(s['query'])
    vr = vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else []
    br = bm25_retriever.search(s['query'], top_k=SEARCH_TOP_K)
    h_results.append(rrf(vr, br))

# Results
results = {}
for name, rlist in [("纯向量", v_results), ("纯BM25", b_results), ("混合召回", h_results)]:
    results[name] = {}
    for k in [3,5,10]:
        results[name][k] = calc_recall_by_chunk_id(rlist, new_samples, k)

print(f"\n{'='*70}")
print(f"{'召回方案':>12} | {'R@3':>35} | {'R@5':>35} | {'R@10':>35}")
print(f"{'-'*70}")
for name in ["纯向量", "纯BM25", "混合召回"]:
    parts = [f"{name:>12}"]
    for k in [3,5,10]:
        hits, totals, overall = results[name][k]
        f = f"{hits['fact']}/{totals['fact']}" if totals['fact'] else "0/0"
        c = f"{hits['comparison']}/{totals['comparison']}" if totals['comparison'] else "0/0"
        s = f"{hits['summary']}/{totals['summary']}" if totals['summary'] else "0/0"
        parts.append(f"F{f} C{c} S{s} [{overall:.0f}%]")
    print(f"{' | '.join(parts)}")

print(f"\n{'='*70}")
print("Recall@5 对比")
print(f"{'='*70}")
print(f"{'召回方案':>12} | {'事实型':>8} | {'对比型':>8} | {'汇总型':>8} | {'总体':>8}")
print(f"{'-'*50}")
for name in ["纯向量", "纯BM25", "混合召回"]:
    hits, totals, overall = results[name][5]
    f_pct = hits['fact']/totals['fact']*100 if totals['fact'] else 0
    c_pct = hits['comparison']/totals['comparison']*100 if totals['comparison'] else 0
    s_pct = hits['summary']/totals['summary']*100 if totals['summary'] else 0
    print(f"{name:>12} | {f_pct:>7.1f}% | {c_pct:>7.1f}% | {s_pct:>7.1f}% | {overall:>7.1f}%")

best = max([("纯向量", results["纯向量"][5][2]), ("纯BM25", results["纯BM25"][5][2]), ("混合召回", results["混合召回"][5][2])], key=lambda x: x[1])
print(f"\n结论: Recall@5最优为 '{best[0]}' ({best[1]:.1f}%)")
