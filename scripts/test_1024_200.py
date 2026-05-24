import os, sys, json, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.chunker import SemanticChunker
from core.retriever.bm25_search import BM25Retriever

PARSED_DIR = "data/parsed"
EVAL_FILE = "data/eval/eval_dataset_manual.json"

chunker = SemanticChunker(chunk_size=1024, chunk_overlap=200)
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
avg_len = sum(len(c.text) for c in all_chunks) / total
print(f"\nchunk_size=1024, overlap=200:")
print(f"  chunk总数={total}, 平均长度={avg_len:.0f}")

doc_ids = [c.id for c in all_chunks]
documents = [{"id": c.id, "text": c.text, "source": c.source, "page_num": c.page_num} for c in all_chunks]
bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents(doc_ids, documents)

with open(EVAL_FILE, 'r', encoding='utf-8') as f:
    samples = json.load(f)['samples']

hits_1 = hits_3 = hits_5 = total_q = 0
for s in samples:
    if s['query_type'] != 'fact': continue
    total_q += 1
    results = bm25.search(s['query'], top_k=20)
    src, pg = s['source_file'], str(s['page_num'])
    docs = [r.get("document",{}) for r in results]
    if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:1]): hits_1 += 1
    if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:3]): hits_3 += 1
    if any(d.get("source","")==src and str(d.get("page_num",""))==pg for d in docs[:5]): hits_5 += 1

print(f"  BM25 Recall@1={hits_1/total_q*100:.1f}%, @3={hits_3/total_q*100:.1f}%, @5={hits_5/total_q*100:.1f}%")
print(f"\n=== 完整对比表 ===")
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>7} {'平均长度':>7} {'R@1':>6} {'R@3':>6} {'R@5':>6}")
print(f"{'---':>10} {'---':>8} {'---':>7} {'---':>7} {'---':>6} {'---':>6} {'---':>6}")
print(f"{'256':>10} {'50':>8} {'130900':>7} {'232':>7} {'15.0%':>6} {'30.0%':>6} {'45.0%':>6}")
print(f"{'512':>10} {'50':>8} {'55716':>7} {'451':>7} {'15.0%':>6} {'35.0%':>6} {'45.0%':>6}")
print(f"{'1024':>10} {'50':>8} {'26973':>7} {'856':>7} {'15.0%':>6} {'40.0%':>6} {'55.0%':>6}")
print(f"{'1024':>10} {'100':>8} {'28147':>7} {'861':>7} {'25.0%':>6} {'35.0%':>6} {'60.0%':>6}")
print(f"{'1024':>10} {'200':>8} {total:>7} {avg_len:>7.0f} {hits_1/total_q*100:>5.1f}% {hits_3/total_q*100:>5.1f}% {hits_5/total_q*100:>5.1f}%")
