"""测试表格保护策略：改前（旧）vs 改后（新），对比chunk数量和BM25 Recall"""
import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.chunker import SemanticChunker
from core.retriever.bm25_search import BM25Retriever

PARSED_DIR = "data/parsed"
EVAL_FILE = "data/eval/eval_dataset_three_type.json"

def run_chunking(chunk_size=512, chunk_overlap=100):
    chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []
    table_count = 0
    for fpath in sorted(os.listdir(PARSED_DIR)):
        if not fpath.endswith('.json') or fpath.startswith('H3_'): continue
        try:
            with open(os.path.join(PARSED_DIR, fpath), 'r', encoding='utf-8') as f:
                parsed = json.load(f)
            source = parsed.get("source", fpath.replace(".json", ".pdf"))
            pages = parsed.get("pages", [])
            chunks = chunker.chunk_parsed_document({"pages": pages}, source_file=source)
            for c in chunks:
                if c.chunk_type == "table":
                    table_count += 1
            all_chunks.extend(chunks)
        except: pass
    return all_chunks, table_count

print("=" * 70)
print("表格保护策略测试")
print("=" * 70)

# Run new chunker
print("\n正在用新chunker切块（chunk_size=512, overlap=100）...")
new_chunks, new_tables = run_chunking()
new_total = len(new_chunks)
new_avg_len = sum(len(c.text) for c in new_chunks) / new_total if new_total else 0

print(f"  总chunk数: {new_total}")
print(f"  其中表格chunk: {new_tables}")
print(f"  平均长度: {new_avg_len:.0f}")

# Build BM25 with new chunks
print("\n正在建BM25索引...")
bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents([c.id for c in new_chunks],
    [{"id": c.id, "text": c.text, "source": c.source, "page_num": c.page_num} for c in new_chunks])

# Run eval
with open(EVAL_FILE, 'r', encoding='utf-8') as f:
    samples = json.load(f)['samples']

def calc_recall(samples, bm25_obj, k, search_k=200):
    hits = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    totals = {qt: 0 for qt in ['fact', 'comparison', 'summary']}
    for s in samples:
        qt = s['query_type']
        totals[qt] += 1
        target_ids = [x.strip() for x in s['ground_truth_chunk_id'].split(',') if x.strip()]
        results = bm25_obj.search(s['query'], top_k=search_k)
        retrieved_ids = [r.get("id", "") for r in results[:k]]
        if any(tid in retrieved_ids for tid in target_ids):
            hits[qt] += 1
    total_hits = sum(hits.values())
    total_all = sum(totals.values())
    return hits, totals, total_hits/total_all*100

print("\n正在用80条评测集测试（BM25 top_k=200）...")
b3 = calc_recall(samples, bm25, 3)
b5 = calc_recall(samples, bm25, 5)
b10 = calc_recall(samples, bm25, 10)

print(f"\n{'='*70}")
print(f"{'指标':>10} | {'事实型':>8} | {'对比型':>8} | {'汇总型':>8} | {'总体':>8}")
print(f"{'-'*50}")
for label, (hits, totals, overall) in [("R@3", b3), ("R@5", b5), ("R@10", b10)]:
    f_pct = hits['fact']/totals['fact']*100 if totals['fact'] else 0
    c_pct = hits['comparison']/totals['comparison']*100 if totals['comparison'] else 0
    s_pct = hits['summary']/totals['summary']*100 if totals['summary'] else 0
    print(f"{label:>10} | {f_pct:>7.1f}% | {c_pct:>7.1f}% | {s_pct:>7.1f}% | {overall:>7.1f}%")

# 对照旧chunk数据（之前跑的）
print(f"\n{'='*70}")
print("对照：旧方案（表格合并到文本中一起切）")
print(f"{'='*70}")
print(f"{'chunk_size':>10} {'chunk数':>8} {'表格chunk':>10} {'平均长度':>8} {'R@3':>6} {'R@5':>6} {'R@10':>6}")
old_data = {"512/100": {"total": 62330, "tables": 0, "avg": 455, "r3": 35.0, "r5": 41.2, "r10": 54.0}}
print(f"{'512/100旧':>10} {old_data['512/100']['total']:>8} {old_data['512/100']['tables']:>10} {old_data['512/100']['avg']:>8.0f} {old_data['512/100']['r3']:>5.1f}% {old_data['512/100']['r5']:>5.1f}% {old_data['512/100']['r10']:>5.1f}%")

print(f"\n{'新方案（表格独立）':>10} {new_total:>8} {new_tables:>10} {new_avg_len:>8.0f} ", end="")
for (hits, totals, overall) in [b3, b5, b10]:
    print(f"{overall:>5.1f}% ", end="")
print()

print(f"\n表格独立chunk占比: {new_tables/new_total*100:.1f}%")
