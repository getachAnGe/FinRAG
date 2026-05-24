"""
FinRAG 增强版 PDF 解析器 v3.0

结合 PyMuPDF + pdfplumber 双引擎解析
参考 RAGFlow DeepDoc 架构设计

核心功能：
1. PyMuPDF 文本提取 - 处理多栏排版
2. pdfplumber 表格解析 - 结构化表格提取
3. 版面分析 - 识别标题/正文/表格/图片/页眉页脚
4. 乱码检测与 OCR 回退
5. 坐标回溯 - 支持 Source 高亮
"""

import os
import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """
    文本块数据结构
    
    Attributes:
        text: 文本内容
        bbox: 边界框 (x0, y0, x1, y1)
        page_num: 页码
        block_type: 块类型 (text/table/title/figure/header/footer)
        confidence: 置信度
        source: 来源引擎 (pymupdf/pdfplumber/ocr)
    """
    text: str
    bbox: Tuple[float, float, float, float]
    page_num: int
    block_type: str = "text"
    confidence: float = 1.0
    source: str = "pymupdf"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TableBlock:
    """
    表格块数据结构
    
    Attributes:
        data: 表格数据 (二维列表)
        markdown: Markdown 格式
        bbox: 边界框
        page_num: 页码
        headers: 表头
        row_count: 行数
        col_count: 列数
    """
    data: List[List[str]]
    markdown: str
    bbox: Tuple[float, float, float, float]
    page_num: int
    headers: List[str] = field(default_factory=list)
    row_count: int = 0
    col_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "data": self.data,
            "markdown": self.markdown,
            "bbox": list(self.bbox) if self.bbox else None,
            "page_num": self.page_num,
            "headers": self.headers,
            "row_count": self.row_count,
            "col_count": self.col_count
        }


@dataclass
class ParsedPage:
    """
    解析后的页面数据
    
    Attributes:
        page_num: 页码
        width: 页面宽度
        height: 页面高度
        text_blocks: 文本块列表
        tables: 表格列表
        layout_type: 版面类型 (single_column/double_column)
    """
    page_num: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableBlock] = field(default_factory=list)
    layout_type: str = "single_column"
    
    def to_dict(self) -> Dict:
        return {
            "page_num": self.page_num,
            "width": self.width,
            "height": self.height,
            "text_blocks": [b.to_dict() for b in self.text_blocks],
            "tables": [t.to_dict() for t in self.tables],
            "layout_type": self.layout_type
        }


class PyMuPDFExtractor:
    """
    PyMuPDF 文本提取器
    
    优势：
    1. 快速文本提取
    2. 支持多栏排版检测
    3. 精确的字符坐标
    """
    
    def __init__(self, detect_multi_column: bool = True):
        """
        初始化
        
        Args:
            detect_multi_column: 是否检测多栏排版
        """
        self.detect_multi_column = detect_multi_column
    
    def extract_page(self, page, page_num: int) -> Tuple[List[TextBlock], str]:
        """
        提取单页文本
        
        Args:
            page: PyMuPDF 页面对象
            page_num: 页码
        
        Returns:
            (文本块列表, 版面类型)
        """
        text_blocks = []
        
        blocks = page.get_text("dict", flags=11)["blocks"]
        
        layout_type = self._detect_layout(blocks, page.rect.width)
        
        for block in blocks:
            if block.get("type") != 0:
                continue
            
            lines = block.get("lines", [])
            block_text = ""
            
            for line in lines:
                for span in line.get("spans", []):
                    block_text += span.get("text", "")
                block_text += "\n"
            
            block_text = block_text.strip()
            if not block_text:
                continue
            
            bbox = (
                block.get("bbox", (0, 0, 0, 0))[0],
                block.get("bbox", (0, 0, 0, 0))[1],
                block.get("bbox", (0, 0, 0, 0))[2],
                block.get("bbox", (0, 0, 0, 0))[3]
            )
            
            text_block = TextBlock(
                text=block_text,
                bbox=bbox,
                page_num=page_num,
                block_type="text",
                source="pymupdf"
            )
            text_blocks.append(text_block)
        
        return text_blocks, layout_type
    
    def _detect_layout(self, blocks: List[Dict], page_width: float) -> str:
        """
        检测版面类型 (单栏/双栏)
        
        Args:
            blocks: 块列表
            page_width: 页面宽度
        
        Returns:
            版面类型
        """
        if not self.detect_multi_column:
            return "single_column"
        
        left_blocks = 0
        right_blocks = 0
        center_threshold = page_width / 2
        
        for block in blocks:
            if block.get("type") != 0:
                continue
            
            bbox = block.get("bbox", (0, 0, 0, 0))
            block_center = (bbox[0] + bbox[2]) / 2
            
            if block_center < center_threshold:
                left_blocks += 1
            else:
                right_blocks += 1
        
        if left_blocks > 3 and right_blocks > 3:
            return "double_column"
        
        return "single_column"


