"""
FinRAG 解析准确度测试模块

对比不同解析策略的效果
"""

import os
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ParsingEvaluator:
    """
    解析效果评测器
    
    评测维度：
    1. 文本提取完整度
    2. 表格识别准确率
    3. 版面分析准确率
    """
    
    def __init__(self):
        """
        初始化评测器
        """
        pass
    
    def evaluate_text_extraction(self,
                                 extracted_text: str,
                                 ground_truth_text: str) -> Dict:
        """
        评估文本提取效果
        
        Args:
            extracted_text: 提取的文本
            ground_truth_text: 标准文本
        
        Returns:
            评测结果
        """
        extracted_words = set(extracted_text.lower().split())
        truth_words = set(ground_truth_text.lower().split())
        
        if not truth_words:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        true_positives = len(extracted_words & truth_words)
        
        precision = true_positives / len(extracted_words) if extracted_words else 0.0
        recall = true_positives / len(truth_words)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
    
    def evaluate_table_extraction(self,
                                  extracted_tables: List[List[List[str]]],
                                  ground_truth_tables: List[List[List[str]]]) -> Dict:
        """
        评估表格提取效果
        
        Args:
            extracted_tables: 提取的表格列表
            ground_truth_tables: 标准表格列表
        
        Returns:
            评测结果
        """
        if not ground_truth_tables:
            return {"table_recall": 1.0 if not extracted_tables else 0.0}
        
        matched_tables = 0
        for gt_table in ground_truth_tables:
            for ext_table in extracted_tables:
                if self._compare_tables(ext_table, gt_table) > 0.8:
                    matched_tables += 1
                    break
        
        table_recall = matched_tables / len(ground_truth_tables)
        
        return {
            "table_recall": table_recall,
            "extracted_count": len(extracted_tables),
            "ground_truth_count": len(ground_truth_tables)
        }
    
    def _compare_tables(self, table1: List[List[str]], table2: List[List[str]]) -> float:
        """
        比较两个表格的相似度
        
        Args:
            table1: 表格1
            table2: 表格2
        
        Returns:
            相似度 [0, 1]
        """
        if not table1 or not table2:
            return 0.0
        
        cells1 = set()
        for row in table1:
            for cell in row:
                cells1.add(str(cell).strip().lower())
        
        cells2 = set()
        for row in table2:
            for cell in row:
                cells2.add(str(cell).strip().lower())
        
        if not cells1 or not cells2:
            return 0.0
        
        intersection = cells1 & cells2
        union = cells1 | cells2
        
        return len(intersection) / len(union)
    
    def compare_parsing_methods(self,
                                pdf_path: str,
                                ground_truth: Dict,
                                parsers: Dict[str, Any]) -> Dict:
        """
        比较不同解析方法
        
        Args:
            pdf_path: PDF 文件路径
            ground_truth: 标准答案
            parsers: 解析器字典
        
        Returns:
            比较结果
        """
        results = {}
        
        for parser_name, parser in parsers.items():
            logger.info(f"评测解析器: {parser_name}")
            
            parsed_data = parser.parse(pdf_path)
            
            extracted_text = ""
            for page in parsed_data:
                for block in page.text_blocks:
                    extracted_text += block.text + " "
            
            text_result = self.evaluate_text_extraction(
                extracted_text,
                ground_truth.get("text", "")
            )
            
            extracted_tables = []
            for page in parsed_data:
                for table in page.tables:
                    extracted_tables.append(table.data)
            
            table_result = self.evaluate_table_extraction(
                extracted_tables,
                ground_truth.get("tables", [])
            )
            
            results[parser_name] = {
                "text_extraction": text_result,
                "table_extraction": table_result
            }
        
        return results
    
    def save_results(self, results: Dict, output_path: str):
        """
        保存评测结果
        
        Args:
            results: 评测结果
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[OK] 解析评测结果已保存到: {output_path}")


def run_parsing_test(pdf_path: str, ground_truth_path: str, output_path: str):
    """
    运行解析测试
    
    Args:
        pdf_path: PDF 文件路径
        ground_truth_path: 标准答案路径
        output_path: 输出路径
    """
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    evaluator = ParsingEvaluator()
    
    print("[!] 请在完整系统中配置解析器后运行评测")
    print(f"    PDF 文件: {pdf_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 解析评测")
    parser.add_argument("--pdf", type=str, required=True,
                       help="PDF 文件路径")
    parser.add_argument("--ground-truth", type=str, required=True,
                       help="标准答案路径")
    parser.add_argument("--output", type=str, default="experiments/parsing_results.json",
                       help="输出路径")
    
    args = parser.parse_args()
    
    run_parsing_test(args.pdf, args.ground_truth, args.output)
