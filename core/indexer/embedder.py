"""
FinRAG 向量化模块

使用 BGE-M3 模型进行文本向量化
支持多语言、长文本、稠密/稀疏向量
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import json
import numpy as np
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """
    向量化结果
    
    Attributes:
        dense_vectors: 稠密向量
        sparse_vectors: 稀疏向量 (可选)
        texts: 原始文本
        metadata: 元数据
    """
    dense_vectors: np.ndarray
    sparse_vectors: Optional[List[Dict]] = None
    texts: List[str] = None
    metadata: Dict = None


class Embedder:
    """
    文本向量化器
    
    支持：
    1. BGE-M3 模型 (推荐)
    2. 本地模型加载
    3. 批量向量化
    """
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 device: str = "cpu",
                 max_batch_size: int = 32,
                 max_length: int = 512):
        """
        初始化向量化器
        
        Args:
            model_name: 模型名称或路径
            device: 运行设备 (cpu/cuda)
            max_batch_size: 最大批处理大小
            max_length: 最大文本长度
        """
        self.model_name = model_name
        self.device = device
        self.max_batch_size = max_batch_size
        self.max_length = max_length
        self.model = None
        self.tokenizer = None
        self.dimension = 384
        
        self._init_model()
    
    def _init_model(self):
        """
        初始化模型
        """
        try:
            from FlagEmbedding import BGEM3FlagModel
            
            logger.info(f"[*] 正在加载 BGE-M3 模型: {self.model_name}")
            
            self.model = BGEM3FlagModel(
                self.model_name,
                use_fp16=True if self.device == "cuda" else False,
                device=self.device
            )
            
            self.dimension = 1024
            logger.info(f"[OK] BGE-M3 模型加载完成，向量维度: {self.dimension}")
            
        except ImportError:
            logger.warning("[!] FlagEmbedding 未安装，尝试使用 sentence-transformers")
            self._init_sentence_transformer()
        except Exception as e:
            logger.error(f"[!] BGE-M3 模型加载失败: {e}")
            logger.info("[*] 尝试使用 sentence-transformers 加载")
            self._init_sentence_transformer()
    
    def _init_sentence_transformer(self):
        """
        使用 sentence-transformers 初始化
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"[OK] SentenceTransformer 模型加载完成，维度: {self.dimension}")
            
        except ImportError:
            logger.error("[!] sentence-transformers 也未安装")
            self._init_fallback()
    
    def _init_fallback(self):
        """
        备用方案：使用简单的哈希向量化
        """
        logger.warning("[!] 使用备用哈希向量化方案")
        self.model = None
        self.dimension = 768
    
    def encode(self, texts: List[str], 
               batch_size: int = None,
               show_progress: bool = False) -> np.ndarray:
        """
        文本向量化
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            show_progress: 是否显示进度
        
        Returns:
            向量矩阵 (n_texts, dimension)
        """
        if not texts:
            return np.array([])
        
        batch_size = batch_size or self.max_batch_size
        
        if self.model is None:
            return self._fallback_encode(texts)
        
        try:
            if hasattr(self.model, 'encode'):
                if hasattr(self.model, 'encode_queries'):
                    return self._encode_bge_m3(texts, batch_size)
                else:
                    return self._encode_sentence_transformer(texts, batch_size, show_progress)
        except Exception as e:
            logger.error(f"[!] 向量化失败: {e}")
            return self._fallback_encode(texts)
    
    def _encode_bge_m3(self, texts: List[str], batch_size: int) -> np.ndarray:
        """
        使用 BGE-M3 编码
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False
        )
        
        return np.array(embeddings['dense_vecs'])
    
    def _encode_sentence_transformer(self, texts: List[str], 
                                     batch_size: int,
                                     show_progress: bool) -> np.ndarray:
        """
        使用 SentenceTransformer 编码
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def _fallback_encode(self, texts: List[str]) -> np.ndarray:
        """
        备用向量化方案 (简单哈希)
        """
        np.random.seed(42)
        
        embeddings = []
        for text in texts:
            text_hash = hash(text)
            np.random.seed(abs(text_hash) % (2**31))
            embedding = np.random.randn(self.dimension).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        
        return np.array(embeddings)
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        单文本向量化
        
        Args:
            text: 文本
        
        Returns:
            向量
        """
        return self.encode([text])[0]
    
    def encode_with_metadata(self, 
                            texts: List[str],
                            metadata_list: List[Dict] = None) -> EmbeddingResult:
        """
        带元数据的向量化
        
        Args:
            texts: 文本列表
            metadata_list: 元数据列表
        
        Returns:
            EmbeddingResult
        """
        vectors = self.encode(texts)
        
        return EmbeddingResult(
            dense_vectors=vectors,
            texts=texts,
            metadata={"metadata_list": metadata_list} if metadata_list else None
        )
    
    def save_embeddings(self, embeddings: np.ndarray, output_path: str):
        """
        保存向量
        
        Args:
            embeddings: 向量矩阵
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.save(output_path, embeddings)
        logger.info(f"[OK] 向量已保存到: {output_path}")
    
    @staticmethod
    def load_embeddings(input_path: str) -> np.ndarray:
        """
        加载向量
        
        Args:
            input_path: 输入路径
        
        Returns:
            向量矩阵
        """
        return np.load(input_path)