class PDFPlumberTableExtractor:
    """
    pdfplumber 表格提取器
    
    优势：
    1. 精确的表格结构识别
    2. 支持合并单元格检测
    3. 表格转 Markdown
    """
    
    def __init__(self, table_settings: Dict = None):
        """
        初始化
        
        Args:
            table_settings: 表格检测设置
        """
        self.table_settings = table_settings or {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3
        }
    
    def extract_tables(self, page, page_num: int) -> List[TableBlock]:
        """
        提取页面中的表格
        
        Args:
            page: pdfplumber 页面对象
            page_num: 页码
        
        Returns:
            表格块列表
        """
        tables = []
        
        try:
            found_tables = page.find_tables(table_settings=self.table_settings)
            
            for table in found_tables:
                raw_data = table.extract()
                if not raw_data:
                    continue
                
                cleaned_data = self._clean_table_data(raw_data)
                
                markdown = self._to_markdown(cleaned_data)
                
                headers = cleaned_data[0] if cleaned_data else []
                
                table_block = TableBlock(
                    data=cleaned_data,
                    markdown=markdown,
                    bbox=table.bbox,
                    page_num=page_num,
                    headers=headers,
                    row_count=len(cleaned_data),
                    col_count=len(cleaned_data[0]) if cleaned_data else 0
                )
                tables.append(table_block)
                
        except Exception as e:
            logger.warning(f"表格提取失败 (页 {page_num}): {e}")
        
        return tables
    
    def _clean_table_data(self, data: List[List]) -> List[List[str]]:
        """
        清洗表格数据
        
        Args:
            data: 原始数据
        
        Returns:
            清洗后的数据
        """
        cleaned = []
        for row in data:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    cleaned_row.append(str(cell).strip())
            cleaned.append(cleaned_row)
        
        return cleaned
    
    def _to_markdown(self, data: List[List[str]]) -> str:
        """
        表格转 Markdown
        
        Args:
            data: 表格数据
        
        Returns:
            Markdown 字符串
        """
        if not data:
            return ""
        
        lines = []
        
        header = " | ".join(str(cell) for cell in data[0])
        lines.append(f"| {header} |")
        
        separator = " | ".join(["---"] * len(data[0]))
        lines.append(f"| {separator} |")
        
        for row in data[1:]:
            row_str = " | ".join(str(cell) for cell in row)
            lines.append(f"| {row_str} |")
        
        return "\n".join(lines)


