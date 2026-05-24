"""用精准评测集跑RAG评测"""
import os, sys, json, re, logging
logging.basicConfig(level=logging.ERROR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from core.retriever.reranker import Reranker
from core.generator.llm_client import LLMClient
from core.generator.chain import RAGChain
from utils.file_helper import load_config

config = load_config("config/config.yaml")
embedder = Embedder(model_name=config.get("embedding",{}).get("model_name"), device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

reranker_cfg = config.get("reranker", {})
reranker = Reranker(
    model_name=reranker_cfg.get("model_name", "BAAI/bge-reranker-v2-m3"),
    device=reranker_cfg.get("device", "cpu")
)

gen_cfg = config.get("generator", {})
api_key = os.getenv("DEEPSEEK_API_KEY", gen_cfg.get("llm_api_key"))
llm_client = LLMClient(model_name=gen_cfg.get("llm_model","deepseek-chat"),
    api_base=gen_cfg.get("llm_api_base"), api_key=api_key, temperature=0.01) if api_key else None

rag_chain = RAGChain(embedder=embedder, vector_retriever=vector_retriever,
    bm25_retriever=bm25_retriever, reranker=reranker, llm_client=llm_client,
    config_path="config/config.yaml")

with open("data/eval/eval_dataset_manual.json", 'r', encoding='utf-8') as f:
    dataset = json.load(f)
samples = dataset['samples']

print("=" * 60)
print("精准评测集 RAG 评测")
print("=" * 60)

# 指标1: 检索命中率（chunk_id精确匹配）
chunk_hit = 0
page_hit = 0
total = 0

for s in samples:
    if s['query_type'] != 'fact':
        continue
    total += 1
    q = s['query']
    target_chunk = s.get('ground_truth_chunk_id', '')
    target_src = s.get('source_file', '')
    target_page = s.get('page_num', '')
    
    qv = rag_chain._encode_question(q)
    combined = []
    seen = set()
    top_k = config.get("retriever", {}).get("top_k", 100)
    for r in (vector_retriever.search(qv, top_k=top_k) if qv is not None else []) + bm25_retriever.search(q, top_k=top_k):
        rid = r.get("id","")
        if rid not in seen:
            seen.add(rid)
            doc = r.get("document",{})
            if isinstance(doc, dict):
                r["src"] = doc.get("source","")
                r["pg"] = doc.get("page_num","")
            combined.append(r)
    
    # 检查是否命中
    retrieved_ids = [r.get("id","") for r in combined]
    if target_chunk in retrieved_ids:
        chunk_hit += 1
    elif any(r.get("src","") == target_src and str(r.get("pg","")) == str(target_page) for r in combined):
        page_hit += 1

print(f"\n事实型问题: {total}条")
print(f"  chunk精确命中: {chunk_hit}/{total} = {chunk_hit/total*100:.1f}%")
print(f"  同页面命中(未精确匹配chunk): {page_hit}/{total} = {page_hit/total*100:.1f}%")
print(f"  总计检索命中: {(chunk_hit+page_hit)}/{total} = {(chunk_hit+page_hit)/total*100:.1f}%")
print(f"  完全未命中: {total-chunk_hit-page_hit}/{total}")

# 指标2: 回答准确率（取前20条看DeepSeek能否给出正确数字）
print("\n" + "=" * 60)
print("回答准确率（前20条事实型）")
print("=" * 60)

correct = 0
wrong = 0
for s in samples[:20]:
    if s['query_type'] != 'fact':
        continue
    q = s['query']
    expected_answer = s['ground_truth_answer']
    
    result = rag_chain.run(q)
    actual = result.answer
    
    # 从回答中提取数字
    expected_num = re.findall(r'[\d,.]+\s*(?:亿元|万元|元|%)?', expected_answer)
    actual_num = re.findall(r'[\d,.]+\s*(?:亿元|万元|元|%)?', actual)
    
    # 简化比较：看核心数字是否一致
    def simplify(n):
        return n.replace(',', '').replace(' ', '')
    
    match = any(simplify(e) == simplify(a) for e in expected_num for a in actual_num if len(e) > 3)
    
    status = "✅" if match else "❌"
    if match:
        correct += 1
    else:
        wrong += 1
    
    print(f"\n{status} {q[:50]}...")
    print(f"  期望: {expected_answer}")
    print(f"  回答: {actual[:100]}...")

print(f"\n准确率: {correct}/{correct+wrong} = {correct/(correct+wrong)*100:.1f}%")
