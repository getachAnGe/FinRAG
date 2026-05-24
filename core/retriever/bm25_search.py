"""
FinRAG BM25 关键词检索模块

实现 BM25 算法进行关键词检索
适用于金融术语的精确匹配
"""

import os
import json
import math
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import logging

logger = logging.getLogger(__name__)

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba not installed, falling back to simple tokenization")


class BM25Tokenizer:
    """
    BM25 分词器
    
    支持：
    1. 中文分词 (jieba)
    2. 英文分词
    3. 金融术语识别
    """
    
    FINANCE_TERMS = {
        "摊余成本法", "公允价值", "净资产收益率", "市盈率", "市净率",
        "资产负债表", "利润表", "现金流量表", "所有者权益", "营业收入",
        "净利润", "毛利率", "净利率", "ROE", "ROA", "EBITDA",
        "同比增长", "环比增长", "复合增长率", "年化收益率",
        "股票", "债券", "基金", "期货", "期权", "ETF",
        "多头", "空头", "做多", "做空", "对冲", "套利",
        "归属于上市公司股东的净利润", "归属于母公司所有者的净利润",
        "加权平均净资产收益率", "基本每股收益", "每股收益",
        "研发投入", "研发费用", "总资产", "资产负债率"
    }
    
    def __init__(self):
        """
        初始化分词器
        """
        self.stopwords = self._load_stopwords()
        if JIEBA_AVAILABLE:
            self._load_jieba_userdict()
    
    def _load_stopwords(self) -> set:
        """
        加载停用词
        
        Returns:
            停用词集合
        """
        stopwords = {
            "的", "是", "在", "了", "和", "与", "或", "等", "及",
            "这", "那", "有", "为", "以", "于", "上", "下", "中",
            "第", "页", "年", "月", "日", "元", "万元", "亿元",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below"
        }
        return stopwords
    
    def _load_jieba_userdict(self):
        """
        加载自定义词典（公司名和金融术语）
        """
        import tempfile
        user_dict = "\n".join(self.FINANCE_TERMS)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write(user_dict)
            temp_path = f.name
        
        try:
            jieba.load_userdict(temp_path)
        finally:
            os.unlink(temp_path)
    
    def tokenize(self, text: str) -> List[str]:
        """
        分词
        
        Args:
            text: 输入文本
        
        Returns:
            词项列表
        """
        tokens = []
        
        for term in self.FINANCE_TERMS:
            if term in text:
                tokens.append(term)
        
        english_pattern = re.compile(r'[a-zA-Z]+')
        number_pattern = re.compile(r'\d+\.?\d*')
        
        english_matches = english_pattern.findall(text)
        for match in english_matches:
            if match.lower() not in self.stopwords and len(match) > 1:
                tokens.append(match.lower())
        
        number_matches = number_pattern.findall(text)
        tokens.extend(number_matches)
        
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_matches = chinese_pattern.findall(text)
        
        if JIEBA_AVAILABLE:
            for match in chinese_matches:
                jieba_tokens = jieba.lcut(match)
                tokens.extend([t for t in jieba_tokens if t and t not in self.stopwords and len(t) > 1])
        else:
            for match in chinese_matches:
                tokens.extend(self._segment_chinese(match))
        
        return [t for t in tokens if t and t not in self.stopwords]
    
    def _segment_chinese(self, text: str) -> List[str]:
        """
        简单中文分词 (正向最大匹配)
        
        Args:
            text: 中文文本
        
        Returns:
            分词结果
        """
        max_len = 4
        tokens = []
        i = 0
        
        while i < len(text):
            matched = False
            for j in range(min(max_len, len(text) - i), 0, -1):
                word = text[i:i+j]
                if word in self.FINANCE_TERMS or j == 1:
                    tokens.append(word)
                    i += j
                    matched = True
                    break
            
            if not matched:
                tokens.append(text[i])
                i += 1
        
        return tokens


