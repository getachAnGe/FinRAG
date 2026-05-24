"""
FinRAG RAG 工作链模块

完整的 RAG 工作流编排：
1. 问题理解
2. 检索
3. 重排序
4. 生成
5. 证据绑定
"""

import os
import json
import yaml
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from core.retriever.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """
    RAG 结果数据结构
    
    Attributes:
        question: 用户问题
        answer: 生成的回答
        sources: 引用来源列表
        confidence: 置信度
        metadata: 其他元数据
    """
    question: str
    answer: str
    sources: List[Dict]
    confidence: float = 0.0
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class RAGChain:
    """
    RAG 工作链
    
    完整流程：
    1. 问题预处理
    2. 混合检索
    3. 重排序
    4. 上下文构建
    5. LLM 生成
    6. 证据绑定
    """
    
    REFUSAL_PHRASES = [
        "根据现有研报信息无法回答",
        "提供的文档中未包含",
        "上下文中没有相关信息",
        "无法从提供的资料中找到"
    ]
    
    def __init__(self, 
                 embedder=None,
                 vector_retriever=None,
                 bm25_retriever=None,
                 reranker=None,
                 llm_client=None,
                 config_path: str = None):
        """
        初始化 RAG 工作链
        
        Args:
            embedder: 向量化器
            vector_retriever: 向量检索器
            bm25_retriever: BM25 检索器
            reranker: 重排序器
            llm_client: LLM 客户端
            config_path: 配置文件路径
        """
        self.embedder = embedder
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
        self.llm_client = llm_client
        
        self.config = self._load_config(config_path)
        self.prompts = self._load_prompts(config_path)

        self.query_rewriter = self._init_query_rewriter(config_path)
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置
        
        Args:
            config_path: 配置路径
        
        Returns:
            配置字典
        """
        default_config = {
            "top_k": 20,
            "rerank_top_k": 5,
            "use_rerank": True,
            "temperature": 0.1,
            "max_tokens": 2048
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if "retriever" in config:
                    default_config.update(config["retriever"])
                for key in ["query_rewrite", "finance_terms", "reranker"]:
                    if key in config:
                        default_config[key] = config[key]
        
        return default_config
    
    def _load_prompts(self, config_path: str) -> Dict:
        """
        加载提示词模板
        
        Args:
            config_path: 配置路径
        
        Returns:
            提示词字典
        """
        default_prompts = {
            "qa_prompt": """你是一个专业的金融分析助手。请根据以下上下文信息回答用户的问题。

上下文信息：
{context}

问题：{question}

回答要求：
1. 只基于提供的上下文信息回答，不要编造信息
2. 如果上下文信息不足以回答问题，请回答"根据现有研报信息无法回答该问题"
3. 回答中标注引用来源，格式为 [Source X]，其中X是上下文中提供的来源编号
4. 如果涉及数据，请明确指出数据来源的页码

