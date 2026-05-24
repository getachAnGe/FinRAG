import json
import sys
sys.path.insert(0, '.')

from core.retriever.bm25_search import BM25Retriever

print("Loading enhanced chunks...")
with open('data/chunks/all_chunks_enhanced.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

doc_ids = [chunk['id'] for chunk in chunks]

bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents(doc_ids, chunks)
bm25.save('data/vector_store/bm25_index')

print("BM25 index rebuilt successfully!")
