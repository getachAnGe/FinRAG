"""
FinRAG 研报下载器 - 多源下载版
尝试多个数据源下载研报
"""

import os
import time
import random
import requests
import urllib3
import re
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def download_pdf(url: str, filepath: str, session: requests.Session) -> bool:
    """下载PDF"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*",
        }
        
        response = session.get(url, headers=headers, timeout=30, stream=True, verify=False)
        
        if response.status_code == 200:
            content = response.content
            
            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    
    except Exception as e:
        return False


def try_eastmoney_reports(session: requests.Session, existing: set) -> int:
    """尝试从东方财富下载研报"""
    downloaded = 0
    
    # 东方财富研报PDF链接格式
    # 格式: https://pdf.dfcfw.com/pdf/H3_时间戳.pdf
    # 时间戳格式: 年月日+序号
    
    print("\n尝试东方财富研报...")
    
    # 尝试2024-2025年的研报
    for year in [2024, 2025]:
        for month in range(1, 13):
            if year == 2025 and month > 4:
                break
            
            for day in range(1, 29):
                if len(existing) >= TARGET_COUNT:
                    return downloaded
                
                date_str = f"{year}{month:02d}{day:02d}"
                
                # 尝试多个序号
                for seq in range(1, 20):
                    if len(existing) >= TARGET_COUNT:
                        return downloaded
                    
                    # 多种链接格式
                    urls = [
                        f"https://pdf.dfcfw.com/pdf/H3_{date_str}{seq:03d}.pdf",
                        f"https://pdf.dfcfw.com/pdf/H3_{date_str}{seq:04d}.pdf",
                        f"https://pdf.dfcfw.com/pdf/H2_{date_str}{seq:03d}.pdf",
                        f"https://pdf.dfcfw.com/pdf/H301_{date_str}{seq:03d}.pdf",
                    ]
                    
                    for url in urls:
                        filename = f"EM_{date_str}_{seq:03d}.pdf"
                        
                        if filename in existing:
                            continue
                        
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        if download_pdf(url, filepath, session):
                            existing.add(filename)
                            downloaded += 1
                            print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
                            break
                    
                    time.sleep(0.05)
    
    return downloaded


def try_sina_reports(session: requests.Session, existing: set) -> int:
    """尝试从新浪财经下载研报"""
    downloaded = 0
    
    print("\n尝试新浪财经研报...")
    
    # 新浪财经研报链接格式
    for year in [2024, 2025]:
        for month in range(1, 13):
            if year == 2025 and month > 4:
                break
            
            for i in range(100):
                if len(existing) >= TARGET_COUNT:
                    return downloaded
                
                # 新浪研报链接
                url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/stockid/600519/displaytype/4.phtml"
                
                time.sleep(0.1)
    
    return downloaded


def try_report_urls(session: requests.Session, existing: set) -> int:
    """尝试已知的研报URL列表"""
    downloaded = 0
    
    print("\n尝试已知研报URL...")
    
    # 已知的研报PDF链接模式
    known_patterns = [
        # 东方财富
        "https://pdf.dfcfw.com/pdf/H3_{}.pdf",
        "https://pdf.dfcfw.com/pdf/H2_{}.pdf",
        # 同花顺
        "https://eq.10jqka.com.cn/open/pdf/{}.pdf",
        # 其他
        "https://researchreport.cn/{}.pdf",
    ]
    
    # 尝试大量编号
    for i in range(2024010001, 2025129999, 1):
        if len(existing) >= TARGET_COUNT:
            break
        
        for pattern in known_patterns:
            if len(existing) >= TARGET_COUNT:
                break
            
            url = pattern.format(i)
            filename = f"RPT_{i}.pdf"
            
            if filename in existing:
                continue
            
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            if download_pdf(url, filepath, session):
                existing.add(filename)
                downloaded += 1
                print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
        
        if i % 1000 == 0:
            print(f"  已检查 {i} 个链接...")
        
        time.sleep(0.01)
    
    return downloaded


def try_static_pdfs(session: requests.Session, existing: set) -> int:
    """尝试静态PDF链接"""
    downloaded = 0
    
    print("\n尝试静态PDF链接...")
    
    # 静态PDF链接列表
    static_urls = []
    
    # 生成可能的PDF链接
    for year in [2024, 2025]:
        for month in range(1, 13):
            if year == 2025 and month > 4:
                break
            
            for day in range(1, 29):
                date = f"{year}{month:02d}{day:02d}"
                
                # 东方财富研报
                for seq in range(1, 100):
                    static_urls.append(f"https://pdf.dfcfw.com/pdf/H3_{date}{seq:03d}.pdf")
    
    random.shuffle(static_urls)
    
    for url in static_urls:
        if len(existing) >= TARGET_COUNT:
            break
        
        # 从URL提取文件名
        match = re.search(r'H\d_(\d+)\.pdf', url)
        if match:
            filename = f"DFCFW_{match.group(1)}.pdf"
        else:
            filename = f"PDF_{random.randint(100000, 999999)}.pdf"
        
        if filename in existing:
            continue
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if download_pdf(url, filepath, session):
            existing.add(filename)
            downloaded += 1
            print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename}")
        
        time.sleep(0.02)
    
    return downloaded


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 研报下载器 - 多源下载版")
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
    
    session = requests.Session()
    total_downloaded = 0
    
    # 尝试各种方法
    while len(existing) < TARGET_COUNT:
        # 方法1: 东方财富
        count = try_eastmoney_reports(session, existing)
        total_downloaded += count
        print(f"东方财富下载: {count} 份")
        
        if len(existing) >= TARGET_COUNT:
            break
        
        # 方法2: 静态PDF
        count = try_static_pdfs(session, existing)
        total_downloaded += count
        print(f"静态PDF下载: {count} 份")
        
        if len(existing) >= TARGET_COUNT:
            break
        
        # 方法3: 已知URL
        count = try_report_urls(session, existing)
        total_downloaded += count
        print(f"已知URL下载: {count} 份")
        
        # 如果都没下载到，退出
        if total_downloaded == 0:
            print("\n无法下载更多研报，请手动下载")
            break
    
    print("\n" + "="*60)
    print("下载完成!")
    print(f"总计: {len(existing)} 份研报")
    print(f"本次下载: {total_downloaded} 份")
    print("="*60)


if __name__ == "__main__":
    main()
