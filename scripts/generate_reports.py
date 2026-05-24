"""
快速生成300份金融研报PDF文件
"""

import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

# 行业配置
INDUSTRIES = {
    "传媒": ["分众传媒", "芒果超媒", "光线传媒", "华策影视", "完美世界", "三七互娱", "吉比特", "昆仑万维", "巨人网络", "恺英网络"],
    "白酒": ["贵州茅台", "五粮液", "泸州老窖", "洋河股份", "山西汾酒", "今世缘", "古井贡酒", "酒鬼酒", "水井坊", "舍得酒业"],
    "消费": ["伊利股份", "海天味业", "美的集团", "格力电器", "中国中免", "珀莱雅", "安井食品", "三只松鼠", "良品铺子", "永辉超市"],
    "半导体": ["中芯国际", "韦尔股份", "兆易创新", "北方华创", "紫光国微", "长电科技", "通富微电", "华天科技", "晶方科技", "卓胜微"]
}

TOPICS = ["业绩点评", "行业深度", "公司深度", "财报分析", "事件点评", "调研纪要", "投资策略", "行业周报"]

REPORT_TYPES = ["深度报告", "点评报告", "调研报告", "行业研究", "公司研究"]


def create_simple_pdf(filepath: str, company: str, industry: str, topic: str, date: str):
    """创建简单的PDF文件"""
    
    revenue = round(random.uniform(50, 500), 2)
    growth = round(random.uniform(-10, 30), 2)
    profit = round(random.uniform(5, 50), 2)
    target_price = round(random.uniform(20, 300), 2)
    rating = random.choice(["买入", "增持", "中性", "推荐"])
    
    title = f"{company}{topic}"
    
    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 500 >>
stream
BT
/F1 16 Tf
100 700 Td
({company} - {topic}) Tj
/F1 12 Tf
100 650 Td
(Report Date: {date}) Tj
100 620 Td
(Industry: {industry}) Tj
100 590 Td
(Revenue: {revenue} billion CNY) Tj
100 560 Td
(Growth: {growth}%) Tj
100 530 Td
(Profit: {profit} billion CNY) Tj
100 500 Td
(Target Price: {target_price} CNY) Tj
100 470 Td
(Rating: {rating}) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000260 00000 n 
0000000810 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
890
%%EOF
"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(pdf_content)


def main():
    """主函数"""
    
    print("="*60)
    print("FinRAG 金融研报生成器")
    print("="*60)
    print(f"目标: {TARGET_COUNT} 份研报")
    print(f"输出: {OUTPUT_DIR}")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取已有文件
    existing_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith('RPT_')]
    existing_count = len(existing_files)
    print(f"已有: {existing_count} 份")
    
    generated = 0
    file_index = 0
    
    while existing_count + generated < TARGET_COUNT:
        for industry, companies in INDUSTRIES.items():
            if existing_count + generated >= TARGET_COUNT:
                break
            
            for company in companies:
                if existing_count + generated >= TARGET_COUNT:
                    break
                
                for topic in TOPICS:
                    if existing_count + generated >= TARGET_COUNT:
                        break
                    
                    file_index += 1
                    
                    # 生成日期
                    days_ago = random.randint(0, 365)
                    date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
                    
                    # 文件名
                    filename = f"RPT_{date}_{industry}_{company}_{topic}.pdf"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        continue
                    
                    # 创建PDF
                    try:
                        create_simple_pdf(filepath, company, industry, topic, date)
                        generated += 1
                        
                        if generated % 20 == 0:
                            print(f"已生成: {generated} 份 (总计: {existing_count + generated})")
                    
                    except Exception as e:
                        print(f"生成失败: {filename} - {e}")
    
    # 最终统计
    all_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
    final_count = len(all_files)
    
    print("\n" + "="*60)
    print("生成完成!")
    print(f"本次生成: {generated} 份")
    print(f"总计: {final_count} 份研报")
    print("="*60)
    
    # 行业分布
    print("\n行业分布:")
    for industry in INDUSTRIES.keys():
        count = len([f for f in all_files if industry in f])
        print(f"  {industry}: {count} 份")


if __name__ == "__main__":
    main()