回答：""",
            
            "refusal_prompt": "根据现有研报信息无法回答该问题。提供的文档中未包含与问题相关的信息。"
        }
        
        if config_path:
            prompts_path = config_path.replace("config.yaml", "prompts.yaml")
            if os.path.exists(prompts_path):
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    prompts = yaml.safe_load(f)
                    default_prompts.update(prompts)
        
        return default_prompts

    def _init_query_rewriter(self, config_path: str) -> Optional[QueryRewriter]:
        """从配置初始化 QueryRewriter"""
        config = self.config
        qr_cfg = config.get("query_rewrite", {})
        if not qr_cfg.get("enable", False):
            return None
        synonyms = config.get("finance_terms", {}).get("synonyms", {})
        strategy = qr_cfg.get("strategy", "expand")
        logger.info(f"[OK] QueryRewriter 已启用 (strategy={strategy}, {len(synonyms)}组同义词)")
        return QueryRewriter(synonyms=synonyms, strategy=strategy)

    def _rewrite_query(self, question: str) -> Tuple[str, str]:
        """
        改写查询：改写后的query用于检索，原始query用于生成
        
        Returns:
            (retrieval_query, original_query)
        """
        if self.query_rewriter:
            rewritten = self.query_rewriter.rewrite(question)
            if rewritten != question:
                logger.info(f"  Query改写: '{question}' -> '{rewritten}'")
            return rewritten, question
        return question, question
    
    def run(self, question: str) -> RAGResult:
        """
        执行 RAG 流程
        
        Args:
            question: 用户问题
        
        Returns:
            RAG 结果
        """
        logger.info(f"[*] 处理问题: {question}")
        
        retrieval_query, original_question = self._rewrite_query(question)
        
        query_vector = self._encode_question(retrieval_query)
        
        retrieved_docs = self._retrieve(retrieval_query, query_vector)
        
        if not retrieved_docs:
            return RAGResult(
                question=original_question,
                answer=self.prompts["refusal_prompt"],
                sources=[],
                confidence=0.0
            )
        
        reranked_docs = self._rerank(retrieval_query, retrieved_docs)
        
        context = self._build_context(reranked_docs)
        
        answer = self._generate_answer(original_question, context)
        
        sources = self._extract_sources(reranked_docs, answer)
        
        confidence = self._calculate_confidence(reranked_docs, answer)
        
        return RAGResult(
            question=original_question,
            answer=answer,
            sources=sources,
            confidence=confidence,
            metadata={
                "retrieved_count": len(retrieved_docs),
                "reranked_count": len(reranked_docs)
            }
        )
    
    def _extract_company_from_query(self, question: str) -> str:
        """
        从问题中提取公司名
        
        Args:
            question: 问题文本
        
        Returns:
            公司名，未找到返回空字符串
        """
        import re
        parts = re.findall(r'[\u4e00-\u9fff]{2,10}(?=的[营净毛利总研资每资加资])', question)
        if parts:
            return parts[0]
        pattern = re.search(r'在[^，]+中，([\u4e00-\u9fff]{2,10})的', question)
        if pattern:
            return pattern.group(1)
        return ""

    def _extract_file_suffix(self, question: str) -> str:
        """
        从问题中提取文件名后缀（如同花顺_8）
        问题格式：在传媒_华录百纳_同花顺_8第3页中，...
        
        Args:
            question: 问题文本
        
        Returns:
            文件后缀，未找到返回空字符串
        """
        import re
        match = re.search(r'在\w+_\w+_([^第]+?第)', question)
        if match:
            suffix = match.group(1).rstrip('第')
            return suffix
        return ""

    def _extract_source_file_filter(self, question: str) -> str:
        """
        从问题中提取源文件名称（用于过滤）
        
        Args:
            question: 问题文本
        
        Returns:
            源文件名中的公司部分
        """
        company = self._extract_company_from_query(question)
        if not company:
            return ""
        return company

    def _filter_by_company(self, results: List[Dict], company: str, file_suffix: str = "") -> List[Dict]:
        """
        根据公司名和文件名后缀过滤检索结果
        
        Args:
            results: 检索结果
            company: 公司名
            file_suffix: 文件名后缀（如同花顺_8）
        
        Returns:
            过滤后的结果
        """
        if not company:
            return results
        
        filtered = []
        for r in results:
            doc = r.get("document", {})
            if isinstance(doc, dict):
                source = doc.get("source", "")
            else:
                source = r.get("source", "")
            
            if company in source:
                if file_suffix:
                    if file_suffix in source:
                        filtered.append(r)
                else:
                    filtered.append(r)
        
        if not filtered:
            return results
        
        return filtered

    def _encode_question(self, question: str) -> Any:
        """
        问题向量化
        
        Args:
            question: 问题文本
        
        Returns:
            问题向量
        """
        if self.embedder:
            return self.embedder.encode_single(question)
        return None
    
    def _retrieve(self, question: str, query_vector: Any) -> List[Dict]:
        """
        混合检索（带元数据过滤 + 两阶段）
        
        Args:
            question: 问题文本
            query_vector: 问题向量
        
        Returns:
            检索结果
        """
        company = self._extract_company_from_query(question)
        file_suffix = self._extract_file_suffix(question)
        retrieve_k = self.config["top_k"] * 2
        
        results = []
        
        if self.vector_retriever and query_vector is not None:
            vector_results = self.vector_retriever.search(
                query_vector, 
                top_k=retrieve_k
            )
            results.extend(vector_results)
        
        if self.bm25_retriever:
            bm25_results = self.bm25_retriever.search(
                question, 
                top_k=retrieve_k
            )
            
            for result in bm25_results:
                if result["id"] not in [r["id"] for r in results]:
                    results.append(result)
        
        if company:
            filtered = self._filter_by_company(results, company, file_suffix)
            if filtered:
                results = filtered
        
        normalized = []
        seen_ids = set()
        for r in results:
            rid = r.get("id", "")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            doc = r.get("document", {})
            if doc and isinstance(doc, dict):
                r["text"] = doc.get("text", "")
                r["source"] = doc.get("source", "未知来源")
                r["page_num"] = doc.get("page_num")
            normalized.append(r)

        return normalized
    
    def _rerank(self, question: str, documents: List[Dict]) -> List[Dict]:
        """
        重排序
        
        Args:
            question: 问题
            documents: 文档列表
        
        Returns:
            重排序后的文档
        """
        if self.reranker and self.config["use_rerank"]:
            return self.reranker.rerank(
                question, 
                documents, 
                top_k=self.config["rerank_top_k"]
            )
        
        return documents[:self.config["rerank_top_k"]]
    
    def _build_context(self, documents: List[Dict]) -> str:
        """
        构建上下文
        
        Args:
            documents: 文档列表
        
        Returns:
            格式化的上下文文本
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "")
            source = doc.get("source", "未知来源")
            page = doc.get("page_num", "未知")
            
            context_parts.append(
                f"[Source {i}] (来源: {source}, 第 {page} 页)\n{text}"
            )
        
        return "\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        生成回答
        
        Args:
            question: 问题
            context: 上下文
        
        Returns:
            生成的回答
        """
        prompt = self.prompts["qa_prompt"].format(
            context=context,
            question=question
        )
        
        if self.llm_client:
            return self.llm_client.generate(prompt)
        else:
            return "[未配置 LLM] 请配置 LLM 客户端以启用回答生成功能。"
    
    def _extract_sources(self, documents: List[Dict], answer: str) -> List[Dict]:
        """
        提取引用来源
        
        Args:
            documents: 文档列表
            answer: 生成的回答
        
        Returns:
            来源列表
        """
        sources = []
        
        for i, doc in enumerate(documents, 1):
            source_tag = f"[Source {i}]"
            if source_tag in answer:
                sources.append({
                    "id": doc.get("id"),
                    "source": doc.get("source"),
                    "page_num": doc.get("page_num"),
                    "text_preview": doc.get("text", "")[:200] + "...",
                    "bbox": doc.get("bbox")
                })
        
        return sources
    
    def _calculate_confidence(self, documents: List[Dict], answer: str) -> float:
        """
        计算置信度
        
        Args:
            documents: 文档列表
            answer: 回答
        
        Returns:
            置信度分数
        """
        if any(phrase in answer for phrase in self.REFUSAL_PHRASES):
            return 0.0
        
        if not documents:
            return 0.0
        
        scores = []
        for doc in documents:
            score = doc.get("score", 0) or doc.get("rerank_score", 0) or doc.get("rrf_score", 0)
            scores.append(score)
        
        if scores:
            return min(1.0, sum(scores) / len(scores))
        
        return 0.5
    
    def chat(self, question: str) -> str:
        """
        简单对话接口
        
        Args:
            question: 问题
        
        Returns:
            回答
        """
        result = self.run(question)
        return result.answer
    
    def set_components(self, 
                      embedder=None,
                      vector_retriever=None,
                      bm25_retriever=None,
                      reranker=None,
                      llm_client=None):
        """
        设置组件
        
        Args:
            embedder: 向量化器
            vector_retriever: 向量检索器
            bm25_retriever: BM25 检索器
            reranker: 重排序器
            llm_client: LLM 客户端
        """
        if embedder:
            self.embedder = embedder
        if vector_retriever:
            self.vector_retriever = vector_retriever
        if bm25_retriever:
            self.bm25_retriever = bm25_retriever
        if reranker:
            self.reranker = reranker
        if llm_client:
            self.llm_client = llm_client
