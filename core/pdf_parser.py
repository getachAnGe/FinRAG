"""
FinRAG 高级 PDF 解析器 v2.0
参考 RAGFlow/DeepDoc 架构设计

核心功能：
1. 版面分析 - 识别文本/表格/图片区域
2. OCR 识别 - 支持扫描件 PDF
3. 乱码检测 - 自动检测并回退到 OCR
4. 表格结构识别 - 提取表格为结构化数据
5. 图片提取 - 提取 PDF 中的图片内容

依赖安装：
    pip install pdfplumber pandas paddleocr paddlepaddle
"""

import pdfplumber
import pandas as pd
import numpy as np
import re
import os
import json
import unicodedata
from io import BytesIO
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from PIL import Image
import warnings
warnings.filterwarnings('ignore')


# ==================== 数据类定义 ====================

@dataclass
class TextBlock:
    """
    文本块数据结构
    
    Attributes:
        text: 文本内容
        x0, y0, x1, y1: 边界框坐标 (左上角和右下角)
        page_num: 所在页码
        block_type: 块类型 (text/table/figure)
        confidence: OCR 置信度 (如果是 OCR 识别的)
    """
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    block_type: str = "text"
    confidence: float = 1.0
    
    @property
    def width(self) -> float:
        """计算宽度"""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """计算高度"""
        return self.y1 - self.y0
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """返回边界框元组"""
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass
class TableBlock:
    """
    表格块数据结构
    
    Attributes:
        data: 表格数据 (二维列表)
        markdown: Markdown 格式表格
        bbox: 边界框坐标
        page_num: 所在页码
        confidence: 识别置信度
    """
    data: List[List[str]]
    markdown: str
    bbox: Tuple[float, float, float, float]
    page_num: int
    confidence: float = 1.0


@dataclass
class ImageBlock:
    """
    图片块数据结构
    
    Attributes:
        image: PIL Image 对象
        caption: 图片标题/说明
        bbox: 边界框坐标
        page_num: 所在页码
    """
    image: Image.Image
    caption: str
    bbox: Tuple[float, float, float, float]
    page_num: int


@dataclass
class ParsedPage:
    """
    解析后的页面数据结构
    
    Attributes:
        page_num: 页码
        text_blocks: 文本块列表
        tables: 表格列表
        images: 图片列表
        page_image: 页面渲染图像 (PIL Image)
    """
    page_num: int
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableBlock] = field(default_factory=list)
    images: List[ImageBlock] = field(default_factory=list)
    page_image: Optional[Image.Image] = None


# ==================== OCR 管理器 ====================

