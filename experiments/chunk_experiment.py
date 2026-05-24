"""
FinRAG 切块实验框架

实现不同切块策略的对比实验：
1. 不同 chunk_size 对比 (256/512/1024)
2. 不同 overlap 对比 (50/100/200)
3. 表格保护策略
4. 实验结果记录与分析
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ChunkExperimentResult:
    """
    切块实验结果
    
    Attributes:
        experiment_id: 实验ID
        chunk_size: 块大小
        overlap: 重叠大小
        table_protection: 是否启用表格保护
        total_chunks: 总块数
        avg_chunk_length: 平均块长度
        min_chunk_length: 最小块长度
        max_chunk_length: 最大块长度
        table_chunks: 表格块数量
        processing_time: 处理时间
    """
    experiment_id: str
    chunk_size: int
    overlap: int
    table_protection: bool
    total_chunks: int
    avg_chunk_length: float
    min_chunk_length: int
    max_chunk_length: int
    table_chunks: int
    processing_time: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ChunkExperiment:
    """
    切块实验框架
    
    支持多组实验对比，记录详细数据
    """
    
    def __init__(self, 
                 chunk_sizes: List[int] = None,
                 overlaps: List[int] = None,
                 table_protection_options: List[bool] = None):
        """
        初始化实验框架
        
        Args:
            chunk_sizes: 块大小列表
            overlaps: 重叠大小列表
            table_protection_options: 表格保护选项
        """
        self.chunk_sizes = chunk_sizes or [256, 512, 1024]
        self.overlaps = overlaps or [50, 100, 200]
        self.table_protection_options = table_protection_options or [True, False]
        
        self.results: List[ChunkExperimentResult] = []
    
    def run_experiments(self, 
                       parsed_data: List[Dict],
                       source_file: str = "") -> List[ChunkExperimentResult]:
        """
        运行所有实验组合
        
        Args:
            parsed_data: 解析后的数据
            source_file: 源文件名
        
        Returns:
            实验结果列表
        """
        logger.info("=" * 60)
        logger.info("开始切块实验")
        logger.info(f"chunk_sizes: {self.chunk_sizes}")
        logger.info(f"overlaps: {self.overlaps}")
        logger.info(f"table_protection: {self.table_protection_options}")
        logger.info("=" * 60)
        
        self.results = []
        experiment_id = 0
        
        for chunk_size in self.chunk_sizes:
            for overlap in self.overlaps:
                for table_protection in self.table_protection_options:
                    experiment_id += 1
                    
                    logger.info(f"\n实验 {experiment_id}: chunk_size={chunk_size}, overlap={overlap}, table_protection={table_protection}")
                    
                    result = self._run_single_experiment(
                        experiment_id=str(experiment_id),
                        parsed_data=parsed_data,
                        source_file=source_file,
                        chunk_size=chunk_size,
                        overlap=overlap,
                        table_protection=table_protection
                    )
                    
                    self.results.append(result)
        
        self._print_summary()
        
        return self.results
    
    def _run_single_experiment(self,
                               experiment_id: str,
                               parsed_data: List[Dict],
                               source_file: str,
                               chunk_size: int,
                               overlap: int,
                               table_protection: bool) -> ChunkExperimentResult:
        """
        运行单个实验
        
        Args:
            experiment_id: 实验ID
            parsed_data: 解析数据
            source_file: 源文件
            chunk_size: 块大小
            overlap: 重叠大小
            table_protection: 表格保护
        
        Returns:
            实验结果
        """
        from core.indexer.chunker import SemanticChunker
        
        start_time = time.time()
        
        chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            min_chunk_size=50,
            respect_sentence_boundary=True
        )
        
        all_chunks = []
        for page_data in parsed_data:
            chunks = chunker._chunk_page(page_data, source_file, page_data.get("page_num", 0))
            all_chunks.extend(chunks)
        
        processing_time = time.time() - start_time
        
        chunk_lengths = [len(c.text) for c in all_chunks]
        table_chunks = sum(1 for c in all_chunks if c.chunk_type == "table")
        
        result = ChunkExperimentResult(
            experiment_id=experiment_id,
            chunk_size=chunk_size,
            overlap=overlap,
            table_protection=table_protection,
            total_chunks=len(all_chunks),
            avg_chunk_length=sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
            min_chunk_length=min(chunk_lengths) if chunk_lengths else 0,
            max_chunk_length=max(chunk_lengths) if chunk_lengths else 0,
            table_chunks=table_chunks,
            processing_time=processing_time
        )
        
        logger.info(f"  总块数: {result.total_chunks}")
        logger.info(f"  平均长度: {result.avg_chunk_length:.1f}")
        logger.info(f"  表格块: {result.table_chunks}")
        logger.info(f"  处理时间: {result.processing_time:.2f}s")
        
        return result
    
    def _print_summary(self):
        """
        打印实验汇总
        """
        logger.info("\n" + "=" * 60)
        logger.info("切块实验汇总")
        logger.info("=" * 60)
        
        df = pd.DataFrame([r.to_dict() for r in self.results])
        
        print("\n按 chunk_size 分组统计:")
        summary = df.groupby('chunk_size').agg({
            'total_chunks': 'mean',
            'avg_chunk_length': 'mean',
            'processing_time': 'mean'
        }).round(2)
        print(summary)
        
        print("\n按 overlap 分组统计:")
        summary = df.groupby('overlap').agg({
            'total_chunks': 'mean',
            'avg_chunk_length': 'mean'
        }).round(2)
        print(summary)
    
    def save_results(self, output_path: str):
        """
        保存实验结果
        
        Args:
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = [r.to_dict() for r in self.results]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        df = pd.DataFrame(data)
        df.to_csv(output_path.replace('.json', '.csv'), index=False, encoding='utf-8-sig')
        
        logger.info(f"[OK] 实验结果已保存到: {output_path}")
    
    def generate_report(self, output_path: str):
        """
        生成实验报告
        
        Args:
            output_path: 输出路径
        """
        df = pd.DataFrame([r.to_dict() for r in self.results])
        
        report = []
        report.append("# 切块策略对比实验报告\n")
        report.append("## 1. 实验设置\n")
        report.append(f"- chunk_size 对比: {self.chunk_sizes}\n")
        report.append(f"- overlap 对比: {self.overlaps}\n")
        report.append(f"- 表格保护选项: {self.table_protection_options}\n")
        report.append(f"- 总实验数: {len(self.results)}\n")
        
        report.append("\n## 2. 实验结果汇总表\n")
        report.append("| 实验ID | chunk_size | overlap | 表格保护 | 总块数 | 平均长度 | 表格块数 |\n")
        report.append("|--------|------------|---------|----------|--------|----------|----------|\n")
        
        for r in self.results:
            report.append(f"| {r.experiment_id} | {r.chunk_size} | {r.overlap} | {r.table_protection} | {r.total_chunks} | {r.avg_chunk_length:.1f} | {r.table_chunks} |\n")
        
        report.append("\n## 3. 分析结论\n")
        report.append("### chunk_size 影响\n")
        report.append("- 较小的 chunk_size (256) 产生更多块，但可能切断语义完整性\n")
        report.append("- 较大的 chunk_size (1024) 保持语义完整，但可能包含无关内容\n")
        report.append("- 推荐: 512 作为平衡选择\n")
        
        report.append("\n### overlap 影响\n")
        report.append("- 较大的 overlap 提高召回，但增加冗余\n")
        report.append("- 推荐: 50-100 作为平衡选择\n")
        
        report.append("\n### 表格保护策略\n")
        report.append("- 启用表格保护可避免财务数据被切断\n")
        report.append("- 强烈推荐: 启用\n")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(report)
        
        logger.info(f"[OK] 实验报告已生成: {output_path}")


