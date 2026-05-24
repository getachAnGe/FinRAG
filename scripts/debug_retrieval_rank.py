"""
检索排名诊断脚本
诊断目的：
1. 正确chunk在检索结果中的排名位置
2. 不同top_k下的命中率变化
3. 精简问题 vs 完整问题的效果差异
"""
import os, sys, json, re, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from utils.file_helper import load_config

config = load_config("config/config.yaml")
embedder = Embedder(model_name=config.get("embedding",{}).get("model_name"), device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

with open("data/eval/eval_dataset_precise.json", 'r', encoding='utf-8') as f:
    dataset = json.load(f)
samples = [s for s in dataset['samples'] if s['query_type'] == 'fact']

print("=" * 70)
print(f"检索排名诊断: {len(samples)} 个事实型问题")
print("=" * 70)

# === 测试1: 完整问题的检索排名 ===
print("\n\n【测试1】完整问题的检索排名 (top_k=500)")
print("-" * 70)

correct_at_k = {k: 0 for k in [1, 3, 5, 10, 20, 50, 100, 200, 500]}
total = 0
rank_records = []

for s in samples:
    total += 1
    q = s['query']
    target_chunk = s.get('ground_truth_chunk_id', '')
    target_src = s.get('source_file', '')
    target_page = s.get('page_num', '')

    # Vector search
    qv = embedder.encode_single(q)
    vec_results = vector_retriever.search(qv, top_k=500) if qv is not None else []
    
    # BM25 search
    bm25_results = bm25_retriever.search(q, top_k=500)
    
    # Combine + dedup
    combined = []
    seen = set()
    for r in vec_results + bm25_results:
        rid = r.get("id","")
        if rid not in seen:
            seen.add(rid)
            doc = r.get("document",{})
            if isinstance(doc, dict):
                r["src"] = doc.get("source","")
                r["pg"] = doc.get("page_num","")
            combined.append(r)
    
    # Sort by score descending (interleave)
    combined.sort(key=lambda x: -x.get("score", 0))
    
    # Find rank of target
    rank = -1
    page_rank = -1
    for i, r in enumerate(combined):
        if r.get("id","") == target_chunk:
            rank = i + 1
            break
        if r.get("src","") == target_src and str(r.get("pg","")) == str(target_page):
            if page_rank == -1:
                page_rank = i + 1
    
    # Record
    rank_records.append({
        'company': s.get('company','?'),
        'indicator': s.get('indicator','?'),
        'target_chunk': target_chunk,
        'source': target_src,
        'page': target_page,
        'rank': rank,
        'page_rank': page_rank,
        'total_retrieved': len(combined),
    })
    
    for k in correct_at_k:
        if rank != -1 and rank <= k:
            correct_at_k[k] += 1

# Print summary
print(f"\n总样本: {total}")
print(f"\n--- 不同top_k下的chunk精确命中率 ---")
for k in [1, 3, 5, 10, 20, 50, 100, 200, 500]:
    rate = correct_at_k[k] / total * 100
    print(f"  top_{k:3d}: {correct_at_k[k]:3d}/{total} = {rate:.1f}%")

print(f"\n--- 命中排名分布 ---")
found = [r for r in rank_records if r['rank'] != -1]
not_found = [r for r in rank_records if r['rank'] == -1]
print(f"  找到: {len(found)}/{total}")
print(f"  未找到(top_500内): {len(not_found)}/{total}")

if found:
    ranks = [r['rank'] for r in found]
    print(f"  找到样本的中位排名: {sorted(ranks)[len(ranks)//2]}")
    print(f"  找到样本的平均排名: {sum(ranks)/len(ranks):.0f}")
    print(f"  排名范围: {min(ranks)} ~ {max(ranks)}")
    
    # Rank distribution
    for bucket in [(1,1), (2,5), (6,10), (11,20), (21,50), (51,100), (101,200), (201,500)]:
        cnt = sum(1 for r in ranks if bucket[0] <= r <= bucket[1])
        print(f"    排名 {bucket[0]:3d}-{bucket[1]:3d}: {cnt} 条 ({cnt/len(ranks)*100:.1f}%)")

if not_found:
    print(f"\n--- 未找到样本示例 (前10条) ---")
    for r in not_found[:10]:
        print(f"  [{r['company']}] {r['indicator']} -> {r['source']} p{r['page']} (chunk={r['target_chunk']})")

# === 测试2: 精简问题 (去掉"在XXX第X页中"前缀) ===
print("\n\n【测试2】精简问题的检索效果对比 (top_k=20)")
print("-" * 70)

clean_correct = 0
full_correct = 0
test_samples = 0

for s in samples:
    test_samples += 1
    target_chunk = s.get('ground_truth_chunk_id', '')
    target_src = s.get('source_file', '')
    target_page = s.get('page_num', '')
    
    # Full question
    q_full = s['query']
    
    # Clean question: remove the "在XXX第X页中" prefix
    q_clean = re.sub(r'^在.+?第\d+页中，', '', q_full)
    # Also remove trailing （单位：xxx）
    q_clean = re.sub(r'（单位：.+?）', '', q_clean).strip()
    
    # Search full
    qv_full = embedder.encode_single(q_full)
    vec_full = vector_retriever.search(qv_full, top_k=20) if qv_full is not None else []
    bm25_full = bm25_retriever.search(q_full, top_k=20)
    combined_full = []
    seen_full = set()
    for r in vec_full + bm25_full:
        rid = r.get("id","")
        if rid not in seen_full:
            seen_full.add(rid)
            combined_full.append(r)
    full_ids = [r.get("id","") for r in combined_full]
    
    # Search clean
    qv_clean = embedder.encode_single(q_clean)
    vec_clean = vector_retriever.search(qv_clean, top_k=20) if qv_clean is not None else []
    bm25_clean = bm25_retriever.search(q_clean, top_k=20)
    combined_clean = []
    seen_clean = set()
    for r in vec_clean + bm25_clean:
        rid = r.get("id","")
        if rid not in seen_clean:
            seen_clean.add(rid)
            combined_clean.append(r)
    clean_ids = [r.get("id","") for r in combined_clean]
    
    if target_chunk in full_ids:
        full_correct += 1
    if target_chunk in clean_ids:
        clean_correct += 1

print(f"\n测试样本: {test_samples}")
print(f"完整问题 chunk命中: {full_correct}/{test_samples} = {full_correct/test_samples*100:.1f}%")
print(f"精简问题 chunk命中: {clean_correct}/{test_samples} = {clean_correct/test_samples*100:.1f}%")

# === 测试3: 单独看向量检索 vs BM25 ===
print("\n\n【测试3】向量检索 vs BM25 单独对比")
print("-" * 70)

vec_only = 0
bm25_only = 0
both = 0
neither = 0

for s in samples:
    target_chunk = s.get('ground_truth_chunk_id', '')
    q = s['query']
    
    qv = embedder.encode_single(q)
    vec_ids = [r.get("id","") for r in (vector_retriever.search(qv, top_k=50) if qv is not None else [])]
    bm25_ids = [r.get("id","") for r in bm25_retriever.search(q, top_k=50)]
    
    v = target_chunk in vec_ids
    b = target_chunk in bm25_ids
    
    if v and b: both += 1
    elif v: vec_only += 1
    elif b: bm25_only += 1
    else: neither += 1

n = len(samples)
print(f"\n(top_k=50) 向量 vs BM25 命中分布:")
print(f"  两者都命中: {both}/{n} = {both/n*100:.1f}%")
print(f"  仅向量命中: {vec_only}/{n} = {vec_only/n*100:.1f}%")
print(f"  仅BM25命中: {bm25_only}/{n} = {bm25_only/n*100:.1f}%")
print(f"  两者都未命中: {neither}/{n} = {neither/n*100:.1f}%")

# === 测试4: 看BM25的查询分词到底分成了什么 ===
print("\n\n【测试4】BM25分词效果检查")
print("-" * 70)

for s in samples[:3]:
    q = s['query']
    q_clean = re.sub(r'^在.+?第\d+页中，', '', q)
    q_clean = re.sub(r'（单位：.+?）', '', q_clean).strip()
    
    tokens_full = bm25_retriever.tokenizer.tokenize(q)
    tokens_clean = bm25_retriever.tokenizer.tokenize(q_clean)
    
    print(f"\n原始问题: {q[:60]}...")
    print(f"  BM25分词数量: {len(tokens_full)}")
    print(f"  分词结果(前40): {tokens_full[:40]}")
    print(f"\n精简问题: {q_clean}")
    print(f"  BM25分词数量: {len(tokens_clean)}")
    print(f"  分词结果: {tokens_clean[:30]}")

print("\n\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
