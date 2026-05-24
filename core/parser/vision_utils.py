"""
FinRAG 视觉处理工具模块

提供图像处理、版面分析辅助功能
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image


class ImageProcessor:
    """
    图像处理器
    
    功能：
    1. 图像预处理
    2. 版面分析辅助
    3. 图片提取
    """
    
    @staticmethod
    def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        图像预处理以优化 OCR 效果
        
        Args:
            image: 原始图像 (numpy 数组)
        
        Returns:
            预处理后的图像
        """
        if image is None:
            return None
        
        gray = image if len(image.shape) == 2 else np.mean(image, axis=2)
        
        min_val = np.min(gray)
        max_val = np.max(gray)
        if max_val - min_val > 0:
            normalized = (gray - min_val) / (max_val - min_val) * 255
        else:
            normalized = gray
        
        return normalized.astype(np.uint8)
    
    @staticmethod
    def detect_blank_regions(image: np.ndarray, 
                            threshold: float = 240,
                            min_area: int = 1000) -> List[Tuple[int, int, int, int]]:
        """
        检测图像中的空白区域 (可能为图片区域)
        
        Args:
            image: 输入图像
            threshold: 空白阈值 (像素值高于此值认为是空白)
            min_area: 最小区域面积
        
        Returns:
            空白区域坐标列表 [(x0, y0, x1, y1), ...]
        """
        if image is None:
            return []
        
        if len(image.shape) == 3:
            gray = np.mean(image, axis=2)
        else:
            gray = image
        
        binary = (gray > threshold).astype(np.uint8)
        
        regions = []
        
        return regions
    
    @staticmethod
    def crop_image(image: Image.Image, bbox: Tuple[float, float, float, float]) -> Image.Image:
        """
        根据边界框裁剪图像
        
        Args:
            image: PIL 图像
            bbox: (x0, y0, x1, y1)
        
        Returns:
            裁剪后的图像
        """
        if image is None or bbox is None:
            return None
        
        x0, y0, x1, y1 = bbox
        return image.crop((x0, y0, x1, y1))
    
    @staticmethod
    def calculate_overlap(bbox1: Tuple[float, float, float, float],
                          bbox2: Tuple[float, float, float, float]) -> float:
        """
        计算两个边界框的重叠度 (IoU)
        
        Args:
            bbox1: 第一个边界框
            bbox2: 第二个边界框
        
        Returns:
            IoU 值 [0, 1]
        """
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2
        
        x0_i = max(x0_1, x0_2)
        y0_i = max(y0_1, y0_2)
        x1_i = min(x1_1, x1_2)
        y1_i = min(y1_1, y1_2)
        
        if x0_i >= x1_i or y0_i >= y1_i:
            return 0.0
        
        inter_area = (x1_i - x0_i) * (y1_i - y0_i)
        
        area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
        area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
        
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


class LayoutDetector:
    """
    版面检测器
    
    功能：
    1. 基于坐标的版面分析
    2. 文本/表格/图片区域分类
    """
    
    def __init__(self, 
                 page_width: float,
                 page_height: float,
                 header_threshold: float = 0.15,
                 footer_threshold: float = 0.1):
        """
        初始化版面检测器
        
        Args:
            page_width: 页面宽度
            page_height: 页面高度
            header_threshold: 页眉区域阈值
            footer_threshold: 页脚区域阈值
        """
        self.page_width = page_width
        self.page_height = page_height
        self.header_height = page_height * header_threshold
        self.footer_start = page_height * (1 - footer_threshold)
    
    def classify_region(self, bbox: Tuple[float, float, float, float]) -> str:
        """
        分类区域类型
        
        Args:
            bbox: (x0, y0, x1, y1)
        
        Returns:
            区域类型: header/footer/text/table/figure
        """
        x0, y0, x1, y1 = bbox
        
        if y1 < self.header_height:
            return "header"
        
        if y0 > self.footer_start:
            return "footer"
        
        width = x1 - x0
        height = y1 - y0
        
        if height > width * 0.3:
            return "text"
        
        if width > self.page_width * 0.8:
            return "table"
        
        return "text"
    
    def is_valid_content(self, bbox: Tuple[float, float, float, float]) -> bool:
        """
        判断是否为有效内容区域 (排除页眉页脚)
        
        Args:
            bbox: 边界框
        
        Returns:
            是否为有效内容
        """
        x0, y0, x1, y1 = bbox
        
        if y1 < self.header_height:
            return False
        
        if y0 > self.footer_start:
            return False
        
        return True