class OCRManager:
    """
    OCR 管理器 - 处理扫描件识别
    
    参考 RAGFlow 设计，支持：
    1. 文字检测 (DB 模型)
    2. 文字识别 (CRNN 模型)
    3. 批量识别优化
    
    使用 PaddleOCR 作为底层引擎，支持 CPU/GPU
    """
    
    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        """
        初始化 OCR 管理器
        
        Args:
            use_gpu: 是否使用 GPU (PyTorch 1.8 环境下建议 CPU)
            lang: 语言，'ch' 为中文，'en' 为英文
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr_engine = None
        self._init_ocr()
    
    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            from paddleocr import PaddleOCR
            print(f"[*] 正在初始化 PaddleOCR (语言: {self.lang})...")
            print("    首次使用会自动下载模型，请确保网络畅通...")
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,           # 使用方向分类器
                lang=self.lang,               # 语言设置
                show_log=False                # 减少日志输出
            )
            print("[OK] OCR 引擎初始化完成")
        except ImportError:
            print("[!] 警告: 未安装 paddleocr，OCR 功能将不可用")
            print("    安装命令: pip install paddleocr paddlepaddle")
            self.ocr_engine = None
        except Exception as e:
            print(f"[!] OCR 引擎初始化失败: {e}")
            print("    将继续使用 pdfplumber 提取文本")
            self.ocr_engine = None
    
    def recognize(self, image: np.ndarray) -> List[TextBlock]:
        """
        识别图像中的文字
        
        Args:
            image: numpy 数组格式的图像 (H, W, C)
        
        Returns:
            TextBlock 列表，包含识别的文字和位置
        """
        if self.ocr_engine is None:
            return []
        
        results = self.ocr_engine.ocr(image, cls=True)
        if not results or not results[0]:
            return []
        
        text_blocks = []
        for line in results[0]:
            if line is None:
                continue
            bbox, (text, confidence) = line
            # bbox 格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            
            block = TextBlock(
                text=text,
                x0=min(x_coords),
                y0=min(y_coords),
                x1=max(x_coords),
                y1=max(y_coords),
                page_num=0,  # 后续设置
                block_type="text",
                confidence=confidence
            )
            text_blocks.append(block)
        
        return text_blocks
    
    def recognize_page(self, page_image: Image.Image, page_num: int) -> List[TextBlock]:
        """
        识别整页图像
        
        Args:
            page_image: PIL Image 对象
            page_num: 页码
        
        Returns:
            该页所有文本块
        """
        # 转为 numpy 数组
        image_array = np.array(page_image)
        blocks = self.recognize(image_array)
        # 设置页码
        for block in blocks:
            block.page_num = page_num
        return blocks


# ==================== 布局分析器 ====================

class LayoutAnalyzer:
    """
    版面分析器 - 识别文档布局结构
    
    参考 RAGFlow 的版面识别逻辑，支持识别：
    1. 文本区域 (text)
    2. 表格区域 (table)
    3. 图片区域 (figure)
    4. 标题区域 (title)
    
    使用简单的启发式规则 + 可选的深度学习模型
    """
    
    # 布局类型定义
    LAYOUT_TEXT = "text"
    LAYOUT_TABLE = "table"
    LAYOUT_FIGURE = "figure"
    LAYOUT_TITLE = "title"
    
    def __init__(self, use_deep_learning: bool = False):
        """
        初始化布局分析器
        
        Args:
            use_deep_learning: 是否使用深度学习模型 (需要更多依赖)
        """
        self.use_dl = use_deep_learning
        self.layout_model = None
        
        if use_deep_learning:
            self._init_dl_model()
    
    def _init_dl_model(self):
        """初始化深度学习布局识别模型"""
        try:
            # 这里可以使用 LayoutLM 或类似的模型
            # 为简化，先使用启发式方法
            print("[*] 深度学习布局模型暂未集成，使用启发式规则")
        except Exception as e:
            print(f"[!] 布局模型初始化失败: {e}")
    
    def analyze(self, page, text_blocks: List[TextBlock], 
                tables: List[TableBlock]) -> Dict[str, List[Any]]:
        """
        分析页面布局
        
        Args:
            page: pdfplumber 页面对象
            text_blocks: 已提取的文本块
            tables: 已提取的表格
        
        Returns:
            按类型分类的布局元素字典
        """
        layouts = {
            self.LAYOUT_TEXT: [],
            self.LAYOUT_TABLE: tables,
            self.LAYOUT_FIGURE: [],
            self.LAYOUT_TITLE: []
        }
        
        # 获取页面尺寸
        page_width = page.width
        page_height = page.height
        
        # 识别标题 (简单启发式：字体大、在顶部)
        for block in text_blocks:
            is_title = self._is_title(block, page_width, page_height)
            if is_title:
                block.block_type = self.LAYOUT_TITLE
                layouts[self.LAYOUT_TITLE].append(block)
            else:
                layouts[self.LAYOUT_TEXT].append(block)
        
        # 识别图片区域 (通过检测大块空白区域或图片对象)
        figures = self._detect_figures(page)
        layouts[self.LAYOUT_FIGURE] = figures
        
        return layouts
    
    def _is_title(self, block: TextBlock, page_width: float, 
                  page_height: float) -> bool:
        """
        判断文本块是否为标题
        
        启发式规则：
        1. 位于页面上半部分
        2. 文字较短
        3. 符合标题模式 (如"第X章"、数字编号等)
        """
        # 标题模式
        title_patterns = [
            r"^第[一二三四五六七八九十]+章",
            r"^第\d+章",
            r"^\d+[、.]\s*",
            r"^[一二三四五六七八九十]+[、]",
            r"^[\(（]\d+[）\)]",
        ]
        
        # 检查是否在页面上半部分
        is_upper = block.y1 < page_height * 0.3
        
        # 检查文字长度 (标题通常较短)
        is_short = len(block.text) < 50
        
        # 检查是否符合标题模式
        matches_pattern = any(re.match(p, block.text.strip()) for p in title_patterns)
        
        return (is_upper and is_short and matches_pattern) or matches_pattern
    
    def _detect_figures(self, page) -> List[ImageBlock]:
        """
        检测页面中的图片
        
        通过分析页面中的图像对象和空白区域
        """
        figures = []
        
        # 获取页面中的所有图像
        images = page.images if hasattr(page, 'images') else []
        
        for img_idx, img_info in enumerate(images):
            # 创建图片块
            bbox = (
                img_info.get('x0', 0),
                img_info.get('y0', 0),
                img_info.get('x1', img_info.get('x0', 0) + img_info.get('width', 0)),
                img_info.get('y1', img_info.get('y0', 0) + img_info.get('height', 0))
            )
            
            # 尝试提取图片
            try:
                cropped = page.within_bbox(bbox).to_image()
                pil_img = cropped.original
                
                figure = ImageBlock(
                    image=pil_img,
                    caption=f"Figure {img_idx + 1}",
                    bbox=bbox,
                    page_num=page.page_number
                )
                figures.append(figure)
            except Exception as e:
                print(f"[!] 提取图片失败: {e}")
                continue
        
        return figures


# ==================== 乱码检测器 ====================

class GarbledTextDetector:
    """
    乱码检测器 - 检测 PDF 提取文本中的乱码
    
    参考 RAGFlow 的设计，检测以下乱码类型：
    1. CID 模式: (cid:123) 格式的未映射字符
    2. PUA 字符: Unicode 私人使用区字符
    3. 字体编码问题: 子集字体导致的乱码
    """
    
    # CID 模式正则表达式
    CID_PATTERN = re.compile(r"\(cid\s*:\s*\d+\s*\)")
    
    # 子集字体前缀模式
    SUBSET_FONT_PATTERN = re.compile(r"^[A-Z0-9]{2,6}\+")
    
    @classmethod
    def is_garbled_char(cls, char: str) -> bool:
        """
        检测单个字符是否为乱码
        
        检测标准：
        1. Unicode 私人使用区 (PUA)
        2. 替换字符 (U+FFFD)
        3. 控制字符
        """
        if not char:
            return False
        
        code_point = ord(char)
        
        # PUA 区域检测
        if 0xE000 <= code_point <= 0xF8FF:
            return True
        if 0xF0000 <= code_point <= 0xFFFFF:
            return True
        if 0x100000 <= code_point <= 0x10FFFF:
            return True
        
        # 替换字符
        if code_point == 0xFFFD:
            return True
        
        # 控制字符 (除了制表符、换行、回车)
        if code_point < 0x20 and char not in ('\t', '\n', '\r'):
            return True
        
        # C1 控制字符
        if 0x80 <= code_point <= 0x9F:
            return True
        
        # Unicode 类别检测
        category = unicodedata.category(char)
        if category in ("Cn", "Cs"):  # 未定义或私有字符
            return True
        
        return False
    
    @classmethod
    def is_garbled_text(cls, text: str, threshold: float = 0.5) -> bool:
        """
        检测文本是否为乱码
        
        Args:
            text: 待检测文本
            threshold: 乱码字符比例阈值，超过则认为是乱码
        
        Returns:
            是否为乱码
        """
        if not text or not text.strip():
            return False
        
        # 检测 CID 模式
        if cls.CID_PATTERN.search(text):
            return True
        
        # 统计乱码字符
        garbled_count = 0
        total_count = 0
        
        for char in text:
            if char.isspace():
                continue
            total_count += 1
            if cls.is_garbled_char(char):
                garbled_count += 1
        
        if total_count == 0:
            return False
        
        return garbled_count / total_count >= threshold
    
    @classmethod
    def is_font_encoding_issue(cls, chars: List[Dict], min_chars: int = 20) -> bool:
        """
        检测是否为字体编码问题导致的乱码
        
        特征：
        1. 使用子集字体
        2. 输出全是 ASCII 标点符号
        3. 没有 CJK 字符
        
        Args:
            chars: 字符信息列表，每个字符包含 'text' 和 'fontname'
            min_chars: 最小字符数阈值
        """
        if not chars or len(chars) < min_chars:
            return False
        
        subset_font_count = 0
        total_non_space = 0
        ascii_punct_count = 0
        cjk_count = 0
        
        for char_info in chars:
            text = char_info.get("text", "")
            fontname = char_info.get("fontname", "")
            
            if not text or text.isspace():
                continue
            
            total_non_space += 1
            
            # 检测子集字体
            if cls.SUBSET_FONT_PATTERN.match(fontname):
                subset_font_count += 1
            
            # 字符类型统计
            code_point = ord(text[0])
            
            # CJK 字符范围
            if (0x2E80 <= code_point <= 0x9FFF or      # CJK 统一表意符号
                0xF900 <= code_point <= 0xFAFF or       # CJK 兼容字符
                0x20000 <= code_point <= 0x2FA1F or     # CJK 扩展
                0xAC00 <= code_point <= 0xD7AF or       # 韩文
                0x3040 <= code_point <= 0x30FF):        # 日文假名
                cjk_count += 1
            # ASCII 标点符号
            elif (0x21 <= code_point <= 0x2F or
                  0x3A <= code_point <= 0x40 or
                  0x5B <= code_point <= 0x60 or
                  0x7B <= code_point <= 0x7E):
                ascii_punct_count += 1
        
        if total_non_space < min_chars:
            return False
        
        # 子集字体比例
        subset_ratio = subset_font_count / total_non_space
        if subset_ratio < 0.3:
            return False
        
        # CJK 比例低 + 标点符号比例高 = 编码问题
        cjk_ratio = cjk_count / total_non_space
        punct_ratio = ascii_punct_count / total_non_space
        
        return cjk_ratio < 0.05 and punct_ratio > 0.4


# ==================== 主解析器 ====================

class FinRAGParser:
    """
    FinRAG 高级 PDF 解析器 v2.0
    
    参考 RAGFlow/DeepDoc 架构，提供企业级 PDF 解析能力：
    
    核心流程：
    1. 页面渲染 → 将 PDF 转为高清图像
    2. 双层提取 → pdfplumber + OCR 双保险
    3. 乱码检测 → 自动识别并回退到 OCR
    4. 版面分析 → 识别文本/表格/图片区域
    5. 表格识别 → 结构化提取表格数据
    6. 图片提取 → 提取并保存 PDF 中的图片
    
    Attributes:
        zoom_factor: 渲染倍率，越大越清晰但越慢 (默认 3，即 216 DPI)
        use_ocr: 是否启用 OCR (扫描件必需)
        ocr_manager: OCR 管理器实例
        layout_analyzer: 布局分析器实例
        enable_garbled_detection: 是否启用乱码检测
    """
    
    def __init__(self, 
                 zoom_factor: int = 3,
                 use_ocr: bool = True,
                 use_gpu: bool = False,
                 ocr_lang: str = 'ch',
                 enable_garbled_detection: bool = True):
        """
        初始化解析器
        
        Args:
            zoom_factor: 渲染倍率 (1-9)，建议 3 或 6
            use_ocr: 是否启用 OCR 功能
            use_gpu: OCR 是否使用 GPU (PyTorch 1.8 建议 CPU)
            ocr_lang: OCR 语言，'ch' 中文，'en' 英文
            enable_garbled_detection: 是否启用乱码检测和自动回退
        """
        self.zoom_factor = zoom_factor
        self.use_ocr = use_ocr
        self.enable_garbled_detection = enable_garbled_detection
        
        # 初始化 OCR 管理器
        self.ocr_manager = None
        if use_ocr:
            self.ocr_manager = OCRManager(use_gpu=use_gpu, lang=ocr_lang)
        
        # 初始化布局分析器
        self.layout_analyzer = LayoutAnalyzer(use_deep_learning=False)
        
        # 存储解析结果
        self.parsed_pages: List[ParsedPage] = []
        self.page_images: List[Image.Image] = []
        
        print(f"[*] FinRAGParser 初始化完成")
        print(f"    - 渲染倍率: {zoom_factor}x ({72 * zoom_factor} DPI)")
        print(f"    - OCR 启用: {use_ocr}")
        print(f"    - 乱码检测: {enable_garbled_detection}")
    
    def parse(self, pdf_path: str, 
              page_from: int = 0, 
              page_to: Optional[int] = None) -> List[ParsedPage]:
        """
        主解析函数 - 解析 PDF 文件
        
        这是入口方法，执行完整的解析流程：
        1. 打开 PDF 文件
        2. 渲染每页为图像
        3. 提取文本 (带乱码检测)
        4. 提取表格
        5. 版面分析
        6. 返回结构化数据
        
        Args:
            pdf_path: PDF 文件路径
            page_from: 起始页码 (0-based)
            page_to: 结束页码 (None 表示到最后)
        
        Returns:
            解析后的页面列表
        """
        print(f"\n{'='*60}")
        print(f"[*] 开始解析 PDF: {pdf_path}")
        print(f"{'='*60}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        
        self.parsed_pages = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            page_to = page_to or total_pages
            
            print(f"[*] PDF 总页数: {total_pages}")
            print(f"[*] 处理范围: 第 {page_from + 1} 页 到 第 {page_to} 页")
            print(f"{'='*60}\n")
            
            for page_idx in range(page_from, min(page_to, total_pages)):
                page = pdf.pages[page_idx]
                print(f"\n[第 {page_idx + 1}/{total_pages} 页]")
                print("-" * 40)
                
                # 解析单页
                parsed_page = self._parse_page(page, page_idx)
                self.parsed_pages.append(parsed_page)
                
                # 打印解析结果摘要
                self._print_page_summary(parsed_page)
        
        print(f"\n{'='*60}")
        print(f"[OK] 解析完成！共处理 {len(self.parsed_pages)} 页")
        print(f"{'='*60}")
        
        return self.parsed_pages
    
    def _parse_page(self, page, page_idx: int) -> ParsedPage:
        """
        解析单个页面
        
        Args:
            page: pdfplumber 页面对象
            page_idx: 页面索引 (0-based)
        
        Returns:
            解析后的页面对象
        """
        parsed_page = ParsedPage(page_num=page_idx + 1)
        
        # ===== 步骤 1: 渲染页面为图像 =====
        # RAGFlow 核心思想：所有分析基于视觉 (图像)
        print("  [1/5] 渲染页面为图像...")
        page_image = self._render_page_to_image(page)
        parsed_page.page_image = page_image
        self.page_images.append(page_image)
        
        # ===== 步骤 2: 提取原始文本和字符信息 =====
        print("  [2/5] 提取原始文本...")
        raw_text_blocks, raw_chars = self._extract_raw_text(page, page_idx)
        
        # ===== 步骤 3: 乱码检测和 OCR 回退 =====
        print("  [3/5] 乱码检测...")
        text_blocks = self._process_text_with_fallback(
            raw_text_blocks, raw_chars, page_image, page_idx
        )
        parsed_page.text_blocks = text_blocks
        
        # ===== 步骤 4: 提取表格 =====
        print("  [4/5] 提取表格...")
        tables = self._extract_tables_advanced(page, page_idx)
        parsed_page.tables = tables
        
        # ===== 步骤 5: 版面分析 (识别图片、标题等) =====
        print("  [5/5] 版面分析...")
        layouts = self.layout_analyzer.analyze(page, text_blocks, tables)
        parsed_page.images = layouts.get(LayoutAnalyzer.LAYOUT_FIGURE, [])
        
        return parsed_page
    
    def _render_page_to_image(self, page) -> Image.Image:
        """
        将 PDF 页面渲染为 PIL Image
        
        这是视觉分析的基础，RAGFlow 的核心思想。
        渲染倍率 (zoom_factor) 决定图像清晰度：
        - 1x = 72 DPI (标准屏幕)
        - 3x = 216 DPI (推荐，平衡速度和质量)
        - 6x = 432 DPI (高质量，但较慢)
        
        Args:
            page: pdfplumber 页面对象
        
        Returns:
            PIL Image 对象
        """
        # pdfplumber 的 to_image 方法
        resolution = 72 * self.zoom_factor
        page_image = page.to_image(resolution=resolution)
        
        # 获取原始 PIL Image (带注释的用于可视化，原始的用于 OCR)
        return page_image.original
    
    def _extract_raw_text(self, page, page_idx: int) -> Tuple[List[TextBlock], List[Dict]]:
        """
        从 PDF 提取原始文本和字符信息
        
        Args:
            page: pdfplumber 页面对象
            page_idx: 页面索引
        
        Returns:
            (文本块列表, 原始字符信息列表)
        """
        text_blocks = []
        chars_info = []
        
        # 获取字符级别的信息 (用于乱码检测)
        try:
            chars = page.dedupe_chars().chars
            # 过滤掉颜色为白色的字符 (通常是背景)
            chars_info = [c for c in chars if self._has_color(c)]
        except Exception as e:
            print(f"    [!] 提取字符信息失败: {e}")
            chars_info = []
        
        # 提取单词/文本块
        words = page.extract_words(
            keep_blank_chars=True,
            x_tolerance=3,
            y_tolerance=3
        )
        
        for word in words:
            block = TextBlock(
                text=word.get("text", ""),
                x0=word.get("x0", 0),
                y0=word.get("top", 0),
                x1=word.get("x1", 0),
                y1=word.get("bottom", 0),
                page_num=page_idx + 1,
                block_type="text"
            )
            text_blocks.append(block)
        
        return text_blocks, chars_info
    
    def _has_color(self, char_info: Dict) -> bool:
        """
        检查字符是否有颜色 (过滤白色/透明字符)
        
        Args:
            char_info: 字符信息字典
        
        Returns:
            是否有有效颜色
        """
        # 简化的颜色检查
        # 实际应用中可能需要更复杂的逻辑
        ncs = char_info.get("ncs", "")
        if ncs == "DeviceGray":
            stroke = char_info.get("stroking_color")
            non_stroke = char_info.get("non_stroking_color")
            if stroke and stroke[0] == 1 and non_stroke and non_stroke[0] == 1:
                # 白色字符，可能是背景
                text = char_info.get("text", "")
                if re.match(r"[a-zT_\[\]\(\)-]+", text):
                    return False
        return True
    
    def _process_text_with_fallback(self, 
                                    raw_blocks: List[TextBlock], 
                                    raw_chars: List[Dict],
                                    page_image: Image.Image,
                                    page_idx: int) -> List[TextBlock]:
        """
        处理文本，带乱码检测和 OCR 回退
        
        这是关键的质量保障步骤，参考 RAGFlow 设计：
        1. 检测提取的文本是否有乱码
        2. 如果乱码比例高，回退到 OCR
        3. 合并两种来源的结果
        
        Args:
            raw_blocks: pdfplumber 提取的原始文本块
            raw_chars: 原始字符信息
            page_image: 页面图像 (用于 OCR)
            page_idx: 页面索引
        
        Returns:
            处理后的文本块列表
        """
        if not self.enable_garbled_detection or not raw_blocks:
            return raw_blocks
        
        # 检测乱码
        sample_text = "".join([b.text for b in raw_blocks[:20]])  # 取前 20 个块
        is_garbled = GarbledTextDetector.is_garbled_text(sample_text, threshold=0.3)
        is_font_issue = GarbledTextDetector.is_font_encoding_issue(raw_chars, min_chars=20)
        
        if is_garbled or is_font_issue:
            print(f"    [!] 检测到乱码，切换到 OCR 模式")
            
            if self.ocr_manager and self.ocr_manager.ocr_engine:
                # 使用 OCR 重新识别
                ocr_blocks = self.ocr_manager.recognize_page(page_image, page_idx + 1)
                
                if ocr_blocks:
                    print(f"    [OK] OCR 识别到 {len(ocr_blocks)} 个文本块")
                    return ocr_blocks
                else:
                    print(f"    [!] OCR 未识别到文字，使用原始文本")
            else:
                print(f"    [!] OCR 未启用，使用原始文本")
        else:
            print(f"    [OK] 文本正常，使用 pdfplumber 提取结果")
        
        return raw_blocks
    
    def _extract_tables_advanced(self, page, page_idx: int) -> List[TableBlock]:
        """
        高级表格提取
        
        相比 v1.0 的改进：
        1. 更智能的表格设置
        2. 数据清洗
        3. Markdown 格式化
        4. 置信度评估
        
        Args:
            page: pdfplumber 页面对象
            page_idx: 页面索引
        
        Returns:
            表格块列表
        """
        tables = []
        
        # 表格检测设置 (针对金融报表优化)
        table_settings = {
            "vertical_strategy": "lines",      # 垂直线策略
            "horizontal_strategy": "lines",    # 水平线策略
            "intersection_tolerance": 5,        # 交点容差
            "snap_tolerance": 3,                # 对齐容差
            "join_tolerance": 3,                # 连接容差
            "edge_min_length": 10,              # 最小边长
            "min_words_vertical": 3,            # 垂直方向最小字数
            "min_words_horizontal": 1,          # 水平方向最小字数
        }
        
        try:
            found_tables = page.find_tables(table_settings=table_settings)
            
            for table_idx, table in enumerate(found_tables):
                # 提取原始数据
                raw_data = table.extract()
                if not raw_data:
                    continue
                
                # 数据清洗
                df = pd.DataFrame(raw_data)
                
                # 去除全空行和列
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                # 转换为字符串并处理 None
                df = df.fillna('').astype(str)
                
                # 生成 Markdown
                try:
                    markdown = df.to_markdown(index=False)
                except Exception:
                    # 降级处理：简单表格格式
                    markdown = self._simple_table_to_markdown(df.values.tolist())
                
                table_block = TableBlock(
                    data=df.values.tolist(),
                    markdown=markdown,
                    bbox=table.bbox,
                    page_num=page_idx + 1,
                    confidence=1.0  # 可以添加更复杂的置信度计算
                )
                tables.append(table_block)
                
        except Exception as e:
            print(f"    [!] 表格提取失败: {e}")
        
        return tables
    
    def _simple_table_to_markdown(self, data: List[List[str]]) -> str:
        """
        简单表格转 Markdown (降级方案)
        
        Args:
            data: 二维列表数据
        
        Returns:
            Markdown 格式字符串
        """
        if not data:
            return ""
        
        lines = []
        # 表头
        header = " | ".join(str(cell) for cell in data[0])
        lines.append(f"| {header} |")
        
        # 分隔符
        separator = " | ".join(["---"] * len(data[0]))
        lines.append(f"| {separator} |")
        
        # 数据行
        for row in data[1:]:
            row_str = " | ".join(str(cell) for cell in row)
            lines.append(f"| {row_str} |")
        
        return "\n".join(lines)
    
    def _print_page_summary(self, parsed_page: ParsedPage):
        """
        打印页面解析摘要
        
        Args:
            parsed_page: 解析后的页面对象
        """
        text_count = len(parsed_page.text_blocks)
        table_count = len(parsed_page.tables)
        image_count = len(parsed_page.images)
        
        print(f"  摘要:")
        print(f"    - 文本块: {text_count} 个")
        print(f"    - 表格: {table_count} 个")
        print(f"    - 图片: {image_count} 个")
        
        # 打印文本预览
        if parsed_page.text_blocks:
            preview_text = "".join([b.text for b in parsed_page.text_blocks[:3]])
            preview_text = preview_text[:100].replace('\n', ' ')
            print(f"    - 文本预览: {preview_text}...")
    
    def get_full_text(self) -> str:
        """
        获取完整文本内容
        
        Returns:
            所有页面的合并文本
        """
        texts = []
        for page in self.parsed_pages:
            page_texts = [b.text for b in page.text_blocks]
            texts.append(f"\n--- 第 {page.page_num} 页 ---\n")
            texts.append("\n".join(page_texts))
        return "\n".join(texts)
    
    def get_all_tables(self) -> List[TableBlock]:
        """
        获取所有表格
        
        Returns:
            所有页面的表格列表
        """
        tables = []
        for page in self.parsed_pages:
            tables.extend(page.tables)
        return tables
    
    def export_to_markdown(self, output_path: str):
        """
        导出为 Markdown 文件
        
        Args:
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 解析结果\n\n")
            
            for page in self.parsed_pages:
                f.write(f"## 第 {page.page_num} 页\n\n")
                
                # 写入文本
                if page.text_blocks:
                    f.write("### 文本内容\n\n")
                    for block in page.text_blocks:
                        f.write(f"{block.text}\n\n")
                
                # 写入表格
                if page.tables:
                    f.write("### 表格\n\n")
                    for idx, table in enumerate(page.tables):
                        f.write(f"**表格 {idx + 1}**\n\n")
                        f.write(f"{table.markdown}\n\n")
                
                f.write("---\n\n")
        
        print(f"[OK] Markdown 已导出到: {output_path}")
    
    def export_to_json(self, output_path: str):
        """
        导出为 JSON 文件
        
        Args:
            output_path: 输出文件路径
        """
        data = []
        for page in self.parsed_pages:
            page_data = {
                "page_num": page.page_num,
                "text_blocks": [
                    {
                        "text": b.text,
                        "bbox": b.bbox,
                        "type": b.block_type,
                        "confidence": b.confidence
                    }
                    for b in page.text_blocks
                ],
                "tables": [
                    {
                        "data": t.data,
                        "markdown": t.markdown,
                        "bbox": t.bbox
                    }
                    for t in page.tables
                ],
                "images": [
                    {
                        "caption": img.caption,
                        "bbox": img.bbox
                    }
                    for img in page.images
                ]
            }
            data.append(page_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON 已导出到: {output_path}")


# ==================== 测试代码 ====================

if __name__ == "__main__":
    """
    测试 FinRAGParser v2.0
    
    运行方式：
        python parser.py
    
    需要测试 PDF 文件：test_finance_report.pdf
    """
    
    test_pdf = "test_finance_report.pdf"
    
    if not os.path.exists(test_pdf):
        print("[!] 请确保在当前目录下放置测试 PDF 文件: test_finance_report.pdf")
        print("    你可以使用任意 PDF 文件进行测试")
        exit(1)
    
    print("\n" + "="*60)
    print("FinRAGParser v2.0 测试")
    print("="*60 + "\n")
    
    # 初始化解析器
    parser = FinRAGParser(
        zoom_factor=3,           # 3x 渲染倍率 (216 DPI)
        use_ocr=True,            # 启用 OCR
        use_gpu=False,           # CPU 模式 (兼容 PyTorch 1.8)
        ocr_lang='ch',           # 中文 OCR
        enable_garbled_detection=True  # 启用乱码检测
    )
    
    # 解析 PDF
    results = parser.parse(test_pdf)
    
    # 打印完整文本预览
    print("\n" + "="*60)
    print("完整文本预览 (前 1000 字符):")
    print("="*60)
    full_text = parser.get_full_text()
    print(full_text[:1000])
    print("...")
    
    # 导出结果
    print("\n" + "="*60)
    print("导出结果")
    print("="*60)
    
    # 导出 Markdown
    parser.export_to_markdown("output_parsed.md")
    
    # 导出 JSON
    parser.export_to_json("output_parsed.json")
    
    print("\n[OK] 测试完成！")
