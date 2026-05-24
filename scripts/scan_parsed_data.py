"""
第一步：扫描所有 parsed JSON，提取公司和财务指标
"""
import os, json, re
from collections import defaultdict

parsed_dir = "data/parsed"
files = [f for f in os.listdir(parsed_dir) if f.endswith('.json')]

# 财务指标关键词
INDICATORS = {
    "营业收入": ["营业收入", "营收"],
    "净利润": ["净利润", "净利", "归属于母公司"],
    "毛利率": ["毛利率"],
    "净资产收益率": ["净资产收益率", "ROE", "roe"],
    "每股收益": ["每股收益", "基本每股收益"],
    "研发投入": ["研发投入", "研发费用"],
    "资产负债率": ["资产负债率"],
    "总资产": ["总资产"],
    "经营活动现金流": ["经营活动产生", "经营性现金流"],
    "市盈率": ["市盈率"],
}

company_summary = {}

for fname in files:
    filepath = os.path.join(parsed_dir, fname)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue
    
    source = data.get('source', fname)
    pages = data.get('pages', [])
    
    if not pages:
        continue
    
    total_pages = len(pages)
    total_tables = sum(len(p.get('tables', [])) for p in pages)
    
    # 提取公司名（从文件名）
    basename = fname.replace('.json', '')
    parts = basename.split('_')
    if parts[0] == 'H3':
        company_name = "证券研究报告"
    elif len(parts) >= 3:
        company_name = parts[1]
    else:
        company_name = parts[0]
    
    # 合并所有文本
    all_text = ""
    for page in pages[:5]:
        for block in page.get('text_blocks', []):
            t = block.get('text', '')
            if t:
                all_text += t + "\n"
    
    for page in pages:
        for table in page.get('tables', []):
            md = table.get('markdown', '')
            if md:
                all_text += md + "\n"
    
    # 检测财务指标
    found_indicators = []
    for indicator_name, keywords in INDICATORS.items():
        for kw in keywords:
            if kw in all_text:
                found_indicators.append(indicator_name)
                break
    
    if company_name not in company_summary:
        company_summary[company_name] = {
            "files": [],
            "indicators": set(),
            "total_tables": 0,
            "total_pages": 0,
        }
    
    company_summary[company_name]["files"].append(fname)
    company_summary[company_name]["indicators"].update(found_indicators)
    company_summary[company_name]["total_tables"] += total_tables
    company_summary[company_name]["total_pages"] += total_pages

# 输出结果
print("=" * 80)
print("公司 | 文件数 | 页数 | 表格数 | 包含的财务指标")
print("=" * 80)

good_companies = []
for company, info in sorted(company_summary.items()):
    indicators = list(info["indicators"])
    has_finance_data = len(indicators) > 0
    
    indicator_str = ", ".join(indicators[:6]) if indicators else "无"
    if len(indicators) > 6:
        indicator_str += f"...(+{len(indicators)-6}个)"
    
    print(f"{company:12s} | {len(info['files']):3d}份 | {info['total_pages']:4d}页 | {info['total_tables']:4d}表 | {indicator_str}")
    
    if has_finance_data and len(info['files']) >= 3 and company not in ("证券研究报告", "传媒", "半导体", "消费", "白酒"):
        good_companies.append(company)

print(f"\n{'='*80}")
print(f"有真实财务数据的公司 ({len(good_companies)}家):")
for c in good_companies:
    info = company_summary[c]
    print(f"  {c}: {len(info['files'])}份文件, {list(info['indicators'])[:5]}")
