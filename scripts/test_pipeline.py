"""
测试：用10条数据跑通完整流程
切块 → 向量化 → FAISS保存 → BM25保存 → 检索验证
"""
import os, sys, json, time, logging, shutil, tempfile
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from utils.file_helper import ensure_dir

parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed")
test_dir = os.path.join(PROJECT_ROOT, "data", "test_pipeline")
ensure_dir(test_dir)

# 选10个不同的文件
files = sorted([f for f in os.listdir(parsed_dir) if f.endswith('.json') and not f.startswith('H3')])[:10]
logger.info(f"选取 {len(files)} 个文件")

all_chunks = []
for i, fname in enumerate(files):
    with open(os.path.join(parsed_dir, fname), 'r', encoding='utf-8') as f:
        data = json.load(f)
    source = data.get('source', fname)
    
    for page in data.get('pages', []):
        pn = page.get('page_num', 0)
        texts = []
        for b in page.get('text_blocks', []):
            t = b.get('text', '').strip()
            if t:
                texts.append(t)
        for t in page.get('tables', []):
            md = t.get('markdown', '')
            if md:
                texts.append(md)
        
        full = '\n'.join(texts)
        if not full.strip():
            continue
        
        # 每页切成多个512字符的chunk
        chunk_size = 512
        overlap = 50
        start = 0
        while start < len(full):
            end = min(start + chunk_size, len(full))
            chunk_text = full[start:end].strip()
            if chunk_text:
                cid = f"test_chunk_{len(all_chunks)+1}"
                all_chunks.append({
                    'id': cid,
                    'text': chunk_text,
                    'source': source,
                    'page_num': pn,
                })
            start = end - overlap if end < len(full) else len(full)

logger.info(f"共生成 {len(all_chunks)} 个chunk")

# 向量化
logger.info("加载 sentence-transformers 模型...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-base-zh-v1.5', device='cpu')
dim = model.get_sentence_embedding_dimension()
logger.info(f"模型加载完成, 维度: {dim}")

texts = [c['text'] for c in all_chunks]
doc_ids = [c['id'] for c in all_chunks]

logger.info(f"向量化 {len(texts)} 个文本块...")
t0 = time.time()
embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True, batch_size=32)
import numpy as np
vectors = np.array(embeddings)
logger.info(f"向量化完成: {vectors.shape}, 耗时 {time.time()-t0:.1f}s")

# FAISS保存（用系统临时目录）
logger.info("保存 FAISS 索引...")
import faiss
index = faiss.IndexFlatIP(dim)
index.add(vectors)

faiss_file = os.path.join(test_dir, "faiss_index.index")
tmp_file = os.path.join(tempfile.gettempdir(), "test_faiss_tmp.index")
faiss.write_index(index, tmp_file)
shutil.move(tmp_file, faiss_file)
logger.info(f"FAISS 已保存 ({os.path.getsize(faiss_file)/1024:.1f}KB)")

# doc_store
doc_store = {c['id']: c for c in all_chunks}
with open(os.path.join(test_dir, "doc_store.json"), 'w', encoding='utf-8') as f:
    json.dump(doc_store, f, ensure_ascii=False)
logger.info("doc_store 已保存")

# BM25
logger.info("构建 BM25 索引...")
sys.path.insert(0, PROJECT_ROOT)
from core.retriever.bm25_search import BM25Retriever
bm25 = BM25Retriever(k1=1.5, b=0.75)
bm25.add_documents(doc_ids, [doc_store[cid] for cid in doc_ids])
bm25.save(os.path.join(test_dir, "bm25_index"))
logger.info("BM25 已保存")

# 验证检索
logger.info("\n" + "=" * 50)
logger.info("验证检索效果")
logger.info("=" * 50)

test_queries = [
    "格力电器的营业收入是多少？",
    "伊利股份的净利润是多少？",
    "紫光国微的研发投入是多少？",
]

for q in test_queries:
    q_vec = model.encode([q], normalize_embeddings=True)
    scores, indices = index.search(np.array(q_vec), 3)
    logger.info(f"\n问题: {q}")
    for rank, idx in enumerate(indices[0]):
        if idx < len(all_chunks):
            chunk = all_chunks[idx]
            logger.info(f"  Top{rank+1}: {chunk['source']} p{chunk['page_num']} score={scores[0][rank]:.4f}")
            logger.info(f"    {chunk['text'][:80]}")

logger.info(f"\n{'='*50}")
logger.info(f"测试通过！全部文件已保存到: {test_dir}")
logger.info(f"{'='*50}")
