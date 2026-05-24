# -*- coding: utf-8 -*-
"""
测试 FinRAGParser v2.0
"""

import sys
sys.path.insert(0, '.')

# 导入解析器
from pdf_parser import FinRAGParser
import os

print("=" * 60)
print("FinRAGParser v2.0 功能测试")
print("=" * 60)

# 测试 1: 初始化解析器 (不启用 OCR)
print("\n[测试 1] 初始化解析器 (OCR 关闭)...")
try:
    parser = FinRAGParser(
        zoom_factor=2,
        use_ocr=False,
        enable_garbled_detection=False
    )
    print("[OK] 解析器初始化成功！")
    print(f"    - zoom_factor: {parser.zoom_factor}")
    print(f"    - use_ocr: {parser.use_ocr}")
except Exception as e:
    print(f"[FAIL] 初始化失败: {e}")

# 测试 2: 数据类功能
print("\n[测试 2] 数据类功能测试...")
try:
    from pdf_parser import TextBlock, TableBlock, ParsedPage
    
    # 创建文本块
    block = TextBlock(
        text="测试文本",
        x0=10, y0=20, x1=100, y1=30,
        page_num=1
    )
    print(f"[OK] TextBlock 创建成功")
    print(f"    - 文本: {block.text}")
    print(f"    - 尺寸: {block.width:.1f} x {block.height:.1f}")
    
    # 创建表格块
    table = TableBlock(
        data=[["A", "B"], ["C", "D"]],
        markdown="| A | B |\\n|---|---|\\n| C | D |",
        bbox=(0, 0, 100, 100),
        page_num=1
    )
    print(f"[OK] TableBlock 创建成功")
    
    # 创建页面
    page = ParsedPage(page_num=1)
    page.text_blocks.append(block)
    page.tables.append(table)
    print(f"[OK] ParsedPage 创建成功")
    print(f"    - 文本块数: {len(page.text_blocks)}")
    print(f"    - 表格数: {len(page.tables)}")
    
except Exception as e:
    print(f"[FAIL] 数据类测试失败: {e}")

# 测试 3: 乱码检测
print("\n[测试 3] 乱码检测功能测试...")
try:
    from pdf_parser import GarbledTextDetector
    
    # 测试正常文本
    normal_text = "这是一段正常的中文文本。"
    is_garbled = GarbledTextDetector.is_garbled_text(normal_text)
    print(f"[OK] 正常文本检测: {is_garbled} (期望 False)")
    
    # 测试 CID 模式
    cid_text = "这是一段(cid:123)乱码文本"
    is_garbled = GarbledTextDetector.is_garbled_text(cid_text)
    print(f"[OK] CID 乱码检测: {is_garbled} (期望 True)")
    
except Exception as e:
    print(f"[FAIL] 乱码检测测试失败: {e}")

# 测试 4: 如果有 PDF 文件，测试解析
print("\n[测试 4] PDF 解析测试...")
test_pdf = "test_finance_report.pdf"
if os.path.exists(test_pdf):
    try:
        results = parser.parse(test_pdf)
        print(f"[OK] PDF 解析成功！共 {len(results)} 页")
        
        # 导出测试
        parser.export_to_markdown("test_output.md")
        parser.export_to_json("test_output.json")
        print("[OK] 导出文件成功")
    except Exception as e:
        print(f"[FAIL] PDF 解析失败: {e}")
else:
    print(f"[!] 未找到测试文件: {test_pdf}")
    print("    请放置一个 PDF 文件以进行完整测试")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
