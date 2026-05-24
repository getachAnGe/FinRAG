"""
FinRAG 数据入库脚本

一键完成：解析 -> 切片 -> 向量化 -> 入库
"""

import os
import sys
import json
import argparse
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def run_ingestion(pdf_dir: str,
                  output_dir: str,
                  config_path: str = None,
                  skip_parsing: bool = False,
                  skip_chunking: bool = False):
    """
    执行完整的数据入库流程
    
    Args:
        pdf_dir: PDF 文件目录
        output_dir: 输出目录
        config_path: 配置文件路径
        skip_parsing: 跳过解析步骤
        skip_chunking: 跳过切片步骤
    """
    from utils.file_helper import load_config, get_pdf_files, ensure_dir
    from core.parser.pdf_parser import FinRAGParser
    from core.indexer.chunker import SemanticChunker
    from core.indexer.embedder import Embedder, VectorIndex
    from core.retriever.vector_search import VectorRetriever
    from core.retriever.bm25_search import BM25Retriever
    
    config = {}
    if config_path and os.path.exists(config_path):
        config = load_config(config_path)
    
    parsed_dir = os.path.join(output_dir, "parsed")
    chunks_dir = os.path.join(output_dir, "chunks")
    vector_dir = os.path.join(output_dir, "vector_store")
    
    ensure_dir(parsed_dir)
    ensure_dir(chunks_dir)
    ensure_dir(vector_dir)
    
    pdf_files = get_pdf_files(pdf_dir)
    if not pdf_files:
        logger.error(f"未找到 PDF 文件: {pdf_dir}")
        return
    
    logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")
    
    all_parsed_data = []
    
    if not skip_parsing:
        logger.info("=" * 60)
        logger.info("阶段 1: PDF 解析")
        logger.info("=" * 60)
        
        parser_config = config.get("pdf_parser", {})
        parser = FinRAGParser(
            zoom_factor=parser_config.get("zoom_factor", 3),
            use_ocr=parser_config.get("use_ocr", True),
            use_gpu=parser_config.get("use_gpu", False),
            ocr_lang=parser_config.get("ocr_lang", "ch"),
            enable_garbled_detection=parser_config.get("enable_garbled_detection", True)
        )
        
        for pdf_file in pdf_files:
            logger.info(f"解析: {pdf_file}")
            
            try:
                parsed_pages = parser.parse(pdf_file)
                
                parsed_data = {
                    "source": os.path.basename(pdf_file),
                    "pages": []
                }
                
                for page in parsed_pages:
                    page_data = {
                        "page_num": page.page_num,
                        "text_blocks": [
                            {
                                "text": b.text,
                                "bbox": b.bbox,
                                "block_type": b.block_type,
                                "confidence": b.confidence
                            }
                            for b in page.text_blocks
                        ],
                        "tables": [
                            {
                                "data": t.data,
                                "markdown": t.markdown,
                                "bbox": t.bbox
                            }
                            for t in page.tables
                        ]
                    }
                    parsed_data["pages"].append(page_data)
                
                output_file = os.path.join(
                    parsed_dir, 
                    os.path.basename(pdf_file).replace(".pdf", ".json")
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                
                all_parsed_data.append(parsed_data)
                logger.info(f"[OK] 已保存: {output_file}")
                
            except Exception as e:
                logger.error(f"解析失败 {pdf_file}: {e}")
    else:
        logger.info("跳过解析步骤，加载已有解析结果...")
        
        for filename in os.listdir(parsed_dir):
            if filename.endswith(".json"):
                with open(os.path.join(parsed_dir, filename), 'r', encoding='utf-8') as f:
                    all_parsed_data.append(json.load(f))
    
    all_chunks = []
    
    if not skip_chunking:
        logger.info("=" * 60)
        logger.info("阶段 2: 文本切片")
        logger.info("=" * 60)
        
        chunker_config = config.get("indexer", {})
        chunker = SemanticChunker(
            chunk_size=chunker_config.get("chunk_size", 512),
            chunk_overlap=chunker_config.get("chunk_overlap", 50)
        )
        
        for parsed_data in all_parsed_data:
            source = parsed_data.get("source", "")
            logger.info(f"切片: {source}")
            
            chunks = chunker.chunk_parsed_document(parsed_data, source)
            all_chunks.extend(chunks)
        
        chunks_file = os.path.join(chunks_dir, "all_chunks.json")
        chunker.save_chunks(all_chunks, chunks_file)
        
        logger.info(f"[OK] 共生成 {len(all_chunks)} 个切片")
    else:
        logger.info("跳过切片步骤，加载已有切片...")
        
        chunks_file = os.path.join(chunks_dir, "all_chunks.json")
        if os.path.exists(chunks_file):
            all_chunks = SemanticChunker.load_chunks(chunks_file)
    
    logger.info("=" * 60)
    logger.info("阶段 3: 向量化与入库")
    logger.info("=" * 60)
    
    if not all_chunks:
        logger.error("没有切片数据，无法继续")
        return
    
    embedder_config = config.get("indexer", {})
    embedder = Embedder(
        model_name=embedder_config.get("embedding_model", "BAAI/bge-m3"),
        device=embedder_config.get("embedding_device", "cpu")
    )
    
    texts = [chunk.text for chunk in all_chunks]
    logger.info(f"向量化 {len(texts)} 个文本块...")
    
    vectors = embedder.encode(texts, show_progress=True)
    
    vector_index = VectorIndex(dimension=vectors.shape[1])
    doc_ids = [chunk.id for chunk in all_chunks]
    vector_index.add_vectors(vectors, doc_ids)
    
    vector_index.save(os.path.join(vector_dir, "faiss_index"))
    
    doc_store = {chunk.id: chunk.to_dict() for chunk in all_chunks}
    with open(os.path.join(vector_dir, "doc_store.json"), 'w', encoding='utf-8') as f:
        json.dump(doc_store, f, ensure_ascii=False)
    
    logger.info("[OK] 向量索引构建完成")
    
    logger.info("=" * 60)
    logger.info("阶段 4: BM25 索引构建")
    logger.info("=" * 60)
    
    bm25_retriever = BM25Retriever(
        k1=config.get("retriever", {}).get("bm25_k1", 1.5),
        b=config.get("retriever", {}).get("bm25_b", 0.75)
    )
    
    bm25_retriever.add_documents(doc_ids, [chunk.to_dict() for chunk in all_chunks])
    bm25_retriever.save(os.path.join(vector_dir, "bm25_index"))
    
    logger.info("[OK] BM25 索引构建完成")
    
    logger.info("=" * 60)
    logger.info("入库完成！")
    logger.info(f"  - 解析文件: {len(all_parsed_data)} 个")
    logger.info(f"  - 文本切片: {len(all_chunks)} 个")
    logger.info(f"  - 向量维度: {vectors.shape[1]}")
    logger.info("=" * 60)


def main():
    """
    命令行入口
    """
    parser = argparse.ArgumentParser(description="FinRAG 数据入库脚本")
    parser.add_argument("--pdf-dir", type=str, default="data/raw_pdf",
                       help="PDF 文件目录")
    parser.add_argument("--output-dir", type=str, default="data",
                       help="输出目录")
    parser.add_argument("--config", type=str, default="config/config.yaml",
                       help="配置文件路径")
    parser.add_argument("--skip-parsing", action="store_true",
                       help="跳过解析步骤")
    parser.add_argument("--skip-chunking", action="store_true",
                       help="跳过切片步骤")
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    pdf_dir = os.path.join(project_root, args.pdf_dir)
    output_dir = os.path.join(project_root, args.output_dir)
    config_path = os.path.join(project_root, args.config)
    
    run_ingestion(
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        config_path=config_path,
        skip_parsing=args.skip_parsing,
        skip_chunking=args.skip_chunking
    )


if __name__ == "__main__":
    main()
