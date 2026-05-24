"""
FinRAG RAGAS 自动化评测模块

使用 RAGAS 框架评估 RAG 系统质量
评估维度：
1. Faithfulness (忠实度)
2. Answer Relevancy (回答相关性)
3. Context Precision (上下文精确度)
4. Context Recall (上下文召回率)
"""

import os
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """
    RAGAS 评测器
    
    简化版实现，无需依赖 ragas 库
    """
    
    def __init__(self, llm_client=None):
        """
        初始化评测器
        
        Args:
            llm_client: LLM 客户端 (用于生成评测)
        """
        self.llm_client = llm_client
    
    def evaluate(self,
                questions: List[str],
                answers: List[str],
                contexts: List[List[str]],
                ground_truths: List[str] = None) -> Dict:
        """
        评估 RAG 系统
        
        Args:
            questions: 问题列表
            answers: 回答列表
            contexts: 上下文列表
            ground_truths: 标准答案列表
        
        Returns:
            评测结果
        """
        results = {
            "faithfulness": [],
            "answer_relevancy": [],
            "context_precision": [],
            "context_recall": []
        }
        
        for i, (question, answer, context) in enumerate(zip(questions, answers, contexts)):
            faithfulness = self._evaluate_faithfulness(answer, context)
            results["faithfulness"].append(faithfulness)
            
            relevancy = self._evaluate_answer_relevancy(question, answer)
            results["answer_relevancy"].append(relevancy)
            
            precision = self._evaluate_context_precision(question, context)
            results["context_precision"].append(precision)
            
            if ground_truths and i < len(ground_truths):
                recall = self._evaluate_context_recall(
                    ground_truths[i], context
                )
                results["context_recall"].append(recall)
        
        return {
            "faithfulness": sum(results["faithfulness"]) / len(results["faithfulness"]),
            "answer_relevancy": sum(results["answer_relevancy"]) / len(results["answer_relevancy"]),
            "context_precision": sum(results["context_precision"]) / len(results["context_precision"]),
            "context_recall": sum(results["context_recall"]) / len(results["context_recall"]) if results["context_recall"] else None,
            "num_samples": len(questions)
        }
    
    def _evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        评估忠实度 (回答是否基于上下文)
        
        Args:
            answer: 回答
            contexts: 上下文列表
        
        Returns:
            忠实度分数 [0, 1]
        """
        if not answer or not contexts:
            return 0.0
        
        context_text = " ".join(contexts)
        
        answer_words = set(answer.lower().split())
        context_words = set(context_text.lower().split())
        
        overlap = answer_words & context_words
        
        if not answer_words:
            return 0.0
        
        return len(overlap) / len(answer_words)
    
    def _evaluate_answer_relevancy(self, question: str, answer: str) -> float:
        """
        评估回答相关性
        
        Args:
            question: 问题
            answer: 回答
        
        Returns:
            相关性分数 [0, 1]
        """
        if not question or not answer:
            return 0.0
        
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        overlap = question_words & answer_words
        
        if not question_words:
            return 0.0
        
        return len(overlap) / len(question_words)
    
    def _evaluate_context_precision(self, question: str, contexts: List[str]) -> float:
        """
        评估上下文精确度
        
        Args:
            question: 问题
            contexts: 上下文列表
        
        Returns:
            精确度分数 [0, 1]
        """
        if not contexts:
            return 0.0
        
        question_words = set(question.lower().split())
        
        scores = []
        for context in contexts:
            context_words = set(context.lower().split())
            overlap = question_words & context_words
            if question_words:
                scores.append(len(overlap) / len(question_words))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _evaluate_context_recall(self, ground_truth: str, contexts: List[str]) -> float:
        """
        评估上下文召回率
        
        Args:
            ground_truth: 标准答案
            contexts: 上下文列表
        
        Returns:
            召回率分数 [0, 1]
        """
        if not ground_truth or not contexts:
            return 0.0
        
        truth_words = set(ground_truth.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        overlap = truth_words & context_words
        
        if not truth_words:
            return 0.0
        
        return len(overlap) / len(truth_words)
    
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
        
        logger.info(f"[OK] RAGAS 评测结果已保存到: {output_path}")


def run_ragas_evaluation(rag_chain, test_data_path: str, output_path: str):
    """
    运行 RAGAS 评测
    
    Args:
        rag_chain: RAG 工作链
        test_data_path: 测试数据路径
        output_path: 输出路径
    """
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    questions = test_data.get("questions", [])
    ground_truths = test_data.get("ground_truths", [])
    
    answers = []
    contexts = []
    
    for question in questions:
        result = rag_chain.run(question)
        answers.append(result.answer)
        contexts.append([s.get("text_preview", "") for s in result.sources])
    
    evaluator = RAGASEvaluator()
    results = evaluator.evaluate(questions, answers, contexts, ground_truths)
    
    evaluator.save_results(results, output_path)
    
    print("\n" + "=" * 60)
    print("RAGAS 评测结果")
    print("=" * 60)
    print(f"忠实度 (Faithfulness): {results['faithfulness']:.4f}")
    print(f"回答相关性 (Answer Relevancy): {results['answer_relevancy']:.4f}")
    print(f"上下文精确度 (Context Precision): {results['context_precision']:.4f}")
    if results['context_recall']:
        print(f"上下文召回率 (Context Recall): {results['context_recall']:.4f}")
    print(f"样本数量: {results['num_samples']}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG RAGAS 评测")
    parser.add_argument("--test-data", type=str, required=True,
                       help="测试数据路径")
    parser.add_argument("--output", type=str, default="experiments/ragas_results.json",
                       help="输出路径")
    
    args = parser.parse_args()
    
    print("[!] 请在完整系统中配置 RAG 工作链后运行评测")
