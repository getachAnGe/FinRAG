"""
全量向量化+建索引（已验证通过的方案）
"""
import os, sys, json, time, logging, shutil, tempfile
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from utils.file_helper import ensure_dir

chunks_path = os.path.join(PROJECT_ROOT, "data", "chunks", "all_chunks.json")
vector_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
ensure_dir(vector_dir)

with open(chunks_path, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

texts = [c.get('text', '') for c in chunks]
doc_ids = [c.get('id', f'chunk_{i}') for i, c in enumerate(chunks)]
logger.info(f"加载 {len(chunks)} 个chunk")

logger.info("加载 sentence-transformers 模型...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-base-zh-v1.5', device='cpu')
dim = model.get_sentence_embedding_dimension()
logger.info(f"模型加载完成, 维度: {dim}")

logger.info(f"向量化 {len(texts)} 个文本块 (batch_size=128)...")
t0 = time.time()

embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True, batch_size=128)

import numpy as np
vectors = np.array(embeddings)
t1 = time.time()
logger.info(f"向量化完成: {vectors.shape}, 耗时 {t1-t0:.1f}s")

logger.info("保存 FAISS 索引...")
import faiss
index = faiss.IndexFlatIP(dim)
index.add(vectors)

faiss_file = os.path.join(vector_dir, "faiss_index.index")
if os.path.exists(faiss_file):
    os.remove(faiss_file)

tmp_file = os.path.join(tempfile.gettempdir(), "faiss_full_tmp.index")
faiss.write_index(index, tmp_file)
shutil.move(tmp_file, faiss_file)
logger.info(f"FAISS 已保存 ({os.path.getsize(faiss_file)/1024/1024:.1f}MB)")

logger.info("保存 doc_store...")
doc_store = {c['id']: c for c in chunks}
with open(os.path.join(vector_dir, "doc_store.json"), 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)

# VectorRetriever兼容
store_data = {"doc_store": doc_store, "id_list": doc_ids, "dimension": dim}
with open(os.path.join(vector_dir, "faiss_index.store.json"), 'w', encoding='utf-8') as f:
    json.dump(store_data, f, ensure_ascii=False)
logger.info("doc_store 已保存")

logger.info("构建 BM25 索引...")
from core.retriever.bm25_search import BM25Retriever
bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents(doc_ids, [doc_store[cid] for cid in doc_ids])
bm25.save(os.path.join(vector_dir, "bm25_index"))
logger.info("BM25 已保存")

t2 = time.time()
logger.info(f"\n{'='*50}")
logger.info(f"全部完成!")
logger.info(f"  chunk数: {len(chunks)}")
logger.info(f"  维度: {dim}")
logger.info(f"  向量化耗时: {t1-t0:.1f}s")
logger.info(f"  总耗时: {t2-t0:.1f}s")
logger.info(f"{'='*50}")
