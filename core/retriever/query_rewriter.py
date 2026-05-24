"""简易 Query 改写：对财报类问句自动扩写同义词"""

import re
from typing import Dict, List


class QueryRewriter:
    """
    查询改写器
    在检索前对用户 query 进行同义词扩展，提升召回率。
    """

    def __init__(self, synonyms: Dict[str, List[str]] = None, strategy: str = "expand"):
        """
        Args:
            synonyms: 同义词映射，如 {"归母净利": ["净利润", "归母净利润"]}
            strategy: expand(追加同义词) / replace(替换为同义词)
        """
        self.synonyms = synonyms or {}
        self.strategy = strategy

    def rewrite(self, query: str) -> str:
        """对 query 进行同义词改写，返回改写后的 query"""
        if not self.synonyms:
            return query

        if self.strategy == "replace":
            return self._replace(query)
        else:
            return self._expand(query)

    def _expand(self, query: str) -> str:
        """同义词扩展：在原词旁追加同义词"""
        expanded = query
        for term, syns in self.synonyms.items():
            if term in expanded:
                extra = " ".join(syns[:2])
                expanded = expanded.replace(term, f"{term}{extra}")
        return expanded

    def _replace(self, query: str) -> str:
        """同义词替换：用同义词替换原词"""
        result = query
        for term, syns in self.synonyms.items():
            if term in result:
                result = result.replace(term, syns[0])
        return result
