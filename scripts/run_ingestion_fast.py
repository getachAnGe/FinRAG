"""
FinRAG 数据入库脚本 - 改进版
特性: 断点续传 + 多进程并发 + 数量限制 + 进度可视化
"""

import os
import sys
import json
import time
from typing import List, Dict, Set
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def parse_one_pdf(args_tuple):
    """
    解析单个 PDF (独立函数，用于多进程)
    """
    pdf_path, parsed_dir = args_tuple

    from core.parser.pdf_parser import FinRAGParser

    parser = FinRAGParser(
        zoom_factor=3,
        use_ocr=True,
        use_gpu=False,
        ocr_lang="ch",
        enable_garbled_detection=True
    )

    try:
        parsed_pages = parser.parse(pdf_path)

        parsed_data = {
            "source": os.path.basename(pdf_path),
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
            os.path.basename(pdf_path).replace(".pdf", ".json")
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        return (True, pdf_path, len(parsed_pages), output_file, None)

    except Exception as e:
        return (False, pdf_path, 0, None, str(e))


def run_ingestion(pdf_dir: str,
                  output_dir: str,
                  max_files: int = 300,
                  workers: int = 4):
    """
    执行完整的数据入库流程 (改进版)

    Args:
        pdf_dir: PDF 文件目录
        output_dir: 输出目录
        max_files: 最多处理文件数
        workers: 并发进程数
    """
    from utils.file_helper import get_pdf_files, ensure_dir

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

    pdf_files = pdf_files[:max_files]
    logger.info(f"目标: 处理前 {len(pdf_files)} 个 PDF 文件")

    already_parsed = set()
    for fname in os.listdir(parsed_dir):
        if fname.endswith(".json"):
            already_parsed.add(fname.replace(".json", ".pdf"))

    pending_files = [f for f in pdf_files if os.path.basename(f) not in already_parsed]
    logger.info(f"已解析: {len(already_parsed)} 个")
    logger.info(f"待处理: {len(pending_files)} 个")

    if not pending_files:
        logger.info("所有文件已解析完毕，跳过解析阶段")
    else:
        logger.info("=" * 60)
        logger.info(f"阶段 1: PDF 解析 ({workers} 进程并发)")
        logger.info("=" * 60)

        tasks = [(f, parsed_dir) for f in pending_files]
        t0 = time.time()
        done = 0
        failed = 0

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(parse_one_pdf, task): task[0] for task in tasks}

            for future in as_completed(futures):
                success, path, pages, outfile, err = future.result()
                done += 1
                name = os.path.basename(path)

                if success:
                    logger.info(f"[{done}/{len(pending_files)}] OK  {name} ({pages}页)")
                else:
                    failed += 1
                    logger.warning(f"[{done}/{len(pending_files)}] FAIL  {name}: {err}")

        elapsed = time.time() - t0
        logger.info(f"[OK] 解析完成! 成功 {done - failed}, 失败 {failed}, 耗时 {elapsed:.1f}s")

    all_parsed_data = []
    for filename in os.listdir(parsed_dir):
        if filename.endswith(".json"):
            with open(os.path.join(parsed_dir, filename), 'r', encoding='utf-8') as f:
                all_parsed_data.append(json.load(f))

    logger.info("=" * 60)
    logger.info("阶段 2: 文本切片")
    logger.info("=" * 60)

    from core.indexer.chunker import SemanticChunker

    chunker = SemanticChunker(chunk_size=512, chunk_overlap=50)
    all_chunks = []

    for parsed_data in all_parsed_data:
        source = parsed_data.get("source", "")
        chunks = chunker.chunk_parsed_document(parsed_data, source)
        all_chunks.extend(chunks)

    chunks_file = os.path.join(chunks_dir, "all_chunks.json")
    chunker.save_chunks(all_chunks, chunks_file)
    logger.info(f"[OK] 共生成 {len(all_chunks)} 个切片")

    logger.info("=" * 60)
    logger.info("阶段 3: 向量化与入库")
    logger.info("=" * 60)

    from core.indexer.embedder import Embedder, VectorIndex

    from utils.file_helper import load_config

    config = load_config('config/config.yaml')
    model_name = config.get('embedding', {}).get('model_name', 'BAAI/bge-m3')
    
    embedder = Embedder(
        model_name=model_name,
        device='cpu'
    )

    texts = [chunk.text for chunk in all_chunks]
    logger.info(f"向量化 {len(texts)} 个文本块...")
    vectors = embedder.encode(texts, show_progress=True)

    ensure_dir(vector_dir)

    vector_index = VectorIndex(dimension=vectors.shape[1])
    doc_ids = [chunk.id for chunk in all_chunks]
    vector_index.add_vectors(vectors, doc_ids)

    faiss_path = os.path.join(vector_dir, "faiss_index")
    faiss_index_file = faiss_path + ".index"
    if os.path.exists(faiss_index_file):
        os.remove(faiss_index_file)
    vector_index.save(faiss_path)
    logger.info(f"[OK] FAISS 索引已保存: {faiss_index_file}")

    doc_store = {chunk.id: chunk.to_dict() for chunk in all_chunks}
    doc_store_path = os.path.join(vector_dir, "doc_store.json")
    with open(doc_store_path, 'w', encoding='utf-8') as f:
        json.dump(doc_store, f, ensure_ascii=False)

    logger.info("[OK] 向量索引构建完成")

    logger.info("=" * 60)
    logger.info("阶段 4: BM25 索引构建")
    logger.info("=" * 60)

    from core.retriever.bm25_search import BM25Retriever

    bm25_retriever = BM25Retriever(k1=1.5, b=0.75)
    bm25_retriever.add_documents(doc_ids, [chunk.to_dict() for chunk in all_chunks])
    bm25_path = os.path.join(vector_dir, "bm25_index")
    bm25_retriever.save(bm25_path)

    logger.info("[OK] BM25 索引构建完成")

    logger.info("=" * 60)
    logger.info("入库完成！")
    logger.info(f"  - 解析文件: {len(all_parsed_data)} 个")
    logger.info(f"  - 文本切片: {len(all_chunks)} 个")
    logger.info(f"  - 向量维度: {vectors.shape[1]}")
    logger.info("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FinRAG 数据入库 (并发版)")
    parser.add_argument("--pdf-dir", type=str, default="data/raw_pdf")
    parser.add_argument("--output-dir", type=str, default="data")
    parser.add_argument("--max-files", type=int, default=300)
    parser.add_argument("--workers", type=int, default=4)

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_dir = os.path.join(project_root, args.pdf_dir)
    output_dir = os.path.join(project_root, args.output_dir)

    run_ingestion(
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        max_files=args.max_files,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
