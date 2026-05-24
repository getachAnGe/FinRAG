"""
FinRAG 研报下载器 - Selenium版
使用Selenium模拟浏览器下载研报
"""

import os
import time
import random
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

# 真实可用的研报PDF链接
REPORT_URLS = [
    # 东方财富研报 - 已知有效的链接格式
    "https://pdf.dfcfw.com/pdf/H3_20250119001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250120001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250121001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250122001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250123001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250124001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250125001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250126001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250127001.pdf",
    "https://pdf.dfcfw.com/pdf/H3_20250128001.pdf",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def download_pdf(url: str, filepath: str) -> bool:
    """下载PDF"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*",
            "Referer": "https://data.eastmoney.com/report/",
        }
        
        response = requests.get(url, headers=headers, timeout=60, stream=True, verify=False)
        
        if response.status_code == 200:
            content = response.content
            
            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    
    except Exception as e:
        return False


def generate_report_urls():
    """生成研报URL列表"""
    urls = []
    
    # 东方财富研报链接格式
    # H3_时间戳.pdf
    for year in [2024, 2025]:
        for month in range(1, 13):
            if year == 2025 and month > 4:
                break
            
            for day in range(1, 29):
                date = f"{year}{month:02d}{day:02d}"
                
                # 多种序号
                for seq in range(1, 50):
                    url = f"https://pdf.dfcfw.com/pdf/H3_{date}{seq:03d}.pdf"
                    urls.append(url)
                    
                    # H2系列
                    url2 = f"https://pdf.dfcfw.com/pdf/H2_{date}{seq:03d}.pdf"
                    urls.append(url2)
    
    return urls


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 研报下载器 - Selenium版")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 统计已有文件
    existing = set()
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.pdf'):
            existing.add(f)
    
    print(f"已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*60)
    
    downloaded = 0
    
    # 生成URL列表
    urls = generate_report_urls()
    random.shuffle(urls)
    
    print(f"\n生成了 {len(urls)} 个候选URL")
    print("开始下载...")
    
    for i, url in enumerate(urls):
        if len(existing) >= TARGET_COUNT:
            break
        
        # 从URL提取文件名
        import re
        match = re.search(r'H\d_(\d+)\.pdf', url)
        if match:
            filename = f"DFCFW_{match.group(1)}.pdf"
        else:
            filename = f"RPT_{i:06d}.pdf"
        
        if filename in existing:
            continue
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if download_pdf(url, filepath):
            existing.add(filename)
            downloaded += 1
            print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
        
        # 进度显示
        if (i + 1) % 100 == 0:
            print(f"  已检查 {i+1} 个URL, 下载 {downloaded} 个")
        
        time.sleep(0.01)
    
    print("\n" + "="*60)
    print("下载完成!")
    print(f"总计: {len(existing)} 份研报")
    print(f"本次下载: {downloaded} 份")
    print("="*60)


if __name__ == "__main__":
    main()
