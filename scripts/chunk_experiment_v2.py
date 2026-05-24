"""两阶段切块实验：
阶段1：固定overlap=50，跑chunk_size=256/512/1024
阶段2：选最优chunk_size，跑overlap=50/100/200
每阶段记录：切块数量、平均长度、BM25 Recall@5
"""
import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.indexer.chunker import SemanticChunker
from core.retriever.bm25_search import BM25Retriever

PARSED_DIR = "data/parsed"
EVAL_FILE = "data/eval/eval_dataset_manual.json"

def get_all_parsed_files():
    files = []
    for f in os.listdir(PARSED_DIR):
        if f.endswith('.json') and not f.startswith('H3_'):
            files.append(os.path.join(PARSED_DIR, f))
    files.sort()
    return files

def load_parsed(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_experiment(chunk_size, overlap):
    chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=overlap)
    all_chunks = []
    all_files = get_all_parsed_files()
    
    for fpath in all_files:
        try:
            parsed = load_parsed(fpath)
            source = parsed.get("source", os.path.basename(fpath).replace(".json", ".pdf"))
            pages = parsed.get("pages", [])
            chunks = chunker.chunk_parsed_document({"pages": pages}, source_file=source)
            all_chunks.extend(chunks)
        except:
            pass
    
    total = len(all_chunks)
    avg_len = sum(len(c.text) for c in all_chunks) / total if total > 0 else 0
    
    # Build BM25 index
    doc_ids = [c.id for c in all_chunks]
    documents = [{
        "id": c.id,
        "text": c.text,
        "source": c.source,
        "page_num": c.page_num
    } for c in all_chunks]
    
    bm25 = BM25Retriever(k1=1.5, b=0.75)
    bm25.add_documents(doc_ids, documents)
    
    # Load eval questions
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    samples = eval_data['samples']
    
    # Recall: match by source file + page number (not chunk_id, since chunk_id changes)
    total_q = 0
    hits_1 = 0
    hits_3 = 0
    hits_5 = 0
    
    for s in samples:
        if s['query_type'] != 'fact':
            continue
        total_q += 1
        q = s['query']
        target_src = s['source_file']
        target_page = str(s['page_num'])
        
        results = bm25.search(q, top_k=20)
        
        # Check if any retrieved doc matches source+page
        found_1 = any(r.get("document",{}).get("source","") == target_src and str(r.get("document",{}).get("page_num","")) == target_page for r in results[:1])
        found_3 = any(r.get("document",{}).get("source","") == target_src and str(r.get("document",{}).get("page_num","")) == target_page for r in results[:3])
        found_5 = any(r.get("document",{}).get("source","") == target_src and str(r.get("document",{}).get("page_num","")) == target_page for r in results[:5])
        
        if found_1: hits_1 += 1
        if found_3: hits_3 += 1
        if found_5: hits_5 += 1
    
    r1 = hits_1 / total_q * 100 if total_q > 0 else 0
    r3 = hits_3 / total_q * 100 if total_q > 0 else 0
    r5 = hits_5 / total_q * 100 if total_q > 0 else 0
    
    return total, avg_len, r1, r3, r5, total_q

# ===== 阶段1 =====
print("=" * 70)
print("阶段1：固定 overlap=50，对比 chunk_size")
print("=" * 70)

stage1_results = []
for cs in [256, 512, 1024]:
    print(f"\n正在测试 chunk_size={cs}, overlap=50 ...")
    total, avg_len, r1, r3, r5, n = run_experiment(cs, 50)
    stage1_results.append((cs, 50, total, avg_len, r1, r3, r5))
    print(f"  切块总数={total}, 平均长度={avg_len:.0f}")
    print(f"  BM25 Recall@1={r1:.1f}%, @3={r3:.1f}%, @5={r5:.1f}%")

print("\n" + "=" * 70)
print("阶段1汇总")
print("=" * 70)
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>8} {'平均长度':>8} {'R@1':>6} {'R@3':>6} {'R@5':>6}")
for cs, ov, total, avg_len, r1, r3, r5 in stage1_results:
    print(f"{cs:>10} {ov:>8} {total:>8} {avg_len:>8.0f} {r1:>5.1f}% {r3:>5.1f}% {r5:>5.1f}%")

best_cs = max(stage1_results, key=lambda x: x[6])[0]
print(f"\n→ 最优 chunk_size = {best_cs}")

# ===== 阶段2 =====
print("\n" + "=" * 70)
print(f"阶段2：固定 chunk_size={best_cs}，对比 overlap")
print("=" * 70)

stage2_results = []
for ov in [50, 100, 200]:
    print(f"\n正在测试 chunk_size={best_cs}, overlap={ov} ...")
    total, avg_len, r1, r3, r5, n = run_experiment(best_cs, ov)
    stage2_results.append((best_cs, ov, total, avg_len, r1, r3, r5))
    print(f"  切块总数={total}, 平均长度={avg_len:.0f}")
    print(f"  BM25 Recall@1={r1:.1f}%, @3={r3:.1f}%, @5={r5:.1f}%")

print("\n" + "=" * 70)
print("阶段2汇总")
print("=" * 70)
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>8} {'平均长度':>8} {'R@1':>6} {'R@3':>6} {'R@5':>6}")
for cs, ov, total, avg_len, r1, r3, r5 in stage2_results:
    print(f"{cs:>10} {ov:>8} {total:>8} {avg_len:>8.0f} {r1:>5.1f}% {r3:>5.1f}% {r5:>5.1f}%")

best_ov = max(stage2_results, key=lambda x: x[6])[1]
print(f"\n最终推荐: chunk_size={best_cs}, overlap={best_ov}")
