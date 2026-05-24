"""
真实金融研报下载器 - 持续尝试版
使用多种方法下载真实研报
"""
import os
import time
import random
import requests
import urllib3
import json
import re
from urllib.parse import urljoin, quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                content = response.content
                
                if 'pdf' in content_type.lower() or content[:4] == b'%PDF':
                    if len(content) > 10000:
                        with open(filepath, "wb") as f:
                            f.write(content)
                        return True
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 7))
    
    return False

def try_eastmoney_api():
    """尝试东方财富API"""
    print("\n方法1: 尝试东方财富研报API...")
    
    downloaded = 0
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            try:
                api_url = f"https://reportapi.eastmoney.com/report/list?cb=&pageNo=1&pageSize=20&code={code}"
                
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Referer": "https://data.eastmoney.com/",
                }
                
                response = requests.get(api_url, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    text = response.text
                    
                    json_match = re.search(r'\((.*?)\)', text)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        
                        if 'data' in data:
                            for item in data['data'][:5]:
                                title = item.get('title', '')
                                pdf_url = item.get('pdfUrl', '')
                                
                                if pdf_url:
                                    filename = f"{industry}_{code}_{title[:20]}.pdf"
                                    filepath = os.path.join(OUTPUT_DIR, filename)
                                    
                                    print(f"  找到研报: {title}")
                                    
                                    if download_pdf(pdf_url, filepath):
                                        downloaded += 1
                                        print(f"    ✓ 下载成功")
                                    
                                    time.sleep(random.uniform(2, 4))
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"    错误: {str(e)[:50]}")
                continue
    
    return downloaded

def try_cninfo_api():
    """尝试巨潮资讯API"""
    print("\n方法2: 尝试巨潮资讯API...")
    
    downloaded = 0
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            try:
                search_url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
                
                data = {
                    "stock": f"{code},gssh{code}",
                    "tabName": "fulltext",
                    "pageSize": 20,
                    "pageNum": 1,
                    "column": "szse" if code.startswith(("0", "3")) else "sse",
                    "category": "category_ndbg_szsh",
                    "isHLtitle": "true",
                }
                
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                
                response = requests.post(search_url, data=data, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if 'announcements' in result:
                        for item in result['announcements'][:5]:
                            title = item.get('announcementTitle', '')
                            adjunct_url = item.get('adjunctUrl', '')
                            
                            if adjunct_url:
                                pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}"
                                filename = f"{industry}_{code}_{title[:20]}.pdf"
                                filepath = os.path.join(OUTPUT_DIR, filename)
                                
                                print(f"  找到公告: {title}")
                                
                                if download_pdf(pdf_url, filepath):
                                    downloaded += 1
                                    print(f"    ✓ 下载成功")
                                
                                time.sleep(random.uniform(2, 4))
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"    错误: {str(e)[:50]}")
                continue
    
    return downloaded

def try_10jqka():
    """尝试同花顺"""
    print("\n方法3: 尝试同花顺研报...")
    
    downloaded = 0
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            try:
                url = f"http://stockpage.10jqka.com.cn/{code}/"
                
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    print(f"  访问 {code} 页面成功")
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                continue
    
    return downloaded

def try_public_pdf_links():
    """尝试公开PDF链接"""
    print("\n方法4: 尝试已知的研报PDF链接...")
    
    downloaded = 0
    
    known_links = []
    
    for industry, codes in INDUSTRIES.items():
        for code in codes:
            company_name = COMPANY_NAMES.get(code, code)
            
            links = [
                (f"{industry}_{code}_年报", f"http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId="),
                (f"{industry}_{code}_研报", f"https://data.eastmoney.com/report/stock/{code}.html"),
            ]
            
            known_links.extend(links)
    
    for report_name, url in known_links:
        try:
            filename = f"{report_name}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            print(f"  尝试: {report_name}")
            
            if download_pdf(url, filepath):
                downloaded += 1
                print(f"    ✓ 下载成功")
            
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            continue
    
    return downloaded

def main():
    """主函数"""
    print("="*80)
    print("真实金融研报下载器 - 持续尝试版")
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
        
        downloaded += try_eastmoney_api()
        downloaded += try_cninfo_api()
        downloaded += try_10jqka()
        downloaded += try_public_pdf_links()
        
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
