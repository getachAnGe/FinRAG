"""切块参数对比实验：只统计切块数量和平均长度，不做BM25/向量化"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.indexer.chunker import SemanticChunker

PARSED_DIR = "data/parsed"

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

params = [
    (256, 50),
    (256, 100),
    (256, 200),
    (512, 50),
    (512, 100),
    (512, 200),
    (1024, 50),
    (1024, 100),
    (1024, 200),
]

all_files = get_all_parsed_files()
print(f"解析文件总数: {len(all_files)}")

results = []

for chunk_size, overlap in params:
    chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=overlap)
    all_chunks = []
    
    for fpath in all_files:
        try:
            parsed = load_parsed(fpath)
            source = parsed.get("source", os.path.basename(fpath).replace(".json", ".pdf"))
            pages = parsed.get("pages", [])
            chunks = chunker.chunk_parsed_document({"pages": pages}, source_file=source)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"  跳过 {fpath}: {e}")
    
    total = len(all_chunks)
    avg_len = sum(len(c.text) for c in all_chunks) / total if total > 0 else 0
    
    results.append((chunk_size, overlap, total, avg_len))
    print(f"chunk_size={chunk_size}, overlap={overlap}: {total} chunks, avg_len={avg_len:.0f}")

print("\n" + "=" * 70)
print(f"{'chunk_size':>10} {'overlap':>8} {'chunk数':>10} {'平均长度':>10}")
print("=" * 70)
for chunk_size, overlap, total, avg_len in results:
    print(f"{chunk_size:>10} {overlap:>8} {total:>10} {avg_len:>10.0f}")
