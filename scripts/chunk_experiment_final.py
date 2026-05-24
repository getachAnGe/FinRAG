import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.chunker import SemanticChunker
from core.retriever.bm25_search import BM25Retriever

PARSED_DIR = "data/parsed"
EVAL_FILE = "data/eval/eval_dataset_manual.json"

def run(cs, ov):
    chunker = SemanticChunker(chunk_size=cs, chunk_overlap=ov)
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
        except: pass

    total = len(all_chunks)
    avg_len = sum(len(c.text) for c in all_chunks) / total if total else 0

    bm25 = BM25Retriever(k1=1.5, b=0.75)
    bm25.add_documents([c.id for c in all_chunks],
        [{"id": c.id, "text": c.text, "source": c.source, "page_num": c.page_num} for c in all_chunks])

    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        samples = json.load(f)['samples']

    hits_1 = hits_3 = hits_5 = total_q = 0
    for s in samples:
        if s['query_type'] != 'fact': continue
        total_q += 1
        r = bm25.search(s['query'], top_k=20)
        docs = [x.get("document",{}) for x in r]
        src, pg = s['source_file'], str(s['page_num'])
        if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:1]): hits_1 += 1
        if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:3]): hits_3 += 1
        if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:5]): hits_5 += 1

    return total, avg_len, hits_1/total_q*100, hits_3/total_q*100, hits_5/total_q*100

print("=" * 70)
print("阶段1：固定 overlap=100，对比 chunk_size")
print("=" * 70)

s1 = []
for cs in [256, 512, 1024]:
    print(f"\n  chunk_size={cs}, overlap=100 ...")
    t, a, r1, r3, r5 = run(cs, 100)
    s1.append((cs, t, a, r1, r3, r5))
    print(f"    chunk数={t}, 平均长度={a:.0f}, R@1={r1:.1f}%, R@3={r3:.1f}%, R@5={r5:.1f}%")

print(f"\n{'='*70}")
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>8} {'平均长度':>8} {'R@1':>6} {'R@3':>6} {'R@5':>6}")
for cs, t, a, r1, r3, r5 in s1:
    print(f"{cs:>10} {'100':>8} {t:>8} {a:>8.0f} {r1:>5.1f}% {r3:>5.1f}% {r5:>5.1f}%")

best_cs = max(s1, key=lambda x: x[5])[0]
print(f"\n-> 最优 chunk_size = {best_cs}")

print(f"\n{'='*70}")
print(f"阶段2：固定 chunk_size={best_cs}，对比 overlap")
print(f"{'='*70}")

s2 = []
for ov in [50, 100, 150]:
    print(f"\n  chunk_size={best_cs}, overlap={ov} ...")
    t, a, r1, r3, r5 = run(best_cs, ov)
    s2.append((best_cs, ov, t, a, r1, r3, r5))
    print(f"    chunk数={t}, 平均长度={a:.0f}, R@1={r1:.1f}%, R@3={r3:.1f}%, R@5={r5:.1f}%")

print(f"\n{'='*70}")
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>8} {'平均长度':>8} {'R@1':>6} {'R@3':>6} {'R@5':>6}")
for cs, ov, t, a, r1, r3, r5 in s2:
    print(f"{cs:>10} {ov:>8} {t:>8} {a:>8.0f} {r1:>5.1f}% {r3:>5.1f}% {r5:>5.1f}%")

best_ov = max(s2, key=lambda x: x[6])[1]
print(f"\n-> 最优 overlap = {best_ov}")
print(f"\n最终推荐: chunk_size={best_cs}, overlap={best_ov}")