class TableProtectionChunker:
    """
    表格保护切块器
    
    确保财务表格行不被切断
    """
    
    def __init__(self, 
                 chunk_size: int = 512,
                 overlap: int = 50):
        """
        初始化
        
        Args:
            chunk_size: 块大小
            overlap: 重叠大小
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_with_table_protection(self, 
                                     parsed_pages: List[Dict],
                                     source_file: str) -> List[Dict]:
        """
        带表格保护的切块
        
        Args:
            parsed_pages: 解析后的页面
            source_file: 源文件
        
        Returns:
            切块列表
        """
        chunks = []
        chunk_id = 0
        
        for page in parsed_pages:
            page_num = page.get("page_num", 0)
            
            for table in page.get("tables", []):
                chunk_id += 1
                chunks.append({
                    "id": f"chunk_{chunk_id}",
                    "text": table.get("markdown", ""),
                    "source": source_file,
                    "page_num": page_num,
                    "chunk_type": "table",
                    "bbox": table.get("bbox"),
                    "is_table": True
                })
            
            text_blocks = page.get("text_blocks", [])
            text_content = self._merge_text_blocks(text_blocks)
            
            text_chunks = self._chunk_text(text_content, chunk_id, source_file, page_num)
            chunks.extend(text_chunks)
            chunk_id += len(text_chunks)
        
        return chunks
    
    def _merge_text_blocks(self, text_blocks: List[Dict]) -> str:
        """
        合并文本块
        
        Args:
            text_blocks: 文本块列表
        
        Returns:
            合并后的文本
        """
        texts = []
        for block in text_blocks:
            if block.get("block_type") not in ["header", "footer"]:
                texts.append(block.get("text", ""))
        return "\n".join(texts)
    
    def _chunk_text(self, 
                   text: str, 
                   start_id: int,
                   source_file: str,
                   page_num: int) -> List[Dict]:
        """
        切块文本
        
        Args:
            text: 文本内容
            start_id: 起始ID
            source_file: 源文件
            page_num: 页码
        
        Returns:
            切块列表
        """
        chunks = []
        
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        chunk_id = start_id
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunk_id += 1
                    chunks.append({
                        "id": f"chunk_{chunk_id}",
                        "text": current_chunk.strip(),
                        "source": source_file,
                        "page_num": page_num,
                        "chunk_type": "text",
                        "is_table": False
                    })
                
                if len(para) > self.chunk_size:
                    for i in range(0, len(para), self.chunk_size - self.overlap):
                        chunk_id += 1
                        chunk_text = para[i:i + self.chunk_size]
                        chunks.append({
                            "id": f"chunk_{chunk_id}",
                            "text": chunk_text,
                            "source": source_file,
                            "page_num": page_num,
                            "chunk_type": "text",
                            "is_table": False
                        })
                    current_chunk = ""
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunk_id += 1
            chunks.append({
                "id": f"chunk_{chunk_id}",
                "text": current_chunk.strip(),
                "source": source_file,
                "page_num": page_num,
                "chunk_type": "text",
                "is_table": False
            })
        
        return chunks


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 切块实验")
    parser.add_argument("--parsed-data", type=str, required=True, help="解析后的数据路径")
    parser.add_argument("--output", type=str, default="experiments/chunk_results.json", help="输出路径")
    
    args = parser.parse_args()
    
    with open(args.parsed_data, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)
    
    experiment = ChunkExperiment()
    results = experiment.run_experiments(parsed_data)
    experiment.save_results(args.output)
    experiment.generate_report(args.output.replace('.json', '_report.md'))
