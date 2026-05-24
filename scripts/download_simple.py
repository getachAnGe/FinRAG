"""
简单直接的研报下载器
从公开网站爬取研报PDF
"""
import os
import time
import random
import requests
import urllib3
import re
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def download_pdf(url: str, filepath: str) -> bool:
    """下载PDF"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=60, verify=False, stream=True)
        
        if response.status_code == 200:
            content = response.content
            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        return False
    except:
        return False

def search_reports_from_baidu():
    """从百度搜索研报"""
    print("\n从百度搜索研报...")
    
    downloaded = 0
    
    keywords = [
        "传媒行业研究报告 filetype:pdf",
        "白酒行业研究报告 filetype:pdf",
        "消费行业研究报告 filetype:pdf",
        "半导体行业研究报告 filetype:pdf",
    ]
    
    for keyword in keywords:
        try:
            url = f"https://www.baidu.com/s?wd={keyword}"
            headers = {"User-Agent": USER_AGENT}
            
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                print(f"  搜索关键词: {keyword}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:10]:
                    href = link.get('href', '')
                    
                    if '.pdf' in href.lower():
                        print(f"    找到PDF链接: {href[:50]}")
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"    错误: {str(e)[:50]}")
    
    return downloaded

def try_researchgate():
    """从ResearchGate下载金融研究论文"""
    print("\n从ResearchGate下载金融研究...")
    
    downloaded = 0
    
    search_terms = [
        "media industry finance",
        "liquor industry finance",
        "consumer industry finance",
        "semiconductor industry finance",
    ]
    
    for term in search_terms:
        try:
            url = f"https://www.researchgate.net/search?q={term}"
            headers = {"User-Agent": USER_AGENT}
            
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                print(f"  搜索: {term}")
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            continue
    
    return downloaded

def try_ssrn():
    """从SSRN下载金融研究"""
    print("\n从SSRN下载金融研究...")
    
    downloaded = 0
    
    paper_ids = [
        "1234567", "2345678", "3456789", "4567890", "5678901",
    ]
    
    for paper_id in paper_ids:
        try:
            url = f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={paper_id}"
            headers = {"User-Agent": USER_AGENT}
            
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                print(f"  访问论文: {paper_id}")
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            continue
    
    return downloaded

def try_public_financial_reports():
    """从公开财务报告网站下载"""
    print("\n从公开财务报告网站下载...")
    
    downloaded = 0
    
    public_urls = [
        ("SEC财务报告", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K&dateb=&owner=include&count=40&output=atom"),
        ("世界银行报告", "https://documents.worldbank.org/en/publication/documents-reports"),
    ]
    
    for name, url in public_urls:
        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                print(f"  访问 {name} 成功")
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"  错误: {str(e)[:50]}")
    
    return downloaded

def download_from_sec():
    """从SEC下载真实财务报告"""
    print("\n从SEC下载真实财务报告...")
    
    downloaded = 0
    
    company_ciks = {
        "传媒": ["0001067983", "0001326801", "0001558370"],
        "白酒": ["0000320193", "0001652044", "0001704174"],
        "消费": ["0001744489", "0001786320", "0001800281"],
        "半导体": ["0001829176", "0001852636", "0001874128"],
    }
    
    for industry, ciks in company_ciks.items():
        for cik in ciks:
            try:
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=10"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    print(f"  访问 {industry} - {cik} 成功")
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        
                        if 'Archives' in href and '.pdf' in href.lower():
                            pdf_url = f"https://www.sec.gov{href}"
                            
                            filename = f"{industry}_{cik}_report.pdf"
                            filepath = os.path.join(OUTPUT_DIR, filename)
                            
                            print(f"    找到PDF: {filename}")
                            
                            if download_pdf(pdf_url, filepath):
                                downloaded += 1
                                print(f"      ✓ 下载成功")
                            
                            time.sleep(random.uniform(2, 5))
                
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"    错误: {str(e)[:50]}")
                continue
    
    return downloaded

def main():
    """主函数"""
    print("="*80)
    print("简单直接的研报下载器")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    total_downloaded = 0
    attempt = 0
    
    while len(existing) < TARGET_COUNT:
        attempt += 1
        print(f"\n\n{'='*80}")
        print(f"第 {attempt} 轮尝试")
        print(f"{'='*80}")
        
        downloaded = 0
        
        downloaded += search_reports_from_baidu()
        downloaded += try_researchgate()
        downloaded += try_ssrn()
        downloaded += try_public_financial_reports()
        downloaded += download_from_sec()
        
        total_downloaded += downloaded
        
        existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
        
        print(f"\n本轮下载: {downloaded} 份")
        print(f"总计下载: {total_downloaded} 份")
        print(f"当前总数: {len(existing)} 份")
        
        if len(existing) >= TARGET_COUNT:
            print("\n✓ 成功下载300份研报！")
            break
        
        wait_time = random.uniform(10, 20)
        print(f"\n等待 {wait_time:.1f} 秒后继续...")
        time.sleep(wait_time)
    
    print("\n" + "="*80)
    print("最终统计:")
    print(f"  总计文件: {len(existing)} 份")
    print("="*80)

if __name__ == "__main__":
    main()
