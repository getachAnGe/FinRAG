"""
全流程索引构建 pipeline：
1. 重新切块（表格保护 + chunk_size=512, overlap=100）
2. 构建BM25索引
3. BGE-M3向量化
4. 构建FAISS索引
"""
import os, sys, json, time, logging, shutil, tempfile
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PARSED_DIR = os.path.join(ROOT, "data", "parsed")
CHUNKS_DIR = os.path.join(ROOT, "data", "chunks")
VECTOR_DIR = os.path.join(ROOT, "data", "vector_store")
CHUNKS_FILE = os.path.join(CHUNKS_DIR, "all_chunks.json")

os.makedirs(CHUNKS_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

# ================================================================
# 1. 切块
# ================================================================
logger.info("=" * 50)
logger.info("步骤1/4: 切块（表格保护 + 512/100）")
logger.info("=" * 50)

from core.indexer.chunker import SemanticChunker

chunker = SemanticChunker(chunk_size=512, chunk_overlap=100)
all_chunks = []

files = sorted(os.listdir(PARSED_DIR))
for fname in files:
    if not fname.endswith('.json') or fname.startswith('H3_'):
        continue
    try:
        with open(os.path.join(PARSED_DIR, fname), 'r', encoding='utf-8') as f:
            parsed = json.load(f)
        source = parsed.get("source", fname.replace(".json", ".pdf"))
        pages = parsed.get("pages", [])
        chunks = chunker.chunk_parsed_document({"pages": pages}, source_file=source)
        all_chunks.extend(chunks)
    except Exception as e:
        logger.warning(f"  跳过 {fname}: {e}")

total = len(all_chunks)
tables = sum(1 for c in all_chunks if c.chunk_type == "table")
avg_len = sum(len(c.text) for c in all_chunks) / total if total else 0
logger.info(f"  chunk数: {total}, 表格chunk: {tables}, 平均长度: {avg_len:.0f}")

# 保存chunk
chunk_dicts = [c.to_dict() for c in all_chunks]
with open(CHUNKS_FILE, 'w', encoding='utf-8') as f:
    json.dump(chunk_dicts, f, ensure_ascii=False)
logger.info(f"  已保存: {CHUNKS_FILE} ({os.path.getsize(CHUNKS_FILE)/1024/1024:.1f}MB)")

# ================================================================
# 2. BM25索引
# ================================================================
logger.info("=" * 50)
logger.info("步骤2/4: 构建BM25索引")
logger.info("=" * 50)

from core.retriever.bm25_search import BM25Retriever

doc_ids = [c['id'] for c in chunk_dicts]
documents = [{
    "id": c['id'],
    "text": c['text'],
    "source": c['source'],
    "page_num": c['page_num']
} for c in chunk_dicts]

t0 = time.time()
bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents(doc_ids, documents)
bm25.save(os.path.join(VECTOR_DIR, "bm25_index"))
logger.info(f"  BM25索引保存完成 ({time.time()-t0:.1f}s)")

# ================================================================
# 3. 向量化 + FAISS索引
# ================================================================
logger.info("=" * 50)
logger.info("步骤3-4/4: BGE-M3向量化 + FAISS索引")
logger.info("=" * 50)

texts = [c['text'] for c in chunk_dicts]
t0 = time.time()

from sentence_transformers import SentenceTransformer
logger.info(f"  加载BGE-M3模型...")
model = SentenceTransformer('BAAI/bge-m3', device='cpu')
dim = model.get_sentence_embedding_dimension()
logger.info(f"  模型加载完成, 维度: {dim}")

logger.info(f"  向量化 {len(texts)} 个chunk...")
embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True, batch_size=32)
import numpy as np
vectors = np.array(embeddings)
t1 = time.time()
logger.info(f"  向量化完成: {vectors.shape}, 耗时 {t1-t0:.1f}s")

logger.info(f"  构建FAISS索引...")
import faiss
index = faiss.IndexFlatIP(dim)
index.add(vectors)
logger.info(f"  FAISS索引包含 {index.ntotal} 个向量")

# 保存FAISS
faiss_file = os.path.join(VECTOR_DIR, "faiss_index.index")
if os.path.exists(faiss_file):
    os.remove(faiss_file)
tmp_file = os.path.join(tempfile.gettempdir(), "faiss_pipeline_tmp.index")
faiss.write_index(index, tmp_file)
shutil.move(tmp_file, faiss_file)
logger.info(f"  FAISS已保存 ({os.path.getsize(faiss_file)/1024/1024:.1f}MB)")

# 保存doc_store
doc_store = {c['id']: c for c in chunk_dicts}
with open(os.path.join(VECTOR_DIR, "doc_store.json"), 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)

store_data = {"doc_store": doc_store, "id_list": doc_ids, "dimension": dim}
with open(os.path.join(VECTOR_DIR, "faiss_index.store.json"), 'w', encoding='utf-8') as f:
    json.dump(store_data, f, ensure_ascii=False)
logger.info(f"  doc_store已保存")

t2 = time.time()
logger.info(f"\n{'='*50}")
logger.info(f"全流程完成!")
logger.info(f"  chunk数: {total} (表格chunk: {tables})")
logger.info(f"  平均长度: {avg_len:.0f}字")
logger.info(f"  向量维度: {dim}")
logger.info(f"  向量化耗时: {t1-t0:.1f}s ({((t1-t0)/60):.1f}min)")
logger.info(f"  总耗时: {t2-t0:.1f}s ({((t2-t0)/60):.1f}min)")
logger.info(f"{'='*50}")
