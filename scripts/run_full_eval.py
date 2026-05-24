"""三种召回方案对比评估：纯向量 / 纯BM25 / 混合召回
   使用 chunk_id 匹配（适用于所有问题类型）
"""
import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from utils.file_helper import load_config

config = load_config("config/config.yaml")
embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    dataset = json.load(f)
samples = dataset['samples']

def get_target_ids(s):
    """Get list of target chunk_ids for a sample"""
    cid = s.get('ground_truth_chunk_id', '')
    return [x.strip() for x in cid.split(',') if x.strip()]

def calc_recall_by_chunk_id(results_list, samples, k):
    hits = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    totals = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    
    for results, s in zip(results_list, samples):
        qt = s['query_type']
        totals[qt] += 1
        target_ids = get_target_ids(s)
        
        retrieved_ids = [r.get("id", "") for r in results[:k]]
        if any(tid in retrieved_ids for tid in target_ids):
            hits[qt] += 1
    
    total_hits = sum(hits.values())
    total_all = sum(totals.values())
    return hits, totals, total_hits/total_all*100

print("=" * 70)
print(f"三种召回方案对比评测（{len(samples)}条）")
print("=" * 70)

SEARCH_TOP_K = 200
RRF_K = 40

# === 1. 纯向量 ===
print("\n[1/3] 纯向量检索 ...")
v_results = []
for s in samples:
    qv = embedder.encode_single(s['query'])
    v_results.append(vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else [])

# === 2. 纯BM25 ===
print("\n[2/3] 纯BM25检索 ...")
b_results = []
for s in samples:
    b_results.append(bm25_retriever.search(s['query'], top_k=SEARCH_TOP_K))

# === 3. 混合召回(RRF) ===
print("\n[3/3] 混合召回（向量+BM25，RRF融合, k=40, 候选=200）...")

def rrf(vr, br, k=RRF_K, top_n=10):
    scores = {}
    docs = {}
    for rank, r in enumerate(vr):
        rid = r.get("id","")
        scores[rid] = scores.get(rid, 0) + 1.0/(k+rank+1)
        docs[rid] = r
    for rank, r in enumerate(br):
        rid = r.get("id","")
        scores[rid] = scores.get(rid, 0) + 1.0/(k+rank+1)
        if rid not in docs:
            docs[rid] = r
    sids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [docs[rid] for rid in sids[:top_n]]

h_results = []
for s in samples:
    qv = embedder.encode_single(s['query'])
    vr = vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else []
    br = bm25_retriever.search(s['query'], top_k=SEARCH_TOP_K)
    h_results.append(rrf(vr, br))

# === 计算各方案各类型 Recall ===
results = {}
for name, rlist in [("纯向量", v_results), ("纯BM25", b_results), ("混合召回", h_results)]:
    results[name] = {}
    for k in [3, 5, 10]:
        hits, totals, overall = calc_recall_by_chunk_id(rlist, samples, k)
        results[name][k] = (hits, totals, overall)

# === 打印表格 ===
print(f"\n{'='*70}")
print(f"{'召回方案':>12} | {'R@3':>35} | {'R@5':>35} | {'R@10':>35}")
print(f"{'-'*70}")
for name in ["纯向量", "纯BM25", "混合召回"]:
    parts = [f"{name:>12}"]
    for k in [3, 5, 10]:
        hits, totals, overall = results[name][k]
        parts.append(f"F{hits['fact']}/{totals['fact']} C{hits['comparison']}/{totals['comparison']} S{hits['summary']}/{totals['summary']} [{overall:.0f}%]")
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