class BM25Retriever:
    """
    BM25 检索器
    
    实现标准 BM25 算法：
    score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))
    
    其中：
    - f(qi, D): 词 qi 在文档 D 中的词频
    - |D|: 文档 D 的长度
    - avgdl: 平均文档长度
    - k1, b: 调节参数
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        初始化 BM25 检索器
        
        Args:
            k1: 词频饱和参数
            b: 文档长度归一化参数
        """
        self.k1 = k1
        self.b = b
        self.tokenizer = BM25Tokenizer()
        
        self.doc_store = {}
        self.doc_tokens = {}
        self.doc_lengths = {}
        self.avgdl = 0
        self.doc_count = 0
        self.df = defaultdict(int)
        self.idf = {}
    
    def add_documents(self, doc_ids: List[str], documents: List[Dict]):
        """
        添加文档到索引
        
        Args:
            doc_ids: 文档 ID 列表
            documents: 文档内容列表
        """
        total_length = 0
        
        for doc_id, doc in zip(doc_ids, documents):
            text = doc.get("text", "")
            
            tokens = self.tokenizer.tokenize(text)
            
            self.doc_store[doc_id] = doc
            self.doc_tokens[doc_id] = tokens
            self.doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)
            
            term_freq = Counter(tokens)
            for term in term_freq:
                self.df[term] += 1
        
        self.doc_count = len(doc_ids)
        self.avgdl = total_length / self.doc_count if self.doc_count > 0 else 0
        
        self._compute_idf()
        
        logger.info(f"[OK] BM25 索引构建完成，共 {self.doc_count} 个文档，平均长度 {self.avgdl:.1f}")
    
    def _compute_idf(self):
        """
        计算 IDF 值
        """
        for term, df in self.df.items():
            self.idf[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        BM25 检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        if self.doc_count == 0:
            return []
        
        query_tokens = self.tokenizer.tokenize(query)
        
        scores = {}
        for doc_id, doc_tokens in self.doc_tokens.items():
            score = self._score_document(query_tokens, doc_tokens, doc_id)
            if score > 0:
                scores[doc_id] = score
        
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs[:top_k]:
            results.append({
                "id": doc_id,
                "score": float(score),
                "document": self.doc_store.get(doc_id, {})
            })
        
        return results
    
    def _score_document(self, query_tokens: List[str], doc_tokens: List[str], doc_id: str) -> float:
        """
        计算文档得分
        
        Args:
            query_tokens: 查询词项
            doc_tokens: 文档词项
            doc_id: 文档 ID
        
        Returns:
            BM25 得分
        """
        score = 0.0
        doc_length = self.doc_lengths[doc_id]
        doc_term_freq = Counter(doc_tokens)
        
        for term in query_tokens:
            if term not in self.idf:
                continue
            
            tf = doc_term_freq.get(term, 0)
            if tf == 0:
                continue
            
            idf = self.idf[term]
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avgdl)
            
            score += idf * numerator / denominator
        
        return score
    
    def save(self, path: str):
        """
        保存索引
        
        Args:
            path: 保存路径
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            "k1": self.k1,
            "b": self.b,
            "doc_store": self.doc_store,
            "doc_tokens": self.doc_tokens,
            "doc_lengths": self.doc_lengths,
            "avgdl": self.avgdl,
            "doc_count": self.doc_count,
            "df": dict(self.df),
            "idf": self.idf
        }
        
        with open(f"{path}.bm25.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        logger.info(f"[OK] BM25 索引已保存到: {path}")
    
    def load(self, path: str):
        """
        加载索引
        
        Args:
            path: 索引路径
        """
        if os.path.exists(f"{path}.bm25.json"):
            with open(f"{path}.bm25.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.k1 = data.get("k1", 1.5)
            self.b = data.get("b", 0.75)
            self.doc_store = data.get("doc_store", {})
            self.doc_tokens = data.get("doc_tokens", {})
            self.doc_lengths = data.get("doc_lengths", {})
            self.avgdl = data.get("avgdl", 0)
            self.doc_count = data.get("doc_count", 0)
            self.df = defaultdict(int, data.get("df", {}))
            self.idf = data.get("idf", {})
            
            logger.info(f"[OK] BM25 索引已加载，共 {self.doc_count} 个文档")
    
    def get_document_count(self) -> int:
        """
        获取文档数量
        
        Returns:
            文档数量
        """
        return self.doc_count
