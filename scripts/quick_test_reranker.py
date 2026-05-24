"""快速测试Reranker修复是否有效"""
import os, sys, json, re, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from core.retriever.reranker import Reranker
from utils.file_helper import load_config

config = load_config("config/config.yaml")
SEARCH_TOP_K = 200
RRF_K = 40

embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

reranker = Reranker(model_name=config["reranker"]["model_name"], device="cpu")

# Load eval
with open("data/chunks/all_chunks.json", 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    eval_data = json.load(f)

def find_cid(source, page, search_vals):
    for c in new_chunks:
        if source not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        for sv in search_vals:
            if sv.replace(',','') in c.get('text','').replace(',',''):
                return c['id']
    return None

def find_cid_by_company(company, page, search_vals):
    for c in new_chunks:
        if company not in c.get('source',''): continue
        if str(c.get('page_num','')) != str(page): continue
        for sv in search_vals:
            if sv.replace(',','') in c.get('text','').replace(',',''):
                return c['id']
    return None

samples = []
for s in eval_data['samples']:
    qt, ans = s['query_type'], s['ground_truth_answer']
    if qt == 'fact':
        vals = re.findall(r'[\d,.]+', ans)
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; samples.append(ns)
    elif qt == 'comparison':
        parts = s['query'].split('和')
        if len(parts) >= 2:
            all_cids = []
            for idx in range(2):
                m = re.search(r'(\S+?)第(\d+)页', parts[idx])
                if m:
                    nums = re.findall(r'[\d,.]+', ans.split('高于')[idx]) if '高于' in ans else re.findall(r'[\d,.]+', ans)
                    cid = find_cid(m.group(1)+'.pdf', m.group(2), nums) or find_cid_by_company(m.group(1).split('_')[1], m.group(2), nums)
                    if cid: all_cids.append(cid)
            if len(all_cids) >= 2:
                ns = s.copy(); ns['ground_truth_chunk_id'] = ','.join(all_cids[:2]); samples.append(ns)
    elif qt == 'summary':
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = kws[:1] if kws else [ans[:8]]
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; samples.append(ns)

def get_target_ids(s):
    return [x.strip() for x in s.get('ground_truth_chunk_id','').split(',') if x.strip()]

def recall_at_k(results, sample, k):
    tids = get_target_ids(sample)
    rids = [r.get("id","") for r in results[:k]]
    return any(t in rids for t in tids)

def rrf_fusion(vr, br):
    scores = {}; docs = {}
    for rank, r in enumerate(vr):
        rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(RRF_K+rank+1); docs[rid] = r
    for rank, r in enumerate(br):
        rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(RRF_K+rank+1)
        if rid not in docs: docs[rid] = r
    sids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [docs[rid] for rid in sids]

# 只跑前5个query快速测试
print(f"快速测试前5个query...\n")
test_samples = samples[:5]

for i, s in enumerate(test_samples):
    q = s['query']
    ans = s['ground_truth_answer']
    print(f"Query {i+1}: {q}")
    print(f"Answer: {ans}")
    tids = get_target_ids(s)
    print(f"Target chunk ids: {tids}")
    
    qv = embedder.encode_single(q)
    vr = vector_retriever.search(qv, top_k=SEARCH_TOP_K) if qv is not None else []
    br = bm25_retriever.search(q, top_k=SEARCH_TOP_K)
    fused = rrf_fusion(vr, br)
    
    # No Reranker: top-5 direct
    top5_direct = fused[:5]
    recall_no = recall_at_k(top5_direct, s, 5)
    
    # 打印直接取Top-5的结果
    print("\n--- 直接取Top-5 ---")
    for j, r in enumerate(top5_direct):
        is_target = "✅" if r.get("id","") in tids else "  "
        print(f"  {j+1}. {r.get('id','')} {is_target}")
    
    # Reranker: rerank top-100 → top-5
    top100 = fused[:100]
    reranked = reranker.rerank(q, top100, top_k=5) if reranker else fused[:100]
    recall_yes = recall_at_k(reranked, s, 5)
    
    # 打印Reranker后的结果
    print("\n--- Reranker后取Top-5 ---")
    for j, r in enumerate(reranked):
        is_target = "✅" if r.get("id","") in tids else "  "
        score = r.get("rerank_score", "N/A")
        print(f"  {j+1}. {r.get('id','')} {is_target} (score: {score})")
    
    print(f"\n直接召回: {'✅' if recall_no else '❌'} | Reranker召回: {'✅' if recall_yes else '❌'}\n")
    print("="*70)
