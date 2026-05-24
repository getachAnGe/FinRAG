import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from utils.file_helper import load_config

config = load_config("config/config.yaml")

# 加载向量检索器
vector_dir = "data/vector_store"
vector_retriever = VectorRetriever(dimension=1024)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

# 加载BM25检索器
bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

# 加载评测集
with open("data/eval/eval_dataset_three_type.json", 'r', encoding='utf-8') as f:
    eval_data = json.load(f)

# 取一个query测试
sample = eval_data['samples'][0]
q = sample['query']
print(f"Query: {q}")
print(f"Answer: {sample['ground_truth_answer']}")

# 模拟混合召回
from core.indexer.embedder import Embedder
embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
qv = embedder.encode_single(q) if embedder else None
vr = vector_retriever.search(qv, top_k=200) if qv is not None else []
br = bm25_retriever.search(q, top_k=200)

# RRF融合
from collections import defaultdict
rrf_k = 40
doc_scores = defaultdict(float)
doc_info = {}
for rank, result in enumerate(vr, 1):
    doc_id = result.get("id")
    doc_scores[doc_id] += 1.0 / (rrf_k + rank)
    doc_info[doc_id] = result
for rank, result in enumerate(br, 1):
    doc_id = result.get("id")
    doc_scores[doc_id] += 1.0 / (rrf_k + rank)
    if doc_id not in doc_info:
        doc_info[doc_id] = result

sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
fused = []
for doc_id, score in sorted_docs:
    result = doc_info[doc_id].copy()
    result["rrf_score"] = float(score)
    fused.append(result)

print("\n=== 检查融合后第一个chunk的数据结构 ===")
if fused:
    doc = fused[0]
    print(f"doc.keys(): {list(doc.keys())}")
    print(f"\ndoc['id']: {doc.get('id')}")
    print(f"\ndoc['document'] (if exists):")
    if 'document' in doc:
        print(f"  type: {type(doc['document'])}")
        print(f"  keys: {list(doc['document'].keys()) if isinstance(doc['document'], dict) else 'N/A'}")
    print(f"\ndoc['text'] (if exists):")
    if 'text' in doc:
        print(f"  type: {type(doc['text'])}")
        print(f"  preview: {doc['text'][:200] if isinstance(doc['text'], str) else str(doc['text'])}")

# 检查doc_store里的结构
print("\n=== 检查doc_store里的第一个chunk ===")
first_doc_id = next(iter(vector_retriever.doc_store.keys()), None)
if first_doc_id:
    doc_store_doc = vector_retriever.doc_store[first_doc_id]
    print(f"doc_store_doc.keys(): {list(doc_store_doc.keys())}")
    print(f"\ndoc_store_doc['text'] preview: {doc_store_doc.get('text', '')[:200]}")
