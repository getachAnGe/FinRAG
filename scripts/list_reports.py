"""
列出财务报告文件
"""
import os

PDF_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"

files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]

print(f"财务报告位置: {PDF_DIR}")
print(f"\n总数量: {len(files)} 份")
print("\n前20个文件:")
for i, f in enumerate(sorted(files)[:20], 1):
    print(f"  {i}. {f}")

print("\n后10个文件:")
for i, f in enumerate(sorted(files)[-10:], len(files)-9):
    print(f"  {i}. {f}")

print(f"\n完整路径示例:")
print(f"  {os.path.join(PDF_DIR, files[0])}")
