"""调试Reranker GPU加载"""
import os, sys, logging
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_helper import load_config
import torch

config = load_config("config/config.yaml")
print(f"CUDA可用: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB" if torch.cuda.is_available() else "")

# 先测embedder
from core.indexer.embedder import Embedder
print(f"\n加载Embedder模型: {config['embedding']['model_name']}")
embedder = Embedder(model_name=config["embedding"]["model_name"], device="cpu")
print(f"Embedder维度: {embedder.dimension}")
print(f"Embedder模型: {type(embedder.model).__name__ if embedder.model else None}")

# 测试embed
q = "北方华创2025年的营业收入是多少？"
qv = embedder.encode_single(q)
print(f"查询向量维度: {qv.shape if qv is not None else 'None'}")

# 加载vector retriever
from core.retriever.vector_search import VectorRetriever
vector_dir = "data/vector_store"
vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
import json
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)
print(f"向量索引维度: {vector_retriever.index.d if hasattr(vector_retriever, 'index') and vector_retriever.index else 'None'}")

# 测试搜索
from core.retriever.bm25_search import BM25Retriever
bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

vr = vector_retriever.search(qv, top_k=200) if qv is not None else []
print(f"向量召回: {len(vr)}条, 第一条id: {vr[0]['id'] if vr else 'None'}")

# 加载Reranker
print(f"\n加载Reranker模型: {config['reranker']['model_name']}")
print(f"加载前显存: {torch.cuda.memory_allocated()/1024**2:.0f}MB / {torch.cuda.memory_reserved()/1024**2:.0f}MB" if torch.cuda.is_available() else "")

from core.retriever.reranker import Reranker
reranker = Reranker(model_name=config["reranker"]["model_name"], device="cuda")

if torch.cuda.is_available():
    print(f"加载后显存: {torch.cuda.memory_allocated()/1024**2:.0f}MB / {torch.cuda.memory_reserved()/1024**2:.0f}MB")
    if reranker.model:
        print(f"Reranker模型参数量: {sum(p.numel() for p in reranker.model.parameters())/1e6:.0f}M")
        print(f"Reranker模型显存占用: {sum(p.numel() * p.element_size() for p in reranker.model.parameters())/1024**2:.0f}MB")

# 测试rerank
print(f"\n测试Rerank...")
from collections import defaultdict
rrf_k = 40
# RRF融合
br = bm25_retriever.search(q, top_k=200)
scores = {}
docs = {}
for rank, r in enumerate(vr):
    rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(rrf_k+rank+1); docs[rid] = r
for rank, r in enumerate(br):
    rid = r.get("id",""); scores[rid] = scores.get(rid,0) + 1.0/(rrf_k+rank+1)
    if rid not in docs: docs[rid] = r
sids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
fused = [docs[rid] for rid in sids]

print(f"候选chunks: {len(fused[:30])}")

top5 = reranker.rerank(q, fused[:30], top_k=5) if reranker else fused[:30]
print(f"Rerank后Top5 ids: {[r.get('id','') for r in top5]}")

if torch.cuda.is_available():
    print(f"Rerank后显存: {torch.cuda.memory_allocated()/1024**2:.0f}MB / {torch.cuda.memory_reserved()/1024**2:.0f}MB")
