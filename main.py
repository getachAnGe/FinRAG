"""
FinRAG - 金融领域智能问答系统

主入口文件
"""

import os
import sys
import argparse
import json
import logging

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def run_parse(args):
    """
    运行 PDF 解析
    """      
    from core.parser.pdf_parser import FinRAGParser
    from utils.file_helper import load_config
    
    config = {}
    if args.config:
        config = load_config(args.config)
    
    parser_config = config.get("pdf_parser", {})
    parser = FinRAGParser(
        zoom_factor=parser_config.get("zoom_factor", 3),
        use_ocr=parser_config.get("use_ocr", True),
        use_gpu=parser_config.get("use_gpu", False),
        ocr_lang=parser_config.get("ocr_lang", "ch"),
        enable_garbled_detection=parser_config.get("enable_garbled_detection", True)
    )
    
    results = parser.parse(args.pdf)
    
    if args.output:
        if args.output.endswith(".json"):
            parser.export_to_json(args.output)
        else:
            parser.export_to_markdown(args.output + ".md")
    
    print(f"\n[OK] 解析完成，共 {len(results)} 页")


def run_ingest(args):
    """
    运行数据入库
    """
    from scripts.run_ingestion import run_ingestion
    
    run_ingestion(
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        config_path=args.config,
        skip_parsing=args.skip_parsing,
        skip_chunking=args.skip_chunking
    )


def run_query(args):
    """
    运行问答
    """
    from utils.file_helper import load_config
    from sentence_transformers import SentenceTransformer
    from core.retriever.vector_search import VectorRetriever
    from core.retriever.bm25_search import BM25Retriever
    from core.retriever.reranker import Reranker
    from core.generator.llm_client import LLMClient
    from core.generator.chain import RAGChain
    
    config = load_config(args.config) if args.config else {}
    
    vector_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
    
    # 1. Embedder（用 SentenceTransformer 直接加载，避开 FlagEmbedding 的兼容性问题）
    embedder_config = config.get("embedding", {})
    model_name = embedder_config.get("model_name", "BAAI/bge-m3")
    print(f"[*] 加载 Embedding 模型: {model_name}")
    embedder_model = SentenceTransformer(model_name, device="cpu")
    embedder_dim = embedder_model.get_sentence_embedding_dimension()
    print(f"[OK] 向量维度: {embedder_dim}")
    
    # 封装 encode_single 供 RAGChain 使用
    class SimpleEmbedder:
        def __init__(self, model, dim):
            self.model = model
            self.dimension = dim
        def encode_single(self, text):
            return self.model.encode(text, convert_to_numpy=True)
        def encode(self, texts, **kwargs):
            return self.model.encode(texts, convert_to_numpy=True)
    
    embedder = SimpleEmbedder(embedder_model, embedder_dim)
    
    # 2. 向量检索
    vector_retriever = VectorRetriever(dimension=embedder_dim)
    vector_index_path = os.path.join(vector_dir, "faiss_index")
    if os.path.exists(vector_index_path + ".index"):
        vector_retriever.load(vector_index_path)
        
        doc_store_path = os.path.join(vector_dir, "doc_store.json")
        if os.path.exists(doc_store_path):
            with open(doc_store_path, 'r', encoding='utf-8') as f:
                doc_store = json.load(f)
            vector_retriever.doc_store = doc_store
    
    # 3. BM25 检索
    bm25_retriever = BM25Retriever()
    bm25_index_path = os.path.join(vector_dir, "bm25_index")
    if os.path.exists(bm25_index_path + ".bm25.json"):
        bm25_retriever.load(bm25_index_path)
    
    # 4. Reranker（按配置启用：bge-reranker-base + GPU）
    reranker_config = config.get("reranker", {})
    import torch
    reranker_device = "cuda" if torch.cuda.is_available() else "cpu"
    reranker = Reranker(
        model_name=reranker_config.get("model_name", "models/reranker/BAAI/bge-reranker-base"),
        device=reranker_device
    )
    print(f"[*] Reranker: {reranker_config.get('model_name', 'bge-reranker-base')} ({reranker_device})")
    
    # 5. LLM 客户端
    generator_config = config.get("generator", {})
    llm_client = None
    api_key = generator_config.get("llm_api_key") or os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        llm_client = LLMClient(
            model_name=generator_config.get("llm_model", "deepseek-chat"),
            api_base=generator_config.get("llm_api_base", "https://api.deepseek.com/v1"),
            api_key=api_key,
            temperature=generator_config.get("temperature", 0.1)
        )
    
    # 6. RAG 链
    rag_chain = RAGChain(
        embedder=embedder,
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        reranker=reranker,
        llm_client=llm_client,
        config_path=args.config
    )
    
    if args.interactive:
        print("\n" + "=" * 60)
        print("FinRAG 金融智能问答系统")
        print("输入 'quit' 或 'exit' 退出")
        print("=" * 60 + "\n")
        
        while True:
            try:
                question = input("\n请输入问题: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("再见！")
                    break
                
                if not question:
                    continue
                
                result = rag_chain.run(question)
                
                print("\n" + "-" * 40)
                print("回答:")
                print(result.answer)
                
                if result.sources:
                    print("\n引用来源:")
                    for i, source in enumerate(result.sources, 1):
                        print(f"  [{i}] {source.get('source')} - 第 {source.get('page_num')} 页")
                
                print("-" * 40)
                
            except KeyboardInterrupt:
                print("\n再见！")
                break
    else:
        if args.question:
            result = rag_chain.run(args.question)
            print("\n" + "=" * 60)
            print("问题:", args.question)
            print("=" * 60)
            print("\n回答:")
            print(result.answer)
            
            if result.sources:
                print("\n引用来源:")
                for i, source in enumerate(result.sources, 1):
                    print(f"  [{i}] {source.get('source')} - 第 {source.get('page_num')} 页")
        else:
            print("请使用 --question 指定问题，或使用 --interactive 进入交互模式")


def run_webui(args):
    """
    启动 Web UI
    """
    import subprocess
    
    webui_path = os.path.join(PROJECT_ROOT, "webui", "app.py")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        webui_path,
        "--server.port", str(args.port)
    ]
    
    if args.host:
        cmd.extend(["--server.address", args.host])
    
    subprocess.run(cmd)


