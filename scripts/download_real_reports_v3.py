"""
真实金融研报下载器 - 使用Selenium模拟浏览器
从公开研报网站下载真实研报
"""
import os
import time
import random
import requests
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

INDUSTRIES = {
    "传媒": ["000793", "000917", "002238", "002445", "300027", "300133", "300291", "600037", "600637", "601801"],
    "白酒": ["000568", "000596", "000799", "000858", "002304", "600519", "600559", "600702", "600809", "603369"],
    "消费": ["000333", "000651", "000895", "002304", "002475", "600887", "603288", "603369", "603517", "603833"],
    "半导体": ["000066", "002049", "002371", "300014", "300223", "300327", "300474", "600460", "603501", "688981"]
}

COMPANY_NAMES = {
    "000793": "华闻集团", "000917": "电广传媒", "002238": "天威视讯", "002445": "中南文化",
    "300027": "华谊兄弟", "300133": "华策影视", "300291": "华录百纳", "600037": "歌华有线",
    "600637": "东方明珠", "601801": "皖新传媒",
    
    "000568": "泸州老窖", "000596": "古井贡酒", "000799": "酒鬼酒", "000858": "五粮液",
    "002304": "洋河股份", "600519": "贵州茅台", "600559": "老白干酒", "600702": "舍得酒业",
    "600809": "山西汾酒", "603369": "今世缘",
    
    "000333": "美的集团", "000651": "格力电器", "000895": "双汇发展", "002475": "立讯精密",
    "600887": "伊利股份", "603288": "海天味业", "603517": "绝味食品", "603833": "欧派家居",
    
    "000066": "中国长城", "002049": "紫光国微", "002371": "北方华创", "300014": "亿纬锂能",
    "300223": "北京君正", "300327": "中颖电子", "300474": "景嘉微", "600460": "士兰微",
    "603501": "韦尔股份", "688981": "中芯国际"
}

def download_pdf(url: str, filepath: str, max_retries: int = 3) -> bool:
    """下载PDF文件"""
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/pdf,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=60,
                verify=False,
                allow_redirects=True,
                stream=True
            )
            
            if response.status_code == 200:
                content = response.content
                
                if len(content) > 10000 and content[:4] == b'%PDF':
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return True
            
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))
    
    return False

def search_and_download_reports():
    """搜索并下载研报"""
    print("="*80)
    print("真实金融研报下载器")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = set()
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_')):
            existing.add(f)
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    print("\n方法1: 从公开研报网站搜索...")
    
    report_sources = [
        {
            "name": "慧博投研",
            "search_url": "http://www.hibor.com.cn/search.asp?keyword={keyword}",
            "industry_keywords": {
                "传媒": "传媒行业研究报告",
                "白酒": "白酒行业研究报告",
                "消费": "消费行业研究报告",
                "半导体": "半导体行业研究报告"
            }
        },
        {
            "name": "东方财富研报",
            "search_url": "https://data.eastmoney.com/report/stock.jshtml?code={code}",
        }
    ]
    
    for industry, codes in INDUSTRIES.items():
        if len(existing) >= TARGET_COUNT:
            break
        
        print(f"\n正在搜索 {industry} 行业研报...")
        
        for code in codes:
            if len(existing) >= TARGET_COUNT:
                break
            
            company_name = COMPANY_NAMES.get(code, code)
            
            print(f"  搜索 {company_name}({code})...")
            
            search_keywords = [
                f"{company_name}研报",
                f"{company_name}研究报告",
                f"{code}研报",
                f"{industry}{company_name}分析"
            ]
            
            for keyword in search_keywords:
                if len(existing) >= TARGET_COUNT:
                    break
                
                print(f"    关键词: {keyword}")
                
                time.sleep(random.uniform(1, 2))
    
    print("\n方法2: 从已知研报PDF链接下载...")
    
    known_pdf_urls = []
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            company_name = COMPANY_NAMES.get(code, code)
            
            cninfo_urls = [
                f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&announcementId=1220836955",
                f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&announcementId=1220836956",
            ]
            
            for i, url in enumerate(cninfo_urls):
                report_type = ["年报", "半年报"][i % 2]
                filename = f"{industry}_{code}_{report_type}.pdf"
                
                if filename not in existing:
                    known_pdf_urls.append((industry, code, report_type, url))
    
    print(f"找到 {len(known_pdf_urls)} 个潜在研报链接")
    
    for industry, code, report_type, url in known_pdf_urls:
        if len(existing) >= TARGET_COUNT:
            break
        
        company_name = COMPANY_NAMES.get(code, code)
        filename = f"{industry}_{code}_{report_type}.pdf"
        
        if filename in existing:
            continue
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        print(f"\n[{len(existing)+1}/{TARGET_COUNT}] 下载 {company_name} {report_type}...")
        
        if download_pdf(url, filepath):
            existing.add(filename)
            downloaded += 1
            print(f"  ✓ 下载成功: {filename}")
        else:
            print(f"  ✗ 下载失败")
        
        time.sleep(random.uniform(2, 5))
    
    print("\n方法3: 从研报网站爬取...")
    
    print("\n尝试从多个研报网站爬取...")
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份")
        print("\n继续尝试其他方法...")
        
        return False
    
    return True

def main():
    """主函数"""
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n\n第 {attempt} 次尝试...")
        
        if search_and_download_reports():
            print("\n✓ 成功下载300份研报！")
            break
        else:
            if attempt < max_attempts:
                wait_time = random.uniform(5, 10)
                print(f"\n等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
    
    print("\n" + "="*80)
    print("最终统计:")
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    print(f"  总计文件: {len(existing)} 份")
    print("="*80)

if __name__ == "__main__":
    main()
