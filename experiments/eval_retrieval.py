"""
FinRAG 检索效果评测模块

评估指标：
1. Recall@K
2. MRR (Mean Reciprocal Rank)
3. NDCG (Normalized Discounted Cumulative Gain)
"""

import os
import json
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    """
    检索效果评测器
    """
    
    def __init__(self):
        """
        初始化评测器
        """
        self.results = []
    
    def evaluate(self,
                queries: List[str],
                ground_truth: List[List[str]],
                retriever,
                top_k: int = 10) -> Dict:
        """
        评测检索效果
        
        Args:
            queries: 查询列表
            ground_truth: 每个查询的相关文档 ID 列表
            retriever: 检索器
            top_k: 检索数量
        
        Returns:
            评测结果
        """
        recall_scores = []
        mrr_scores = []
        ndcg_scores = []
        
        for query, relevant_docs in zip(queries, ground_truth):
            results = retriever.search(query, top_k=top_k)
            retrieved_ids = [r.get("id") for r in results]
            
            recall = self._calculate_recall(retrieved_ids, relevant_docs)
            recall_scores.append(recall)
            
            mrr = self._calculate_mrr(retrieved_ids, relevant_docs)
            mrr_scores.append(mrr)
            
            ndcg = self._calculate_ndcg(retrieved_ids, relevant_docs)
            ndcg_scores.append(ndcg)
        
        return {
            "recall@k": sum(recall_scores) / len(recall_scores),
            "mrr": sum(mrr_scores) / len(mrr_scores),
            "ndcg": sum(ndcg_scores) / len(ndcg_scores),
            "num_queries": len(queries)
        }
    
    def _calculate_recall(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        计算 Recall@K
        
        Args:
            retrieved: 检索结果 ID 列表
            relevant: 相关文档 ID 列表
        
        Returns:
            Recall 值
        """
        if not relevant:
            return 0.0
        
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        
        return len(retrieved_set & relevant_set) / len(relevant_set)
    
    def _calculate_mrr(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        计算 MRR (Mean Reciprocal Rank)
        
        Args:
            retrieved: 检索结果 ID 列表
            relevant: 相关文档 ID 列表
        
        Returns:
            MRR 值
        """
        relevant_set = set(relevant)
        
        for rank, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0 / rank
        
        return 0.0
    
    def _calculate_ndcg(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        计算 NDCG (Normalized Discounted Cumulative Gain)
        
        Args:
            retrieved: 检索结果 ID 列表
            relevant: 相关文档 ID 列表
        
        Returns:
            NDCG 值
        """
        import math
        
        relevant_set = set(relevant)
        
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                dcg += 1.0 / math.log2(rank + 1)
        
        ideal_dcg = 0.0
        for rank in range(1, min(len(relevant), len(retrieved)) + 1):
            ideal_dcg += 1.0 / math.log2(rank + 1)
        
        if ideal_dcg == 0:
            return 0.0
        
        return dcg / ideal_dcg
    
    def compare_methods(self,
                       queries: List[str],
                       ground_truth: List[List[str]],
                       methods: Dict[str, Any],
                       top_k: int = 10) -> Dict:
        """
        比较不同检索方法
        
        Args:
            queries: 查询列表
            ground_truth: 相关文档列表
            methods: 方法名称到检索器的映射
            top_k: 检索数量
        
        Returns:
            比较结果
        """
        comparison = {}
        
        for method_name, retriever in methods.items():
            logger.info(f"评测方法: {method_name}")
            result = self.evaluate(queries, ground_truth, retriever, top_k)
            comparison[method_name] = result
        
        return comparison
    
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
        
        logger.info(f"[OK] 评测结果已保存到: {output_path}")


def run_evaluation(test_data_path: str, output_path: str):
    """
    运行评测
    
    Args:
        test_data_path: 测试数据路径
        output_path: 输出路径
    """
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    queries = test_data.get("queries", [])
    ground_truth = test_data.get("ground_truth", [])
    
    evaluator = RetrievalEvaluator()
    
    print("[!] 请在完整系统中配置检索器后运行评测")
    print(f"    测试查询数: {len(queries)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 检索评测")
    parser.add_argument("--test-data", type=str, required=True,
                       help="测试数据路径")
    parser.add_argument("--output", type=str, default="experiments/results.json",
                       help="输出路径")
    
    args = parser.parse_args()
    
    run_evaluation(args.test_data, args.output)