def main():
    """
    主入口
    """
    parser = argparse.ArgumentParser(
        description="FinRAG - 金融领域智能问答系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 解析 PDF 文件
  python main.py parse --pdf data/raw_pdf/report.pdf --output data/parsed/report.json
  
  # 数据入库
  python main.py ingest --pdf-dir data/raw_pdf --output-dir data
  
  # 问答 (交互模式)
  python main.py query --interactive
  
  # 问答 (单次)
  python main.py query --question "公司的营业收入是多少？"
  
  # 启动 Web UI
  python main.py webui --port 8501
        """
    )
    
    parser.add_argument("--config", type=str, default="config/config.yaml",
                       help="配置文件路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    parse_parser = subparsers.add_parser("parse", help="解析 PDF 文件")
    parse_parser.add_argument("--pdf", type=str, required=True,
                             help="PDF 文件路径")
    parse_parser.add_argument("--output", type=str,
                             help="输出文件路径")
    
    ingest_parser = subparsers.add_parser("ingest", help="数据入库")
    ingest_parser.add_argument("--pdf-dir", type=str, default="data/raw_pdf",
                              help="PDF 文件目录")
    ingest_parser.add_argument("--output-dir", type=str, default="data",
                              help="输出目录")
    ingest_parser.add_argument("--skip-parsing", action="store_true",
                              help="跳过解析步骤")
    ingest_parser.add_argument("--skip-chunking", action="store_true",
                              help="跳过切片步骤")
    
    query_parser = subparsers.add_parser("query", help="问答")
    query_parser.add_argument("--question", type=str,
                             help="问题")
    query_parser.add_argument("--interactive", action="store_true",
                             help="交互模式")
    
    webui_parser = subparsers.add_parser("webui", help="启动 Web UI")
    webui_parser.add_argument("--host", type=str, default="localhost",
                             help="服务器地址")
    webui_parser.add_argument("--port", type=int, default=8501,
                             help="服务器端口")
    
    args = parser.parse_args()
    
    if args.command == "parse":
        run_parse(args)
    elif args.command == "ingest":
        run_ingest(args)
    elif args.command == "query":
        run_query(args)
    elif args.command == "webui":
        run_webui(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
