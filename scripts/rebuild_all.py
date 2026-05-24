"""
重新切块 + 向量化 + 建索引
修复：同一页的文本+表格合并成一个chunk
"""
import os, sys, json, time, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from utils.file_helper import ensure_dir
from core.indexer.chunker import SemanticChunker
from core.indexer.embedder import Embedder, VectorIndex
from core.retriever.bm25_search import BM25Retriever

def main():
    parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed")
    chunks_dir = os.path.join(PROJECT_ROOT, "data", "chunks")
    vector_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
    ensure_dir(chunks_dir)
    ensure_dir(vector_dir)

    # 只处理真实公司的文件（过滤掉H3开头的）
    files = [f for f in os.listdir(parsed_dir) if f.endswith('.json') and not f.startswith('H3')]
    logger.info(f"找到 {len(files)} 个真实研报的解析文件")

    # 阶段1: 重新切块
    logger.info("=" * 60)
    logger.info("阶段1: 重新切块（文本+表格合并）")
    logger.info("=" * 60)
    
    chunker = SemanticChunker(chunk_size=512, chunk_overlap=50)
    all_chunks = []
    
    for fname in files:
        filepath = os.path.join(parsed_dir, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        
        source = data.get('source', fname)
        pages = data.get('pages', [])
        if not pages:
            continue
        
        for page_data in pages:
            page_num = page_data.get("page_num", 0)
            page_chunks = chunker._chunk_page(page_data, source, page_num)
            all_chunks.extend(page_chunks)
    
    logger.info(f"共生成 {len(all_chunks)} 个chunk")
    
    chunks_file = os.path.join(chunks_dir, "all_chunks.json")
    chunker.save_chunks(all_chunks, chunks_file)
    
    # 提取文本和doc_ids
    texts = [c.text for c in all_chunks]
    doc_ids = [c.id for c in all_chunks]
    
    # 阶段2: BGE向量化
    logger.info("=" * 60)
    logger.info("阶段2: BGE向量化")
    logger.info("=" * 60)
    
    embedder = Embedder(model_name="BAAI/bge-base-zh-v1.5", device="cpu")
    logger.info(f"向量化 {len(texts)} 个文本块...")
    t0 = time.time()
    vectors = embedder.encode(texts, show_progress=True)
    t1 = time.time()
    logger.info(f"完成: {vectors.shape}, 耗时 {t1-t0:.1f}s")
    
    # 阶段3: FAISS索引
    logger.info("=" * 60)
    logger.info("阶段3: FAISS索引")
    logger.info("=" * 60)
    
    vector_index = VectorIndex(dimension=vectors.shape[1])
    vector_index.add_vectors(vectors, doc_ids)
    
    faiss_path = os.path.join(vector_dir, "faiss_index")
    if os.path.exists(faiss_path + ".index"):
        os.remove(faiss_path + ".index")
    vector_index.save(faiss_path)
    logger.info(f"FAISS已保存")
    
    # 阶段4: 文档存储
    doc_store = {}
    for c in all_chunks:
        doc_store[c.id] = c.to_dict()
    
    with open(os.path.join(vector_dir, "doc_store.json"), 'w', encoding='utf-8') as f:
        json.dump(doc_store, f, ensure_ascii=False)
    
    # 创建 VectorRetriever 兼容文件
    store_data = {"doc_store": doc_store, "id_list": doc_ids, "dimension": vectors.shape[1]}
    with open(os.path.join(vector_dir, "faiss_index.store.json"), 'w', encoding='utf-8') as f:
        json.dump(store_data, f, ensure_ascii=False)
    
    logger.info(f"doc_store已保存 ({len(doc_store)}个文档)")
    
    # 阶段5: BM25
    logger.info("=" * 60)
    logger.info("阶段4: BM25索引")
    logger.info("=" * 60)
    
    bm25_retriever = BM25Retriever(k1=1.5, b=0.75)
    bm25_retriever.add_documents(doc_ids, [doc_store[cid] for cid in doc_ids])
    bm25_retriever.save(os.path.join(vector_dir, "bm25_index"))
    logger.info(f"BM25已保存")
    
    logger.info("=" * 60)
    logger.info(f"全部完成! 共 {len(all_chunks)} 个chunk, 维度 {vectors.shape[1]}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
