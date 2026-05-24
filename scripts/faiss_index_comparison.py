"""FAISS索引类型对比: Flat vs IVF vs HNSW"""
import os, sys, json, time, re
import numpy as np
import logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from utils.file_helper import load_config

config = load_config("config/config.yaml")
embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
vector_dir = "data/vector_store"

# Load eval questions
with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
old_samples = eval_data['samples']

# Rebuild eval mapping
with open("data/chunks/all_chunks.json", 'r', encoding='utf-8') as f:
    new_chunks = json.load(f)

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

new_samples = []
for s in old_samples:
    qt, ans = s['query_type'], s['ground_truth_answer']
    if qt == 'fact':
        vals = re.findall(r'[\d,.]+', ans)
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; new_samples.append(ns)
    elif qt == 'comparison':
        parts = s['query'].split('和')
        if len(parts) >= 2:
            all_cids = []
            for idx in range(2):
                m = re.search(r'(\S+?)第(\d+)页', parts[idx])
                if m:
                    src_base, pg = m.group(1), m.group(2)
                    nums = re.findall(r'[\d,.]+', ans.split('高于')[idx]) if '高于' in ans else re.findall(r'[\d,.]+', ans)
                    cid = find_cid(src_base+'.pdf', pg, nums) or find_cid_by_company(src_base.split('_')[1], pg, nums)
                    if cid: all_cids.append(cid)
            if len(all_cids) >= 2:
                ns = s.copy(); ns['ground_truth_chunk_id'] = ','.join(all_cids[:2]); new_samples.append(ns)
    elif qt == 'summary':
        vals = re.findall(r'[\d,.]+', ans)
        if not vals:
            kws = [kw for kw in ans.split('，') if len(kw) > 4]
            vals = kws[:1] if kws else [ans[:8]]
        cid = find_cid(s['source_file'], s['page_num'], vals) or find_cid_by_company(s['company'], s['page_num'], vals)
        if cid: ns = s.copy(); ns['ground_truth_chunk_id'] = cid; new_samples.append(ns)

print(f"评测集: {len(new_samples)}条")

# Load existing Flat index and reconstruct vectors
import faiss
import psutil

flat_path = os.path.join(vector_dir, "faiss_index.index")
flat_index = faiss.read_index(flat_path)
dim = flat_index.d
n_total = flat_index.ntotal
print(f"Flat索引: {n_total}个向量, 维度={dim}")

# Reconstruct all vectors
vectors = np.zeros((n_total, dim), dtype=np.float32)
for i in range(n_total):
    vectors[i] = flat_index.reconstruct(i)
print(f"向量提取完成: {vectors.shape}")

# Load doc_store for id_list (from store.json which has ordered id_list)
with open(os.path.join(vector_dir, "faiss_index.store.json"), 'r', encoding='utf-8') as f:
    store_data = json.load(f)
id_list = store_data.get('id_list', [])
if not id_list:
    with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
        doc_store = json.load(f)
    id_list = list(doc_store.keys())
assert len(id_list) == n_total, f"id_list长度({len(id_list)}) != 向量数({n_total})"

# Encode queries
query_texts = [s['query'] for s in new_samples]
print(f"编码 {len(query_texts)} 条查询...")
query_vectors = np.array([embedder.encode_single(q) for q in query_texts]).astype(np.float32)
faiss.normalize_L2(query_vectors)

def get_target_ids(s):
    return [x.strip() for x in s.get('ground_truth_chunk_id','').split(',') if x.strip()]

def eval_index(index, name, vectors, query_vectors, id_list, new_samples, build_time):
    import psutil
    proc = psutil.Process()
    
    # Memory after build
    mem = proc.memory_info().rss / 1024 / 1024
    
    # Query
    nq = len(query_vectors)
    queries_per_sec = max(1, nq // 5)
    
    # Warmup
    _ = index.search(query_vectors[:1], 10)
    
    # Timed queries
    t0 = time.time()
    all_distances, all_indices = index.search(query_vectors, 10)
    t1 = time.time()
    latency = (t1 - t0) / nq * 1000  # ms per query
    
    # Recall@10
    hits_by_type = {'fact':0,'comparison':0,'summary':0}
    totals_by_type = {'fact':0,'comparison':0,'summary':0}
    
    for idx, s in enumerate(new_samples):
        qt = s['query_type']
        totals_by_type[qt] += 1
        target_ids = get_target_ids(s)
        retrieved_ids = [id_list[i] for i in all_indices[idx] if i >= 0 and i < len(id_list)]
        if any(t in retrieved_ids for t in target_ids):
            hits_by_type[qt] += 1
    
    total_hits = sum(hits_by_type.values())
    total_all = sum(totals_by_type.values())
    recall = total_hits / total_all * 100 if total_all else 0
    
    return recall, latency, build_time, mem

results = {}

# === 1. Flat (already built) ===
print("\n[1/3] Flat 索引...")
faiss.normalize_L2(vectors)
flat_index = faiss.IndexFlatIP(dim)
flat_index.add(vectors)
r, lat, bt, mem = eval_index(flat_index, "Flat", vectors, query_vectors, id_list, new_samples, 0)
results["Flat"] = (r, lat, bt, mem)
print(f"  Recall@10={r:.1f}%, 延迟={lat:.1f}ms, 内存={mem:.0f}MB")

# === 2. IVF ===
print("\n[2/3] IVF 索引...")
n_centroids = int(np.sqrt(n_total))  # ~168
t0 = time.time()
ivf_index = faiss.IndexIVFFlat(faiss.IndexFlatIP(dim), dim, n_centroids, faiss.METRIC_INNER_PRODUCT)
ivf_index.train(vectors)
ivf_index.add(vectors)
ivf_index.nprobe = 10  # search probes
bt_ivf = time.time() - t0
r, lat, _, mem = eval_index(ivf_index, "IVF", vectors, query_vectors, id_list, new_samples, bt_ivf)
results["IVF"] = (r, lat, bt_ivf, mem)
print(f"  Recall@10={r:.1f}%, 延迟={lat:.1f}ms, 构建={bt_ivf:.1f}s, 内存={mem:.0f}MB")

# === 3. HNSW ===
print("\n[3/3] HNSW 索引...")
t0 = time.time()
hnsw_index = faiss.IndexHNSWFlat(dim, 32)  # M=32
hnsw_index.hnsw.efConstruction = 200
hnsw_index.add(vectors)
hnsw_index.hnsw.efSearch = 64
bt_hnsw = time.time() - t0
r, lat, _, mem = eval_index(hnsw_index, "HNSW", vectors, query_vectors, id_list, new_samples, bt_hnsw)
results["HNSW"] = (r, lat, bt_hnsw, mem)
print(f"  Recall@10={r:.1f}%, 延迟={lat:.1f}ms, 构建={bt_hnsw:.1f}s, 内存={mem:.0f}MB")

# === Summary Table ===
print("\n" + "=" * 75)
print(f"{'索引类型':>8} | {'Recall@10':>10} | {'查询延迟(ms)':>13} | {'构建时间(s)':>13} | {'内存占用(MB)':>13}")
print("=" * 75)
for name in ["Flat", "IVF", "HNSW"]:
    r, lat, bt, mem = results[name]
    print(f"{name:>8} | {r:>9.1f}% | {lat:>12.2f} | {bt:>12.1f} | {mem:>12.0f}")
print("=" * 75)
