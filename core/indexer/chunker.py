"""
FinRAG 语义感知切片模块

实现基于版面结构的智能切片策略：
1. 标题与下属段落尽量在一个 Chunk
2. 表格独立为一个 Chunk
3. 保持语义完整性
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import os


@dataclass
class Chunk:
    """
    文本块数据结构
    
    Attributes:
        id: 块唯一标识
        text: 文本内容
        source: 来源文件
        page_num: 页码
        bbox: 边界框坐标
        chunk_type: 块类型 (text/table/title)
        parent_id: 父块ID (用于层级关系)
        metadata: 其他元数据
    """
    id: str
    text: str
    source: str = ""
    page_num: int = 0
    bbox: Tuple[float, float, float, float] = None
    chunk_type: str = "text"
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "page_num": self.page_num,
            "bbox": list(self.bbox) if self.bbox else None,
            "chunk_type": self.chunk_type,
            "parent_id": self.parent_id,
            "metadata": self.metadata
        }


class SemanticChunker:
    """
    语义感知切片器
    
    核心原则：
    1. 保持语义完整性 - 不切断句子
    2. 保持结构完整性 - 标题与段落在一起
    3. 表格独立处理 - 不拆分表格
    """
    
    TITLE_PATTERNS = [
        r"^第[一二三四五六七八九十]+章",
        r"^第[一二三四五六七八九十]+节",
        r"^第\d+章",
        r"^第\d+节",
        r"^\d+[、.．]\s*",
        r"^[一二三四五六七八九十]+[、]",
        r"^[\(（]\d+[）\)]",
        r"^[1-9]\d*\.\d+",
        r"^[1-9]\d*\.\d+\.\d+",
    ]
    
    def __init__(self, 
                 chunk_size: int = 512,
                 chunk_overlap: int = 50,
                 min_chunk_size: int = 100,
                 respect_sentence_boundary: bool = True):
        """
        初始化切片器
        
        Args:
            chunk_size: 目标块大小 (字符数)
            chunk_overlap: 块重叠大小
            min_chunk_size: 最小块大小
            respect_sentence_boundary: 是否尊重句子边界
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.respect_sentence_boundary = respect_sentence_boundary
        self.chunk_counter = 0
    
    def chunk_parsed_document(self, parsed_data: Dict, source_file: str = "") -> List[Chunk]:
        """
        对解析后的文档进行切片
        
        Args:
            parsed_data: 解析后的文档数据 (来自 pdf_parser)
            source_file: 源文件名
        
        Returns:
            Chunk 列表
        """
        chunks = []
        
        pages = parsed_data if isinstance(parsed_data, list) else parsed_data.get("pages", [])
        
        for page_data in pages:
            page_num = page_data.get("page_num", 0)
            page_chunks = self._chunk_page(page_data, source_file, page_num)
            chunks.extend(page_chunks)
        
        return chunks
    
    def _chunk_page(self, page_data: Dict, source_file: str, page_num: int) -> List[Chunk]:
        """
        切片单页内容 - 表格独立成chunk，文本按chunk_size切块
        """
        page_chunks = []
        
        # 1. 表格独立成 chunk（不拆分）
        tables = page_data.get("tables", [])
        for table in tables:
            md = table.get("markdown", "")
            if not md:
                data = table.get("data", [])
                if data:
                    md = self._data_to_markdown(data)
            if md and len(md.strip()) >= self.min_chunk_size:
                self.chunk_counter += 1
                chunk_with_source = f"[{source_file} 第{page_num}页] {md}"
                page_chunks.append(Chunk(
                    id=f"chunk_{self.chunk_counter}",
                    text=chunk_with_source,
                    source=source_file,
                    page_num=page_num,
                    bbox=tuple(table.get("bbox", [])) if table.get("bbox") else None,
                    chunk_type="table",
                    metadata={"has_table": True}
                ))
        
        # 2. 收集文本块（排除表格中的文本，避免与独立表格chunk重复）
        text_blocks = page_data.get("text_blocks", [])
        if not text_blocks:
            return page_chunks
        
        # 3. 合并文本后按chunk_size切块
        full_text = ""
        for tb in text_blocks:
            text = tb.get("text", "").strip()
            if text:
                if full_text:
                    full_text += "\n"
                full_text += text
        
        if not full_text.strip():
            return page_chunks
        
        start = 0
        while start < len(full_text):
            end = min(start + self.chunk_size, len(full_text))
            
            if end < len(full_text) and self.respect_sentence_boundary:
                for sep in ["。", "！", "？", "\n", ".", "!", "?"]:
                    adjust = full_text.rfind(sep, start, end)
                    if adjust > start + self.min_chunk_size:
                        end = adjust + 1
                        break
            
            chunk_text = full_text[start:end].strip()
            if len(chunk_text) >= self.min_chunk_size or len(page_chunks) == 0:
                self.chunk_counter += 1
                chunk_with_source = f"[{source_file} 第{page_num}页] {chunk_text}"
                page_chunks.append(Chunk(
                    id=f"chunk_{self.chunk_counter}",
                    text=chunk_with_source,
                    source=source_file,
                    page_num=page_num,
                    chunk_type="text",
                    metadata={"has_table": False}
                ))
            
            start = end - self.chunk_overlap if end < len(full_text) else len(full_text)
        
        return page_chunks
    
    def _create_table_chunk(self, table: Dict, source_file: str, page_num: int) -> Optional[Chunk]:
        """
        为表格创建独立 Chunk
        
        Args:
            table: 表格数据
            source_file: 源文件
            page_num: 页码
        
        Returns:
            表格 Chunk
        """
        markdown = table.get("markdown", "")
        if not markdown:
            data = table.get("data", [])
            if data:
                markdown = self._data_to_markdown(data)
        
        if not markdown:
            return None
        
        self.chunk_counter += 1
        return Chunk(
            id=f"chunk_{self.chunk_counter}",
            text=markdown,
            source=source_file,
            page_num=page_num,
            bbox=tuple(table.get("bbox", [])) if table.get("bbox") else None,
            chunk_type="table",
            metadata={"table_data": table.get("data")}
        )
    
    def _chunk_text_blocks(self, text_blocks: List[Dict], source_file: str, page_num: int) -> List[Chunk]:
        """
        切片文本块
        
        Args:
            text_blocks: 文本块列表
            source_file: 源文件
            page_num: 页码
        
        Returns:
            文本 Chunk 列表
        """
        chunks = []
        
        structured_blocks = self._structure_text_blocks(text_blocks)
        
        current_text = ""
        current_blocks = []
        
        for block in structured_blocks:
            block_text = block.get("text", "")
            block_type = block.get("block_type", "text")
            
            if block_type == "title" and current_text:
                if len(current_text) >= self.min_chunk_size:
                    chunk = self._create_text_chunk(current_text, current_blocks, source_file, page_num)
                    chunks.append(chunk)
                current_text = ""
                current_blocks = []
            
            if current_text and len(current_text) + len(block_text) > self.chunk_size:
                if len(current_text) >= self.min_chunk_size:
                    chunk = self._create_text_chunk(current_text, current_blocks, source_file, page_num)
                    chunks.append(chunk)
                    overlap_text = self._get_overlap_text(current_text)
                    current_text = overlap_text + block_text
                    current_blocks = [block]
                else:
                    current_text += "\n" + block_text
                    current_blocks.append(block)
            else:
                if current_text:
                    current_text += "\n" + block_text
                else:
                    current_text = block_text
                current_blocks.append(block)
        
        if current_text and len(current_text) >= self.min_chunk_size:
            chunk = self._create_text_chunk(current_text, current_blocks, source_file, page_num)
            chunks.append(chunk)
        
        return chunks
    
    def _structure_text_blocks(self, text_blocks: List[Dict]) -> List[Dict]:
        """
        结构化文本块 (识别标题层级)
        
        Args:
            text_blocks: 原始文本块
        
        Returns:
            结构化后的文本块
        """
        structured = []
        
        for block in text_blocks:
            text = block.get("text", "").strip()
            if not text:
                continue
            
            is_title = self._is_title(text)
            
            structured_block = block.copy()
            structured_block["block_type"] = "title" if is_title else "text"
            structured.append(structured_block)
        
        return structured
    
    def _is_title(self, text: str) -> bool:
        """
        判断文本是否为标题
        
        Args:
            text: 文本内容
        
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
    
    def _create_text_chunk(self, text: str, blocks: List[Dict], source_file: str, page_num: int) -> Chunk:
        """
        创建文本 Chunk
        
        Args:
            text: 文本内容
            blocks: 原始块列表
            source_file: 源文件
            page_num: 页码
        
        Returns:
            文本 Chunk
        """
        self.chunk_counter += 1
        
        bbox = None
        if blocks:
            bboxes = [b.get("bbox") for b in blocks if b.get("bbox")]
            if bboxes:
                bbox = self._merge_bboxes(bboxes)
        
        return Chunk(
            id=f"chunk_{self.chunk_counter}",
            text=text.strip(),
            source=source_file,
            page_num=page_num,
            bbox=bbox,
            chunk_type="text"
        )
    
    def _get_overlap_text(self, text: str) -> str:
        """
        获取重叠部分的文本
        
        Args:
            text: 原文本
        
        Returns:
            重叠部分文本
        """
        if len(text) <= self.chunk_overlap:
            return text
        
        overlap_text = text[-self.chunk_overlap:]
        
        sentence_end = max(
            overlap_text.rfind("。"),
            overlap_text.rfind("！"),
            overlap_text.rfind("？"),
            overlap_text.rfind("."),
            overlap_text.rfind("!"),
            overlap_text.rfind("?")
        )
        
        if sentence_end > 0:
            return overlap_text[sentence_end + 1:]
        
        return overlap_text
    
    def _merge_bboxes(self, bboxes: List) -> Tuple:
        """
        合并多个边界框
        
        Args:
            bboxes: 边界框列表
        
        Returns:
            合并后的边界框
        """
        if not bboxes:
            return None
        
        x0 = min(b[0] for b in bboxes if b and len(b) >= 4)
        y0 = min(b[1] for b in bboxes if b and len(b) >= 4)
        x1 = max(b[2] for b in bboxes if b and len(b) >= 4)
        y1 = max(b[3] for b in bboxes if b and len(b) >= 4)
        
        return (x0, y0, x1, y1)
    
    def _data_to_markdown(self, data: List[List]) -> str:
        """
        表格数据转 Markdown
        
        Args:
            data: 表格数据
        
        Returns:
            Markdown 字符串
        """
        if not data:
            return ""
        
        lines = []
        for i, row in enumerate(data):
            row_str = " | ".join(str(cell) if cell else "" for cell in row)
            lines.append(f"| {row_str} |")
            if i == 0:
                lines.append(f"| {' | '.join(['---'] * len(row))} |")
        
        return "\n".join(lines)
    
    def save_chunks(self, chunks: List[Chunk], output_path: str):
        """
        保存切片结果
        
        Args:
            chunks: Chunk 列表
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = [chunk.to_dict() for chunk in chunks]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 已保存 {len(chunks)} 个切片到: {output_path}")
    
    @staticmethod
    def load_chunks(input_path: str) -> List[Chunk]:
        """
        加载切片结果
        
        Args:
            input_path: 输入路径
        
        Returns:
            Chunk 列表
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = []
        for item in data:
            chunk = Chunk(
                id=item["id"],
                text=item["text"],
                source=item.get("source", ""),
                page_num=item.get("page_num", 0),
                bbox=tuple(item["bbox"]) if item.get("bbox") else None,
                chunk_type=item.get("chunk_type", "text"),
                parent_id=item.get("parent_id"),
                metadata=item.get("metadata", {})
            )
            chunks.append(chunk)
        
        return chunks
