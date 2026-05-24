"""
FinRAG 重排序模块

实现交叉编码器重排序和 RRF 融合
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Reranker:
    """
    重排序器
    
    功能：
    1. 交叉编码器重排序
    2. RRF (Reciprocal Rank Fusion) 融合
    """
    
    def __init__(self, 
                 model_name: str = "BAAI/bge-reranker-base",
                 device: str = "cpu",
                 use_cross_encoder: bool = True):
        """
        初始化重排序器
        
        Args:
            model_name: 模型名称
            device: 运行设备
            use_cross_encoder: 是否使用交叉编码器
        """
        self.model_name = model_name
        self.device = device
        self.use_cross_encoder = use_cross_encoder
        self.model = None
        
        if use_cross_encoder:
            self._init_model()
    
    def _init_model(self):
        """
        初始化交叉编码器模型
        """
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"[*] 正在加载重排序模型: {self.model_name}")
            self.model = CrossEncoder(self.model_name, device=self.device)
            logger.info("[OK] 重排序模型加载完成")
            
        except ImportError:
            logger.warning("[!] sentence-transformers 未安装，将使用简单重排序")
            self.model = None
        except Exception as e:
            logger.warning(f"[!] 重排序模型加载失败: {e}")
            self.model = None
    
    def rerank(self, 
              query: str, 
              documents: List[Dict], 
              top_k: int = 5) -> List[Dict]:
        """
        重排序
        
        Args:
            query: 查询文本
            documents: 文档列表 (包含 text 字段)
            top_k: 返回数量
        
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        if self.model is not None:
            return self._cross_encoder_rerank(query, documents, top_k)
        else:
            return self._simple_rerank(query, documents, top_k)
    
    def _cross_encoder_rerank(self, 
                             query: str, 
                             documents: List[Dict], 
                             top_k: int) -> List[Dict]:
        """
        使用交叉编码器重排序

        Args:
            query: 查询
            documents: 文档列表
            top_k: 返回数量

        Returns:
            重排序结果
        """
        # 获取text字段：先尝试document.text，再尝试直接text
        pairs = []
        for doc in documents:
            text = doc.get("document", {}).get("text", doc.get("text", ""))
            pairs.append((query, text))
        
        scores = self.model.predict(pairs)
        
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc, score in scored_docs[:top_k]:
            result = doc.copy()
            result["rerank_score"] = float(score)
            results.append(result)
        
        return results
    
    def _simple_rerank(self, 
                      query: str, 
                      documents: List[Dict], 
                      top_k: int) -> List[Dict]:
        """
        简单重排序 (基于关键词匹配)

        Args:
            query: 查询
            documents: 文档列表
            top_k: 返回数量

        Returns:
            重排序结果
        """
        query_terms = set(query.lower().split())

        scored_docs = []
        for doc in documents:
            text = doc.get("document", {}).get("text", doc.get("text", "")).lower()
            doc_terms = set(text.split())
            
            overlap = len(query_terms & doc_terms)
            score = overlap / (len(query_terms) + 1)
            
            scored_docs.append((doc, score))
        
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc, score in scored_docs[:top_k]:
            result = doc.copy()
            result["rerank_score"] = float(score)
            results.append(result)
        
        return results


class HybridRetriever:
    """
    混合检索器
    
    功能：
    1. 向量检索 + BM25 检索
    2. RRF 融合
    3. 重排序
    """
    
    def __init__(self, 
                 vector_retriever=None,
                 bm25_retriever=None,
                 reranker=None,
                 rrf_k: int = 60):
        """
        初始化混合检索器
        
        Args:
            vector_retriever: 向量检索器
            bm25_retriever: BM25 检索器
            reranker: 重排序器
            rrf_k: RRF 参数 k
        """
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
        self.rrf_k = rrf_k
    
    def search(self, 
              query: str,
              query_vector: np.ndarray = None,
              top_k: int = 20,
              rerank_top_k: int = 5,
              use_rerank: bool = True) -> List[Dict]:
        """
        混合检索
        
        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 初筛数量
            rerank_top_k: 重排序后数量
            use_rerank: 是否使用重排序
        
        Returns:
            检索结果列表
        """
        vector_results = []
        bm25_results = []
        
        if self.vector_retriever and query_vector is not None:
            vector_results = self.vector_retriever.search(query_vector, top_k)
        
        if self.bm25_retriever:
            bm25_results = self.bm25_retriever.search(query, top_k)
        
        if vector_results and bm25_results:
            fused_results = self._rrf_fusion(vector_results, bm25_results)
        elif vector_results:
            fused_results = vector_results
        elif bm25_results:
            fused_results = bm25_results
        else:
            return []
        
        if use_rerank and self.reranker and len(fused_results) > rerank_top_k:
            fused_results = self.reranker.rerank(query, fused_results, rerank_top_k)
        
        return fused_results[:rerank_top_k]
    
    def _rrf_fusion(self, 
                   vector_results: List[Dict], 
                   bm25_results: List[Dict]) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合
        
        RRF(d) = Σ 1 / (k + rank(d))
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25 检索结果
        
        Returns:
            融合后的结果
        """
        doc_scores = defaultdict(float)
        doc_info = {}
        
        for rank, result in enumerate(vector_results, 1):
            doc_id = result.get("id")
            doc_scores[doc_id] += 1.0 / (self.rrf_k + rank)
            doc_info[doc_id] = result
        
        for rank, result in enumerate(bm25_results, 1):
            doc_id = result.get("id")
            doc_scores[doc_id] += 1.0 / (self.rrf_k + rank)
            if doc_id not in doc_info:
                doc_info[doc_id] = result
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs:
            result = doc_info[doc_id].copy()
            result["rrf_score"] = float(score)
            results.append(result)
        
        return results
    
    def set_retrievers(self, vector_retriever=None, bm25_retriever=None):
        """
        设置检索器
        
        Args:
            vector_retriever: 向量检索器
            bm25_retriever: BM25 检索器
        """
        if vector_retriever:
            self.vector_retriever = vector_retriever
        if bm25_retriever:
            self.bm25_retriever = bm25_retriever
    
    def set_reranker(self, reranker):
        """
        设置重排序器
        
        Args:
            reranker: 重排序器
        """
        self.reranker = reranker
