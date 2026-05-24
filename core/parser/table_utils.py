"""
FinRAG 表格处理工具模块

提供表格识别、清洗、格式化等功能
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import re


class TableProcessor:
    """
    表格处理器 - 处理表格识别和格式化
    
    功能：
    1. 表格数据清洗
    2. 表格转 Markdown
    3. 表格转结构化数据
    """
    
    @staticmethod
    def clean_table_data(data: List[List[str]]) -> List[List[str]]:
        """
        清洗表格数据
        
        Args:
            data: 原始表格数据
        
        Returns:
            清洗后的表格数据
        """
        if not data:
            return []
        
        df = pd.DataFrame(data)
        
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        df = df.fillna('')
        df = df.astype(str)
        
        for col in df.columns:
            df[col] = df[col].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
        
        return df.values.tolist()
    
    @staticmethod
    def to_markdown(data: List[List[str]], has_header: bool = True) -> str:
        """
        表格转 Markdown 格式
        
        Args:
            data: 表格数据
            has_header: 是否有表头
        
        Returns:
            Markdown 格式字符串
        """
        if not data:
            return ""
        
        lines = []
        header = " | ".join(str(cell) for cell in data[0])
        lines.append(f"| {header} |")
        
        separator = " | ".join(["---"] * len(data[0]))
        lines.append(f"| {separator} |")
        
        start_row = 1 if has_header else 0
        for row in data[start_row:]:
            row_str = " | ".join(str(cell) for cell in row)
            lines.append(f"| {row_str} |")
        
        return "\n".join(lines)
    
    @staticmethod
    def detect_header_row(data: List[List[str]]) -> int:
        """
        检测表头行位置
        
        Args:
            data: 表格数据
        
        Returns:
            表头行索引，-1 表示未检测到
        """
        if not data or len(data) < 2:
            return 0
        
        for idx, row in enumerate(data[:3]):
            if all(isinstance(cell, str) and not cell.isdigit() for cell in row if cell):
                if idx == 0 or (idx > 0 and any(data[idx-1])):
                    return idx
        
        return 0
    
    @staticmethod
    def merge_cells(data: List[List[str]], 
                    row_start: int, row_end: int, 
                    col_start: int, col_end: int) -> List[List[str]]:
        """
        处理合并单元格
        
        Args:
            data: 原始数据
            row_start: 起始行
            row_end: 结束行
            col_start: 起始列
            col_end: 结束列
        
        Returns:
            处理后的数据
        """
        if not data:
            return []
        
        result = [row[:] for row in data]
        
        merged_value = " ".join(
            str(data[r][c]) 
            for r in range(row_start, min(row_end + 1, len(data)))
            for c in range(col_start, min(col_end + 1, len(data[0])))
            if data[r][c]
        )
        
        for r in range(row_start, min(row_end + 1, len(data))):
            for c in range(col_start, min(col_end + 1, len(data[0]))):
                if r == row_start and c == col_start:
                    result[r][c] = merged_value
                else:
                    result[r][c] = ""
        
        return result
    
    @staticmethod
    def extract_table_from_text(text: str) -> Optional[List[List[str]]]:
        """
        从文本中提取表格结构
        
        Args:
            text: 包含表格的文本
        
        Returns:
            提取的表格数据，如果未找到则返回 None
        """
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return None
        
        table_data = []
        for line in lines:
            if any(c in line for c in ['\t', '|']):
                cells = re.split(r'[\t|]', line.strip('|').strip())
                cells = [c.strip() for c in cells if c.strip()]
                if cells:
                    table_data.append(cells)
            else:
                if table_data:
                    break
        
        return table_data if len(table_data) >= 2 else None
