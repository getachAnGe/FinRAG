"""
FinRAG 评测集构建模块

构建金融场景专属评测集：
1. 事实型问题 - 如 "比亚迪 Q3 营收多少？"
2. 对比型问题 - 如 "宁德时代 vs 比亚迪毛利率哪个高？"
3. 汇总型问题 - 如 "新能源行业 2025 年主要政策变化？"

格式: (query, ground_truth_doc_id, answer)
"""

import os
import json
import random
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class EvalSample:
    """
    评测样本
    
    Attributes:
        query_id: 问题ID
        query: 问题文本
        query_type: 问题类型 (fact/comparison/summary)
        ground_truth_doc_ids: 相关文档ID列表
        ground_truth_answer: 标准答案
        difficulty: 难度 (easy/medium/hard)
        keywords: 关键词列表
    """
    query_id: str
    query: str
    query_type: str
    ground_truth_doc_ids: List[str]
    ground_truth_answer: str
    difficulty: str = "medium"
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EvalDatasetBuilder:
    """
    评测集构建器
    """
    
    FINANCE_TEMPLATES = {
        "fact": [
            "{company} {year}年{quarter}营收是多少？",
            "{company}的{metric}是多少？",
            "{company} {year}年净利润是多少？",
            "{company}的毛利率是多少？",
            "{company}的ROE是多少？",
            "{company}的资产负债率是多少？",
            "{company} {year}年研发投入是多少？",
            "{company}的市盈率是多少？",
            "{company}的每股收益是多少？",
            "{company}的营业收入同比增长率是多少？"
        ],
        "comparison": [
            "{company1}和{company2}的{metric}哪个更高？",
            "{company1}与{company2}的营收规模对比如何？",
            "{company1}和{company2}哪个毛利率更高？",
            "{company1}与{company2}的净利润率对比？",
            "{company1}和{company2}的研发投入占比谁更高？"
        ],
        "summary": [
            "{industry}行业{year}年主要政策变化有哪些？",
            "{industry}行业的发展趋势如何？",
            "{industry}行业面临的主要风险是什么？",
            "{industry}行业的竞争格局如何？",
            "{industry}行业的市场规模有多大？"
        ]
    }
    
    COMPANIES = [
        "比亚迪", "宁德时代", "隆基绿能", "阳光电源", "通威股份",
        "中芯国际", "韦尔股份", "兆易创新", "北方华创", "紫光国微",
        "贵州茅台", "五粮液", "海天味业", "伊利股份", "美的集团"
    ]
    
    INDUSTRIES = ["新能源", "半导体", "消费", "医药", "金融"]
    
    METRICS = [
        "毛利率", "净利率", "ROE", "ROA", "资产负债率",
        "研发投入占比", "营业收入", "净利润", "市盈率", "每股收益"
    ]
    
    def __init__(self, 
                 target_size: int = 100,
                 fact_ratio: float = 0.5,
                 comparison_ratio: float = 0.3,
                 summary_ratio: float = 0.2):
        """
        初始化构建器
        
        Args:
            target_size: 目标样本数
            fact_ratio: 事实型问题比例
            comparison_ratio: 对比型问题比例
            summary_ratio: 汇总型问题比例
        """
        self.target_size = target_size
        self.fact_ratio = fact_ratio
        self.comparison_ratio = comparison_ratio
        self.summary_ratio = summary_ratio
        
        self.samples: List[EvalSample] = []
    
    def build_dataset(self) -> List[EvalSample]:
        """
        构建评测集
        
        Returns:
            评测样本列表
        """
        logger.info(f"[*] 开始构建评测集，目标: {self.target_size} 条")
        
        fact_count = int(self.target_size * self.fact_ratio)
        comparison_count = int(self.target_size * self.comparison_ratio)
        summary_count = self.target_size - fact_count - comparison_count
        
        logger.info(f"    事实型: {fact_count}, 对比型: {comparison_count}, 汇总型: {summary_count}")
        
        self.samples = []
        
        self.samples.extend(self._generate_fact_samples(fact_count))
        self.samples.extend(self._generate_comparison_samples(comparison_count))
        self.samples.extend(self._generate_summary_samples(summary_count))
        
        random.shuffle(self.samples)
        
        for i, sample in enumerate(self.samples):
            sample.query_id = f"q_{i+1:04d}"
        
        logger.info(f"[OK] 评测集构建完成，共 {len(self.samples)} 条")
        
        return self.samples
    
    def _generate_fact_samples(self, count: int) -> List[EvalSample]:
        """
        生成事实型问题
        
        Args:
            count: 数量
        
        Returns:
            样本列表
        """
        samples = []
        templates = self.FINANCE_TEMPLATES["fact"]
        
        for i in range(count):
            template = random.choice(templates)
            company = random.choice(self.COMPANIES)
            metric = random.choice(self.METRICS)
            year = random.choice(["2023", "2024", "2025"])
            quarter = random.choice(["Q1", "Q2", "Q3", "Q4"])
            
            query = template.format(
                company=company,
                metric=metric,
                year=year,
                quarter=quarter
            )
            
            sample = EvalSample(
                query_id=f"fact_{i+1:04d}",
                query=query,
                query_type="fact",
                ground_truth_doc_ids=[f"doc_{random.randint(1, 200):04d}"],
                ground_truth_answer=f"[待标注] {company}的{metric}数据",
                difficulty=random.choice(["easy", "medium", "hard"]),
                keywords=[company, metric]
            )
            samples.append(sample)
        
        return samples
    
    def _generate_comparison_samples(self, count: int) -> List[EvalSample]:
        """
        生成对比型问题
        
        Args:
            count: 数量
        
        Returns:
            样本列表
        """
        samples = []
        templates = self.FINANCE_TEMPLATES["comparison"]
        
        for i in range(count):
            template = random.choice(templates)
            
            company1, company2 = random.sample(self.COMPANIES, 2)
            metric = random.choice(self.METRICS)
            
            query = template.format(
                company1=company1,
                company2=company2,
                metric=metric
            )
            
            sample = EvalSample(
                query_id=f"comp_{i+1:04d}",
                query=query,
                query_type="comparison",
                ground_truth_doc_ids=[f"doc_{random.randint(1, 200):04d}", f"doc_{random.randint(1, 200):04d}"],
                ground_truth_answer=f"[待标注] {company1}与{company2}的{metric}对比分析",
                difficulty=random.choice(["medium", "hard"]),
                keywords=[company1, company2, metric]
            )
            samples.append(sample)
        
        return samples
    
    def _generate_summary_samples(self, count: int) -> List[EvalSample]:
        """
        生成汇总型问题
        
        Args:
            count: 数量
        
        Returns:
            样本列表
        """
        samples = []
        templates = self.FINANCE_TEMPLATES["summary"]
        
        for i in range(count):
            template = random.choice(templates)
            industry = random.choice(self.INDUSTRIES)
            year = random.choice(["2023", "2024", "2025"])
            
            query = template.format(industry=industry, year=year)
            
            sample = EvalSample(
                query_id=f"sum_{i+1:04d}",
                query=query,
                query_type="summary",
                ground_truth_doc_ids=[f"doc_{random.randint(1, 200):04d}" for _ in range(random.randint(2, 5))],
                ground_truth_answer=f"[待标注] {industry}行业{year}年分析",
                difficulty=random.choice(["medium", "hard"]),
                keywords=[industry, year]
            )
            samples.append(sample)
        
        return samples
    
    def save_dataset(self, output_path: str):
        """
        保存评测集
        
        Args:
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = {
            "metadata": {
                "total_samples": len(self.samples),
                "fact_samples": sum(1 for s in self.samples if s.query_type == "fact"),
                "comparison_samples": sum(1 for s in self.samples if s.query_type == "comparison"),
                "summary_samples": sum(1 for s in self.samples if s.query_type == "summary")
            },
            "samples": [s.to_dict() for s in self.samples]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[OK] 评测集已保存到: {output_path}")
    
    @staticmethod
    def load_dataset(input_path: str) -> List[EvalSample]:
        """
        加载评测集
        
        Args:
            input_path: 输入路径
        
        Returns:
            样本列表
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        samples = []
        for item in data.get("samples", []):
            sample = EvalSample(
                query_id=item["query_id"],
                query=item["query"],
                query_type=item["query_type"],
                ground_truth_doc_ids=item["ground_truth_doc_ids"],
                ground_truth_answer=item["ground_truth_answer"],
                difficulty=item.get("difficulty", "medium"),
                keywords=item.get("keywords", [])
            )
            samples.append(sample)
        
        return samples


