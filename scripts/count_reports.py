"""
统计财务报告分布
"""
import os
from collections import defaultdict

PDF_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"

def count_reports():
    """统计报告分布"""
    print("="*80)
    print("财务报告统计")
    print("="*80)
    
    files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    
    industry_count = defaultdict(int)
    year_count = defaultdict(int)
    type_count = defaultdict(int)
    
    for filename in files:
        if filename.startswith(('传媒_', '白酒_', '消费_', '半导体_')):
            parts = filename.replace('.pdf', '').split('_')
            if len(parts) >= 4:
                industry = parts[0]
                year = parts[2]
                report_type = parts[3]
                
                industry_count[industry] += 1
                year_count[year] += 1
                type_count[report_type] += 1
    
    print(f"\n总文件数: {len(files)}")
    print(f"财务报告数: {sum(industry_count.values())}")
    
    print("\n行业分布:")
    for industry, count in sorted(industry_count.items()):
        print(f"  {industry}: {count} 份")
    
    print("\n年份分布:")
    for year, count in sorted(year_count.items()):
        print(f"  {year}年: {count} 份")
    
    print("\n报告类型分布:")
    for report_type, count in sorted(type_count.items()):
        print(f"  {report_type}: {count} 份")
    
    print("\n示例文件:")
    sample_files = [f for f in files if f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))][:10]
    for i, filename in enumerate(sample_files, 1):
        print(f"  {i}. {filename}")
    
    print("="*80)

if __name__ == "__main__":
    count_reports()
