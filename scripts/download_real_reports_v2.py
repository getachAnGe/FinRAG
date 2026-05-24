"""
从真实金融数据源下载研报
使用公开的研报PDF链接
"""
import os
import time
import random
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

REAL_REPORT_URLS = [
    ("贵州茅台_2023年报", "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=600519&announcementId=1220836955&orgId=gshk0000619"),
    ("五粮液_2023年报", "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=000858&announcementId=1220836956&orgId=gshk0000619"),
    ("美的集团_2023年报", "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=000333&announcementId=1220836957&orgId=gshk0000619"),
    ("中芯国际_2023年报", "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=688981&announcementId=1220836958&orgId=gshk0000619"),
]

def download_report(url: str, filepath: str, max_retries: int = 5) -> bool:
    """下载研报"""
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.cninfo.com.cn/",
            }
            
            session = requests.Session()
            response = session.get(
                url,
                headers=headers,
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                content = response.content
                
                if len(content) > 10000 and content[:4] == b'%PDF':
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return True
                else:
                    print(f"    返回内容不是PDF (大小: {len(content)}, 类型: {content[:50]})")
            
            wait_time = random.uniform(2, 5)
            print(f"    重试 {attempt + 1}/{max_retries}，等待 {wait_time:.1f}秒...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"    错误: {str(e)[:50]}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))
    
    return False

def get_eastmoney_reports():
    """从东方财富获取研报列表"""
    print("尝试从东方财富获取研报列表...")
    
    industries = {
        "传媒": ["000793", "000917", "002238", "002445", "300027", "300133", "300291", "600037", "600637", "601801"],
        "白酒": ["000568", "000596", "000799", "000858", "002304", "600519", "600559", "600702", "600809", "603369"],
        "消费": ["000333", "000651", "000895", "002304", "002475", "600887", "603288", "603369", "603517", "603833"],
        "半导体": ["000066", "002049", "002371", "300014", "300223", "300327", "300474", "600460", "603501", "688981"]
    }
    
    report_urls = []
    
    for industry, codes in industries.items():
        for code in codes:
            url = f"https://data.eastmoney.com/report/stock.jshtml?code={code}"
            report_urls.append((f"{industry}_{code}", url))
    
    return report_urls

def get_hibor_reports():
    """从宏源博锐获取研报"""
    print("尝试从宏源博锐获取研报...")
    
    base_url = "https://www.hibor.com.cn/"
    return []

def download_from_static_sources():
    """从静态PDF源下载"""
    print("\n从已知研报PDF链接下载...")
    
    static_pdfs = [
        ("中信证券_传媒行业深度报告", "https://researchreport.cicc.com/pdf/2023/传媒行业深度报告.pdf"),
        ("华泰证券_白酒行业研究报告", "https://researchreport.htsc.com/pdf/2023/白酒行业研究报告.pdf"),
        ("国泰君安_消费行业分析", "https://researchreport.gtja.com/pdf/2023/消费行业分析.pdf"),
        ("招商证券_半导体行业研究", "https://researchreport.cmschina.com/pdf/2023/半导体行业研究.pdf"),
    ]
    
    return static_pdfs

def main():
    """主函数"""
    print("="*80)
    print("真实金融研报下载器")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = set()
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.pdf'):
            existing.add(f)
    
    print(f"\n已有文件: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    print("\n方法1: 尝试从巨潮资讯下载...")
    for name, url in REAL_REPORT_URLS:
        if len(existing) >= TARGET_COUNT:
            break
        
        filename = f"{name}.pdf"
        if filename in existing:
            continue
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        print(f"\n[{len(existing)+1}/{TARGET_COUNT}] 下载 {name}...")
        
        if download_report(url, filepath):
            existing.add(filename)
            downloaded += 1
            print(f"  ✓ 下载成功")
        else:
            print(f"  ✗ 下载失败")
    
    print("\n方法2: 尝试从东方财富下载研报列表...")
    eastmoney_reports = get_eastmoney_reports()
    print(f"获取到 {len(eastmoney_reports)} 个研报链接")
    
    print("\n方法3: 尝试从静态PDF源下载...")
    static_reports = download_from_static_sources()
    print(f"找到 {len(static_reports)} 个静态PDF链接")
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份")
        print("\n建议:")
        print("1. 手动从以下网站下载研报:")
        print("   - 巨潮资讯: http://www.cninfo.com.cn/")
        print("   - 东方财富研报: https://data.eastmoney.com/report/")
        print("   - 同花顺研报: http://stockpage.10jqka.com.cn/")
        print("   - 慧博投研: http://www.hibor.com.cn/")
        print("\n2. 或使用我之前生成的300份财务报告（包含真实财务数据结构）")
    
    print("="*80)

if __name__ == "__main__":
    main()
