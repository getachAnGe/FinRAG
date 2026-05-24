"""
真实金融研报下载器 - 直接下载版
从公开研报网站直接下载PDF
"""
import os
import time
import random
import requests
import urllib3
import re
from urllib.parse import urljoin, quote

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

def download_pdf(url: str, filepath: str, max_retries: int = 5) -> bool:
    """下载PDF文件"""
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/pdf,application/x-pdf,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            session = requests.Session()
            response = session.get(
                url,
                headers=headers,
                timeout=60,
                verify=False,
                allow_redirects=True,
                stream=True
            )
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'pdf' in content_type.lower() or response.content[:4] == b'%PDF':
                    content = response.content
                    
                    if len(content) > 10000:
                        with open(filepath, "wb") as f:
                            f.write(content)
                        return True
            
            wait_time = random.uniform(2, 5)
            time.sleep(wait_time)
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 7))
    
    return False

def get_report_urls_from_eastmoney():
    """从东方财富获取研报URL"""
    print("\n从东方财富研报中心获取研报列表...")
    
    urls = []
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            company_name = COMPANY_NAMES.get(code, code)
            
            url = f"https://data.eastmoney.com/report/stock.jshtml?code={code}"
            urls.append((industry, code, company_name, url))
    
    return urls

def get_report_urls_from_cninfo():
    """从巨潮资讯获取公告URL"""
    print("\n从巨潮资讯获取公告列表...")
    
    urls = []
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            company_name = COMPANY_NAMES.get(code, code)
            
            search_url = f"http://www.cninfo.com.cn/new/fulltextSearch?stockcode={code}&searchtype=1"
            urls.append((industry, code, company_name, search_url))
    
    return urls

def download_from_public_sources():
    """从公开资源下载研报"""
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
    
    print("\n方法1: 从公开研报PDF链接下载...")
    
    public_report_urls = []
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            company_name = COMPANY_NAMES.get(code, code)
            
            report_urls = [
                (f"{industry}_{code}_年报", f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&orgId=&announcementId=1220836955"),
                (f"{industry}_{code}_半年报", f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&orgId=&announcementId=1220836956"),
                (f"{industry}_{code}_一季报", f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&orgId=&announcementId=1220836957"),
                (f"{industry}_{code}_三季报", f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={code}&orgId=&announcementId=1220836958"),
            ]
            
            public_report_urls.extend(report_urls)
    
    print(f"找到 {len(public_report_urls)} 个潜在研报链接")
    
    for i, (report_name, url) in enumerate(public_report_urls):
        if len(existing) >= TARGET_COUNT:
            break
        
        filename = f"{report_name}.pdf"
        
        if filename in existing:
            continue
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        print(f"\n[{len(existing)+1}/{TARGET_COUNT}] 下载 {report_name}...")
        
        if download_pdf(url, filepath):
            existing.add(filename)
            downloaded += 1
            print(f"  ✓ 下载成功")
        else:
            print(f"  ✗ 下载失败")
        
        time.sleep(random.uniform(2, 4))
    
    print("\n方法2: 从研报网站搜索...")
    
    search_urls = []
    
    for industry in INDUSTRIES.keys():
        industry_keywords = {
            "传媒": "传媒行业",
            "白酒": "白酒行业",
            "消费": "消费行业",
            "半导体": "半导体行业"
        }
        
        keyword = industry_keywords.get(industry, industry)
        
        search_url = f"http://www.hibor.com.cn/search.asp?keyword={quote(keyword)}"
        search_urls.append((industry, search_url))
    
    for industry, url in search_urls:
        if len(existing) >= TARGET_COUNT:
            break
        
        print(f"\n搜索 {industry} 行业研报...")
        print(f"  URL: {url}")
        
        time.sleep(random.uniform(1, 2))
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    return len(existing) >= TARGET_COUNT

def main():
    """主函数"""
    max_attempts = 20
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n\n{'='*80}")
        print(f"第 {attempt} 次尝试下载真实研报")
        print(f"{'='*80}")
        
        if download_from_public_sources():
            print("\n✓ 成功下载300份研报！")
            break
        else:
            if attempt < max_attempts:
                wait_time = random.uniform(10, 20)
                print(f"\n等待 {wait_time:.1f} 秒后继续尝试...")
                time.sleep(wait_time)
    
    print("\n" + "="*80)
    print("最终统计:")
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份研报")
        print("继续尝试其他方法...")
    
    print("="*80)

if __name__ == "__main__":
    main()
