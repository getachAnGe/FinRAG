"""手动抽查回答质量"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer.embedder import Embedder
from core.retriever.vector_search import VectorRetriever
from core.retriever.bm25_search import BM25Retriever
from core.generator.llm_client import LLMClient
from core.generator.chain import RAGChain
from utils.file_helper import load_config
import logging
logging.basicConfig(level=logging.ERROR)

config = load_config("config/config.yaml")
embedder = Embedder(model_name=config.get("embedding",{}).get("model_name"), device="cpu")
vector_dir = "data/vector_store"

vector_retriever = VectorRetriever(dimension=embedder.dimension)
vector_retriever.load(os.path.join(vector_dir, "faiss_index"))
with open(os.path.join(vector_dir, "doc_store.json"), 'r', encoding='utf-8') as f:
    vector_retriever.doc_store = json.load(f)

bm25_retriever = BM25Retriever()
bm25_retriever.load(os.path.join(vector_dir, "bm25_index"))

gen_cfg = config.get("generator", {})
api_key = os.getenv("DEEPSEEK_API_KEY", gen_cfg.get("llm_api_key"))
llm_client = LLMClient(model_name=gen_cfg.get("llm_model","deepseek-chat"),
    api_base=gen_cfg.get("llm_api_base"), api_key=api_key, temperature=0.01) if api_key else None

rag_chain = RAGChain(embedder=embedder, vector_retriever=vector_retriever,
    bm25_retriever=bm25_retriever, reranker=None, llm_client=llm_client,
    config_path="config/config.yaml")

test_questions = [
    "格力电器的营业收入是多少？",
    "格力电器的净利润是多少？",
    "格力电器的总资产是多少？",
    "伊利股份的营业收入是多少？",
    "泸州老窖的净利润是多少？",
]

for q in test_questions:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print(f"{'='*60}")
    result = rag_chain.run(q)
    print(f"A: {result.answer[:300]}")
    print(f"  引用来源: {len(result.sources)} 个")
    for s in result.sources[:2]:
        print(f"    - {s.get('source','?')} p{s.get('page_num','?')} id:{s.get('id','?')[:20]}...")