class LayoutAnalyzer:
    """
    版面分析器
    
    参考 RAGFlow DeepDoc 设计
    识别：标题/正文/表格/图片/页眉页脚
    """
    
    TITLE_PATTERNS = [
        r"^第[一二三四五六七八九十]+[章节]",
        r"^第\d+[章节]",
        r"^\d+[、.．]\s*\S+",
        r"^[一二三四五六七八九十]+[、]\s*\S+",
        r"^[\(（]\d+[）\)]\s*\S+",
        r"^[1-9]\d*\.\d+\s+\S+",
    ]
    
    def __init__(self, 
                 header_threshold: float = 0.15,
                 footer_threshold: float = 0.1):
        """
        初始化
        
        Args:
            header_threshold: 页眉区域阈值
            footer_threshold: 页脚区域阈值
        """
        self.header_threshold = header_threshold
        self.footer_threshold = footer_threshold
    
    def analyze(self, 
                text_blocks: List[TextBlock],
                page_height: float) -> List[TextBlock]:
        """
        分析并分类文本块
        
        Args:
            text_blocks: 文本块列表
            page_height: 页面高度
        
        Returns:
            分类后的文本块
        """
        header_height = page_height * self.header_threshold
        footer_start = page_height * (1 - self.footer_threshold)
        
        for block in text_blocks:
            y0, y1 = block.bbox[1], block.bbox[3]
            
            if y1 < header_height:
                block.block_type = "header"
            elif y0 > footer_start:
                block.block_type = "footer"
            elif self._is_title(block.text):
                block.block_type = "title"
        
        return text_blocks
    
    def _is_title(self, text: str) -> bool:
        """
        判断是否为标题
        
        Args:
            text: 文本
        
        Returns:
            是否为标题
        """
        text = text.strip()
        
        if len(text) > 100:
            return False
        
        for pattern in self.TITLE_PATTERNS:
            if re.match(pattern, text):
                return True
        
        return False
    
    def filter_content(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """
        过滤非内容块 (页眉页脚)
        
        Args:
            text_blocks: 文本块列表
        
        Returns:
            过滤后的文本块
        """
        return [
            block for block in text_blocks
            if block.block_type not in ["header", "footer"]
        ]


class GarbledTextDetector:
    """
    乱码检测器
    
    检测 CID 模式、PUA 字符等乱码类型
    """
    
    CID_PATTERN = re.compile(r"\(cid\s*:\s*\d+\s*\)")
    
    @classmethod
    def is_garbled(cls, text: str, threshold: float = 0.3) -> bool:
        """
        检测文本是否乱码
        
        Args:
            text: 文本
            threshold: 乱码比例阈值
        
        Returns:
            是否为乱码
        """
        if not text:
            return False
        
        if cls.CID_PATTERN.search(text):
            return True
        
        garbled_count = 0
        total_count = 0
        
        for char in text:
            if char.isspace():
                continue
            total_count += 1
            
            code = ord(char)
            if 0xE000 <= code <= 0xF8FF:
                garbled_count += 1
            elif code == 0xFFFD:
                garbled_count += 1
        
        if total_count == 0:
            return False
        
        return garbled_count / total_count >= threshold


class EnhancedPDFParser:
    """
    增强版 PDF 解析器
    
    双引擎架构：PyMuPDF + pdfplumber
    """
    
    def __init__(self, 
                 use_pymupdf: bool = True,
                 use_pdfplumber: bool = True,
                 detect_multi_column: bool = True,
                 detect_header_footer: bool = True,
                 header_threshold: float = 0.15,
                 footer_threshold: float = 0.1,
                 garbled_threshold: float = 0.3,
                 table_settings: Dict = None):
        """
        初始化解析器
        
        Args:
            use_pymupdf: 是否使用 PyMuPDF
            use_pdfplumber: 是否使用 pdfplumber
            detect_multi_column: 是否检测多栏
            detect_header_footer: 是否检测页眉页脚
            header_threshold: 页眉阈值
            footer_threshold: 页脚阈值
            garbled_threshold: 乱码阈值
            table_settings: 表格设置
        """
        self.use_pymupdf = use_pymupdf
        self.use_pdfplumber = use_pdfplumber
        self.garbled_threshold = garbled_threshold
        
        self.pymupdf_extractor = PyMuPDFExtractor(detect_multi_column)
        self.table_extractor = PDFPlumberTableExtractor(table_settings)
        self.layout_analyzer = LayoutAnalyzer(header_threshold, footer_threshold)
        
        logger.info("[*] EnhancedPDFParser 初始化完成")
    
    def parse(self, pdf_path: str) -> List[ParsedPage]:
        """
        解析 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            解析后的页面列表
        """
        logger.info(f"[*] 开始解析: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        parsed_pages = []
        
        if self.use_pymupdf:
            parsed_pages = self._parse_with_pymupdf(pdf_path)
        
        if self.use_pdfplumber:
            self._extract_tables_with_pdfplumber(pdf_path, parsed_pages)
        
        logger.info(f"[OK] 解析完成，共 {len(parsed_pages)} 页")
        
        return parsed_pages
    
    def _parse_with_pymupdf(self, pdf_path: str) -> List[ParsedPage]:
        """
        使用 PyMuPDF 解析
        
        Args:
            pdf_path: PDF 路径
        
        Returns:
            页面列表
        """
        try:
            import fitz
        except ImportError:
            logger.error("[!] PyMuPDF 未安装，请运行: pip install pymupdf")
            return []
        
        parsed_pages = []
        
        doc = fitz.open(pdf_path)
        
        for page_num, page in enumerate(doc, 1):
            text_blocks, layout_type = self.pymupdf_extractor.extract_page(page, page_num)
            
            text_blocks = self.layout_analyzer.analyze(text_blocks, page.rect.height)
            
            parsed_page = ParsedPage(
                page_num=page_num,
                width=page.rect.width,
                height=page.rect.height,
                text_blocks=text_blocks,
                layout_type=layout_type
            )
            parsed_pages.append(parsed_page)
        
        doc.close()
        
        return parsed_pages
    
    def _extract_tables_with_pdfplumber(self, 
                                        pdf_path: str, 
                                        parsed_pages: List[ParsedPage]):
        """
        使用 pdfplumber 提取表格
        
        Args:
            pdf_path: PDF 路径
            parsed_pages: 已解析的页面列表
        """
        try:
            import pdfplumber
        except ImportError:
            logger.error("[!] pdfplumber 未安装，请运行: pip install pdfplumber")
            return
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if page_num <= len(parsed_pages):
                    tables = self.table_extractor.extract_tables(page, page_num)
                    parsed_pages[page_num - 1].tables = tables
    
    def export_to_json(self, 
                       parsed_pages: List[ParsedPage], 
                       output_path: str):
        """
        导出为 JSON
        
        Args:
            parsed_pages: 解析结果
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = [page.to_dict() for page in parsed_pages]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[OK] 已导出到: {output_path}")
    
    def get_full_text(self, parsed_pages: List[ParsedPage]) -> str:
        """
        获取完整文本
        
        Args:
            parsed_pages: 解析结果
        
        Returns:
            完整文本
        """
        texts = []
        for page in parsed_pages:
            page_text = f"\n--- 第 {page.page_num} 页 ---\n"
            
            for block in page.text_blocks:
                if block.block_type not in ["header", "footer"]:
                    page_text += block.text + "\n"
            
            for table in page.tables:
                page_text += "\n[表格]\n" + table.markdown + "\n"
            
            texts.append(page_text)
        
        return "\n".join(texts)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG PDF 解析器")
    parser.add_argument("--pdf", type=str, required=True, help="PDF 文件路径")
    parser.add_argument("--output", type=str, default="output.json", help="输出路径")
    
    args = parser.parse_args()
    
    pdf_parser = EnhancedPDFParser()
    pages = pdf_parser.parse(args.pdf)
    pdf_parser.export_to_json(pages, args.output)
