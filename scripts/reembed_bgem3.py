"""
使用 BAAI/bge-m3 重新向量化所有切片并重建索引
"""
import os
import sys
import json
import time
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from utils.file_helper import ensure_dir
from core.indexer.embedder import Embedder, VectorIndex
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever

def main():
    chunks_path = os.path.join(PROJECT_ROOT, "data", "chunks", "all_chunks.json")
    vector_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
    ensure_dir(vector_dir)

    logger.info("=" * 60)
    logger.info("BGE-M3 重向量化")
    logger.info("=" * 60)

    logger.info(f"加载切片: {chunks_path}")
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    logger.info(f"共 {len(chunks)} 个切片")

    texts = [c.get('text', '') for c in chunks]
    doc_ids = [c.get('id', f'chunk_{i}') for i, c in enumerate(chunks)]

    logger.info("初始化 BGE-M3 Embedder (1024维)...")
    t0 = time.time()

    embedder = Embedder(
        model_name="BAAI/bge-m3",
        device="cpu",
        max_batch_size=16,
        max_length=512
    )

    logger.info(f"向量化 {len(texts)} 个文本块...")
    t1 = time.time()
    vectors = embedder.encode(texts, show_progress=True)
    t2 = time.time()
    logger.info(f"向量化完成: {vectors.shape[0]} 个向量, 维度 {vectors.shape[1]}, 耗时 {t2-t1:.1f}s")

    logger.info("=" * 60)
    logger.info("构建 FAISS 索引")
    logger.info("=" * 60)

    vector_index = VectorIndex(dimension=vectors.shape[1])
    vector_index.add_vectors(vectors, doc_ids)

    faiss_path = os.path.join(vector_dir, "faiss_index")
    faiss_index_file = faiss_path + ".index"
    if os.path.exists(faiss_index_file):
        os.remove(faiss_index_file)
    vector_index.save(faiss_path)
    logger.info(f"FAISS 索引已保存: {faiss_index_file}")

    doc_store = {}
    for chunk in chunks:
        cid = chunk.get('id', '')
        doc_store[cid] = {
            'id': cid,
            'text': chunk.get('text', ''),
            'source': chunk.get('source', ''),
            'page_num': chunk.get('page_num'),
            'bbox': chunk.get('bbox'),
            'chunk_type': chunk.get('chunk_type', 'text'),
            'parent_id': chunk.get('parent_id'),
            'metadata': chunk.get('metadata', {})
        }

    doc_store_path = os.path.join(vector_dir, "doc_store.json")
    with open(doc_store_path, 'w', encoding='utf-8') as f:
        json.dump(doc_store, f, ensure_ascii=False)
    logger.info(f"文档存储已保存: {doc_store_path}")

    logger.info("=" * 60)
    logger.info("构建 BM25 索引")
    logger.info("=" * 60)

    bm25_retriever = BM25Retriever(k1=1.5, b=0.75)
    bm25_retriever.add_documents(doc_ids, [doc_store[cid] for cid in doc_ids])
    bm25_path = os.path.join(vector_dir, "bm25_index")
    bm25_retriever.save(bm25_path)
    logger.info(f"BM25 索引已保存")

    t3 = time.time()
    logger.info("=" * 60)
    logger.info("全部完成!")
    logger.info(f"  - 模型: BAAI/bge-m3 (1024维)")
    logger.info(f"  - 向量化: {len(texts)} 个文本块, {t2-t1:.1f}s")
    logger.info(f"  - 总耗时: {t3-t0:.1f}s")
    logger.info(f"  - 输出: {vector_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