class VectorIndex:
    """
    向量索引管理
    
    使用 FAISS 进行高效向量检索
    """
    
    def __init__(self, dimension: int = 1024, index_type: str = "Flat"):
        """
        初始化向量索引
        
        Args:
            dimension: 向量维度
            index_type: 索引类型 (Flat/IVF/HNSW)
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.id_map = []
        
        self._init_index()
    
    def _init_index(self):
        """
        初始化 FAISS 索引
        """
        try:
            import faiss
            
            if self.index_type == "Flat":
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "IVF":
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
            
            logger.info(f"[OK] FAISS 索引初始化完成: {self.index_type}")
            
        except ImportError:
            logger.warning("[!] FAISS 未安装，将使用简单向量检索")
            self.index = None
    
    def add_vectors(self, vectors: np.ndarray, ids: List[str] = None):
        """
        添加向量到索引
        
        Args:
            vectors: 向量矩阵 (n, dimension)
            ids: ID 列表
        """
        if vectors.shape[0] == 0:
            return
        
        vectors = vectors.astype(np.float32)
        
        if self.index is not None:
            import faiss
            faiss.normalize_L2(vectors)
            self.index.add(vectors)
        
        if ids:
            self.id_map.extend(ids)
        else:
            self.id_map.extend([f"vec_{i}" for i in range(len(self.id_map), len(self.id_map) + len(vectors))])
    
    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict]:
        """
        向量检索
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        if self.index is None:
            return []
        
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        
        import faiss
        faiss.normalize_L2(query_vector)
        
        scores, indices = self.index.search(query_vector, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.id_map):
                results.append({
                    "id": self.id_map[idx],
                    "score": float(score),
                    "index": int(idx)
                })
        
        return results
    
    def save(self, output_path: str):
        """
        保存索引
        
        Args:
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if self.index is not None:
            import faiss
            import tempfile
            import shutil
            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, "faiss_tmp.index")
            faiss.write_index(self.index, tmp_file)
            target_file = output_path + ".index"
            if os.path.exists(target_file):
                os.remove(target_file)
            shutil.move(tmp_file, target_file)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        
        with open(output_path + ".ids", 'w', encoding='utf-8') as f:
            json.dump(self.id_map, f)
        
        logger.info(f"[OK] 索引已保存到: {output_path}")
    
    def load(self, input_path: str):
        """
        加载索引
        
        Args:
            input_path: 输入路径
        """
        if os.path.exists(input_path + ".index"):
            import faiss
            import tempfile
            import shutil
            tmp_dir = tempfile.mkdtemp()
            src_file = input_path + ".index"
            tmp_file = os.path.join(tmp_dir, "faiss_tmp.index")
            shutil.copy2(src_file, tmp_file)
            self.index = faiss.read_index(tmp_file)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        
        if os.path.exists(input_path + ".ids"):
            with open(input_path + ".ids", 'r', encoding='utf-8') as f:
                self.id_map = json.load(f)
        
        logger.info(f"[OK] 索引已从 {input_path} 加载")