class RetrievalEvaluator:
    """
    检索效果评测器
    
    支持：
    1. 纯向量召回评测
    2. 纯 BM25 召回评测
    3. 混合召回评测
    4. Reranker 效果评测
    """
    
    def __init__(self, k_values: List[int] = None):
        """
        初始化评测器
        
        Args:
            k_values: K 值列表
        """
        self.k_values = k_values or [3, 5, 10]
    
    def evaluate(self,
                queries: List[str],
                ground_truth_ids: List[List[str]],
                retriever,
                method_name: str = "unknown") -> Dict:
        """
        评测检索效果
        
        Args:
            queries: 查询列表
            ground_truth_ids: 相关文档ID列表
            retriever: 检索器
            method_name: 方法名称
        
        Returns:
            评测结果
        """
        logger.info(f"[*] 评测方法: {method_name}")
        
        results = {f"Recall@{k}": [] for k in self.k_values}
        results["MRR"] = []
        results["NDCG"] = []
        
        for query, truth_ids in zip(queries, ground_truth_ids):
            retrieved = retriever.search(query, top_k=max(self.k_values))
            retrieved_ids = [r.get("id") for r in retrieved]
            
            for k in self.k_values:
                recall = self._calculate_recall(retrieved_ids[:k], truth_ids)
                results[f"Recall@{k}"].append(recall)
            
            mrr = self._calculate_mrr(retrieved_ids, truth_ids)
            results["MRR"].append(mrr)
            
            ndcg = self._calculate_ndcg(retrieved_ids, truth_ids)
            results["NDCG"].append(ndcg)
        
        avg_results = {
            "method": method_name,
            "num_queries": len(queries)
        }
        
        for k in self.k_values:
            avg_results[f"Recall@{k}"] = sum(results[f"Recall@{k}"]) / len(results[f"Recall@{k}"])
        avg_results["MRR"] = sum(results["MRR"]) / len(results["MRR"])
        avg_results["NDCG"] = sum(results["NDCG"]) / len(results["NDCG"])
        
        logger.info(f"    Recall@5: {avg_results['Recall@5']:.4f}")
        logger.info(f"    MRR: {avg_results['MRR']:.4f}")
        
        return avg_results
    
    def _calculate_recall(self, retrieved: List[str], relevant: List[str]) -> float:
        """计算 Recall"""
        if not relevant:
            return 0.0
        return len(set(retrieved) & set(relevant)) / len(set(relevant))
    
    def _calculate_mrr(self, retrieved: List[str], relevant: List[str]) -> float:
        """计算 MRR"""
        relevant_set = set(relevant)
        for rank, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0 / rank
        return 0.0
    
    def _calculate_ndcg(self, retrieved: List[str], relevant: List[str]) -> float:
        """计算 NDCG"""
        import math
        
        relevant_set = set(relevant)
        
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                dcg += 1.0 / math.log2(rank + 1)
        
        ideal_dcg = 0.0
        for rank in range(1, min(len(relevant), len(retrieved)) + 1):
            ideal_dcg += 1.0 / math.log2(rank + 1)
        
        return dcg / ideal_dcg if ideal_dcg > 0 else 0.0
    
    def compare_methods(self,
                       queries: List[str],
                       ground_truth_ids: List[List[str]],
                       methods: Dict[str, Any]) -> Dict:
        """
        对比不同检索方法
        
        Args:
            queries: 查询列表
            ground_truth_ids: 相关文档ID列表
            methods: 方法名称到检索器的映射
        
        Returns:
            对比结果
        """
        comparison = {"methods": [], "results": []}
        
        for method_name, retriever in methods.items():
            result = self.evaluate(queries, ground_truth_ids, retriever, method_name)
            comparison["methods"].append(method_name)
            comparison["results"].append(result)
        
        return comparison
    
    def generate_comparison_table(self, comparison: Dict) -> str:
        """
        生成对比表格
        
        Args:
            comparison: 对比结果
        
        Returns:
            Markdown 表格
        """
        lines = []
        lines.append("| 召回方案 | Recall@3 | Recall@5 | Recall@10 | MRR | NDCG |")
        lines.append("|----------|----------|----------|-----------|-----|------|")
        
        for result in comparison["results"]:
            lines.append(
                f"| {result['method']} | "
                f"{result.get('Recall@3', 0):.4f} | "
                f"{result.get('Recall@5', 0):.4f} | "
                f"{result.get('Recall@10', 0):.4f} | "
                f"{result.get('MRR', 0):.4f} | "
                f"{result.get('NDCG', 0):.4f} |"
            )
        
        return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 评测集构建")
    parser.add_argument("--size", type=int, default=100, help="评测集大小")
    parser.add_argument("--output", type=str, default="data/eval/eval_dataset.json", help="输出路径")
    
    args = parser.parse_args()
    
    builder = EvalDatasetBuilder(target_size=args.size)
    samples = builder.build_dataset()
    builder.save_dataset(args.output)
    
    print(f"\n评测集统计:")
    print(f"  总数: {len(samples)}")
    print(f"  事实型: {sum(1 for s in samples if s.query_type == 'fact')}")
    print(f"  对比型: {sum(1 for s in samples if s.query_type == 'comparison')}")
    print(f"  汇总型: {sum(1 for s in samples if s.query_type == 'summary')}")
