"""
清理文件，只保留中国金融研报PDF
"""
import os
import shutil

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TEMP_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\temp"

os.makedirs(TEMP_DIR, exist_ok=True)

files = os.listdir(OUTPUT_DIR)

pdf_files = [f for f in files if f.endswith('.pdf') and '同花顺' in f]
html_files = [f for f in files if f.endswith('.html')]

print("="*80)
print("清理文件")
print("="*80)

print(f"\n总文件数: {len(files)}")
print(f"中国金融研报PDF: {len(pdf_files)}")
print(f"SEC财务报告HTML: {len(html_files)}")

print("\n移动SEC财务报告到临时目录...")
for f in html_files:
    src = os.path.join(OUTPUT_DIR, f)
    dst = os.path.join(TEMP_DIR, f)
    shutil.move(src, dst)

print("\n清理完成！")

remaining = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
print(f"\n剩余文件: {len(remaining)} 份")

print("="*80)
