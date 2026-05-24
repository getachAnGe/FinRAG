"""
FinRAG 研报下载器 - 直接下载版
从东方财富直接下载研报PDF
"""

import os
import time
import random
import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/pdf,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }


def download_pdf(url: str, filepath: str) -> bool:
    """下载PDF文件"""
    try:
        response = requests.get(url, headers=get_headers(), timeout=60, stream=True, verify=False)
        
        if response.status_code == 200:
            content = response.content
            
            # 检查是否为真实PDF (至少10KB且以%PDF开头)
            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    
    except Exception as e:
        return False


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 研报下载器 - 直接下载版")
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
    
    # 东方财富研报PDF链接格式
    # https://pdf.dfcfw.com/pdf/H3_时间戳.pdf
    # 时间戳格式: 年月日+序号，如 20250101001
    
    # 从2024年1月到2025年4月的研报
    base_urls = [
        "https://pdf.dfcfw.com/pdf/H3_{}.pdf",
        "https://pdf.dfcfw.com/pdf/H3_{}001.pdf",
        "https://pdf.dfcfw.com/pdf/H3_{}002.pdf",
        "https://pdf.dfcfw.com/pdf/H3_{}003.pdf",
    ]
    
    # 生成日期范围
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 4, 30)
    
    current_date = start_date
    
    while current_date <= end_date and len(existing) < TARGET_COUNT:
        date_str = current_date.strftime("%Y%m%d")
        
        for base_url in base_urls:
            if len(existing) >= TARGET_COUNT:
                break
            
            url = base_url.format(date_str)
            
            # 生成文件名
            filename = f"DFCFW_{date_str}_{downloaded+1}.pdf"
            
            if filename in existing:
                continue
            
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # 尝试下载
            if download_pdf(url, filepath):
                existing.add(filename)
                downloaded += 1
                print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
            
            time.sleep(random.uniform(0.1, 0.3))
        
        current_date += timedelta(days=1)
        
        if downloaded % 20 == 0 and downloaded > 0:
            print(f"已下载: {downloaded} 份")
    
    # 如果还不够，尝试其他链接格式
    if len(existing) < TARGET_COUNT:
        print("\n尝试其他链接格式...")
        
        # 尝试随机编号
        for i in range(2024010001, 2025129999, random.randint(1, 100)):
            if len(existing) >= TARGET_COUNT:
                break
            
            url = f"https://pdf.dfcfw.com/pdf/H3_{i}.pdf"
            filename = f"DFCFW_{i}.pdf"
            
            if filename in existing:
                continue
            
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            if download_pdf(url, filepath):
                existing.add(filename)
                downloaded += 1
                print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
            
            time.sleep(random.uniform(0.05, 0.15))
    
    print("\n" + "="*60)
    print("下载完成!")
    print(f"总计: {len(existing)} 份研报")
    print(f"本次下载: {downloaded} 份")
    print("="*60)


if __name__ == "__main__":
    main()
