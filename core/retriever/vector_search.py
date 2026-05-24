"""
FinRAG 向量检索模块

使用 FAISS 进行高效向量检索
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VectorRetriever:
    """
    向量检索器
    
    功能：
    1. 向量索引构建
    2. 相似度检索
    3. 索引持久化
    """
    
    def __init__(self, dimension: int = 1024, use_gpu: bool = False):
        """
        初始化向量检索器
        
        Args:
            dimension: 向量维度
            use_gpu: 是否使用 GPU
        """
        self.dimension = dimension
        self.use_gpu = use_gpu
        self.index = None
        self.doc_store = {}
        self.id_list = []
        
        self._init_faiss()
    
    def _init_faiss(self):
        """
        初始化 FAISS 索引
        """
        try:
            import faiss
            
            self.index = faiss.IndexFlatIP(self.dimension)
            
            if self.use_gpu:
                try:
                    res = faiss.StandardGpuResources()
                    self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
                    logger.info("[OK] FAISS GPU 模式已启用")
                except Exception as e:
                    logger.warning(f"[!] GPU 初始化失败，使用 CPU: {e}")
                    self.use_gpu = False
            
            logger.info(f"[OK] FAISS 索引初始化完成，维度: {self.dimension}")
            
        except ImportError:
            logger.warning("[!] FAISS 未安装，将使用简单向量检索")
            self.index = None
            self.vectors = []
    
    def add_documents(self, 
                     doc_ids: List[str], 
                     vectors: np.ndarray, 
                     documents: List[Dict]):
        """
        添加文档到索引
        
        Args:
            doc_ids: 文档 ID 列表
            vectors: 向量矩阵 (n, dimension)
            documents: 文档内容列表
        """
        if len(doc_ids) != len(vectors) or len(doc_ids) != len(documents):
            raise ValueError("doc_ids, vectors, documents 长度必须一致")
        
        vectors = vectors.astype(np.float32)
        
        if self.index is not None:
            import faiss
            faiss.normalize_L2(vectors)
            self.index.add(vectors)
        else:
            if not hasattr(self, 'vectors'):
                self.vectors = []
            self.vectors.extend(vectors.tolist())
        
        for doc_id, doc in zip(doc_ids, documents):
            self.doc_store[doc_id] = doc
            self.id_list.append(doc_id)
        
        logger.info(f"[OK] 已添加 {len(doc_ids)} 个文档到索引")
    
    def search(self, 
              query_vector: np.ndarray, 
              top_k: int = 10) -> List[Dict]:
        """
        向量检索
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        if len(self.id_list) == 0:
            return []
        
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        
        if self.index is not None:
            import faiss
            faiss.normalize_L2(query_vector)
            
            actual_k = min(top_k, len(self.id_list))
            scores, indices = self.index.search(query_vector, actual_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.id_list):
                    doc_id = self.id_list[idx]
                    results.append({
                        "id": doc_id,
                        "score": float(score),
                        "document": self.doc_store.get(doc_id, {})
                    })
            
            return results
        else:
            return self._simple_search(query_vector, top_k)
    
    def _simple_search(self, query_vector: np.ndarray, top_k: int) -> List[Dict]:
        """
        简单向量检索 (无 FAISS 时的备用方案)
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        if not hasattr(self, 'vectors') or len(self.vectors) == 0:
            return []
        
        query_norm = query_vector.flatten()
        query_norm = query_norm / (np.linalg.norm(query_norm) + 1e-8)
        
        scores = []
        for i, vec in enumerate(self.vectors):
            vec_norm = np.array(vec)
            vec_norm = vec_norm / (np.linalg.norm(vec_norm) + 1e-8)
            score = np.dot(query_norm, vec_norm)
            scores.append((score, i))
        
        scores.sort(reverse=True)
        
        results = []
        for score, idx in scores[:top_k]:
            if idx < len(self.id_list):
                doc_id = self.id_list[idx]
                results.append({
                    "id": doc_id,
                    "score": float(score),
                    "document": self.doc_store.get(doc_id, {})
                })
        
        return results
    
    def save(self, path: str):
        """
        保存索引
        
        Args:
            path: 保存路径
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        if self.index is not None:
            import faiss
            
            index_to_save = self.index
            if self.use_gpu:
                index_to_save = faiss.index_gpu_to_cpu(self.index)
            
            faiss.write_index(index_to_save, f"{path}.index")
        
        with open(f"{path}.store.json", 'w', encoding='utf-8') as f:
            json.dump({
                "doc_store": self.doc_store,
                "id_list": self.id_list,
                "dimension": self.dimension
            }, f, ensure_ascii=False)
        
        logger.info(f"[OK] 索引已保存到: {path}")
    
    def load(self, path: str):
        """
        加载索引
        
        Args:
            path: 索引路径
        """
        if os.path.exists(f"{path}.index"):
            import faiss
            import tempfile
            import shutil
            tmp_dir = tempfile.mkdtemp()
            src_file = f"{path}.index"
            tmp_file = os.path.join(tmp_dir, "faiss_tmp.index")
            shutil.copy2(src_file, tmp_file)
            self.index = faiss.read_index(tmp_file)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        
        if os.path.exists(f"{path}.store.json"):
            with open(f"{path}.store.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.doc_store = data.get("doc_store", {})
                self.id_list = data.get("id_list", [])
        
        logger.info(f"[OK] 索引已从 {path} 加载，共 {len(self.id_list)} 个文档")
    
    def get_document_count(self) -> int:
        """
        获取文档数量
        
        Returns:
            文档数量
        """
        return len(self.id_list)
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        根据 ID 获取文档
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            文档内容
        """
        return self.doc_store.get(doc_id)
