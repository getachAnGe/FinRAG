"""
多渠道下载中国金融研报
尝试所有可能的公开数据源
"""
import os
import time
import random
import requests
import urllib3
import re
import json
from urllib.parse import quote, urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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
                "User-Agent": USER_AGENT,
                "Accept": "application/pdf,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            
            response = requests.get(url, headers=headers, timeout=60, verify=False, stream=True)
            
            if response.status_code == 200:
                content = response.content
                
                if len(content) > 10000 and content[:4] == b'%PDF':
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return True
            
            time.sleep(random.uniform(1, 3))
        except:
            time.sleep(random.uniform(1, 3))
    
    return False

def try_eastmoney_report_list(code: str) -> list:
    """尝试从东方财富获取研报列表（新方法）"""
    try:
        url = f"https://reportapi.eastmoney.com/report/list?cb=&pageNo=1&pageSize=100&code={code}&industryCode=*&qType=0&beginTime=&endTime=&lastUpdateTime="
        
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://data.eastmoney.com/report/",
            "Accept": "*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            text = response.text
            
            json_match = re.search(r'\((.*?)\)', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                
                reports = []
                
                if 'data' in data:
                    for item in data['data']:
                        title = item.get('title', '')
                        encode_url = item.get('encodeUrl', '')
                        
                        if encode_url:
                            pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{encode_url}1.pdf"
                            reports.append({
                                'title': title,
                                'pdf_url': pdf_url,
                            })
                
                return reports[:20]
        
        return []
    except:
        return []

def try_sina_finance(code: str, company_name: str) -> list:
    """尝试从新浪财经获取研报"""
    try:
        url = f"https://vip.stock.finance.sina.com.cn/q/go.php/vReport_List/kind/search/index.phtml?t1=all&t2=all&t3=&keyword={quote(company_name)}"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            html = response.text
            
            pdf_urls = re.findall(r'href="(https?://[^"]*\.pdf)"', html, re.IGNORECASE)
            
            reports = []
            for pdf_url in pdf_urls[:10]:
                reports.append({
                    'title': f'研报_{len(reports)+1}',
                    'pdf_url': pdf_url,
                })
            
            return reports
        
        return []
    except:
        return []

def try_hexun_reports(code: str, company_name: str) -> list:
    """尝试从和讯网获取研报"""
    try:
        url = f"http://stock.hexun.com/2010-04-16/{code}.html"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            html = response.text
            
            pdf_urls = re.findall(r'href="(https?://[^"]*\.pdf)"', html, re.IGNORECASE)
            
            reports = []
            for pdf_url in pdf_urls[:10]:
                reports.append({
                    'title': f'研报_{len(reports)+1}',
                    'pdf_url': pdf_url,
                })
            
            return reports
        
        return []
    except:
        return []

def try_cnstock_reports(code: str, company_name: str) -> list:
    """尝试从中国证券网获取研报"""
    try:
        url = f"https://www.cnstock.com/api/search?keyword={quote(company_name)}&type=report"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            reports = []
            
            if 'data' in data and 'list' in data['data']:
                for item in data['data']['list'][:10]:
                    title = item.get('title', '')
                    pdf_url = item.get('pdfUrl', '')
                    
                    if pdf_url:
                        reports.append({
                            'title': title,
                            'pdf_url': pdf_url,
                        })
            
            return reports
        
        return []
    except:
        return []

def try_10jqka_reports(code: str, company_name: str) -> list:
    """尝试从同花顺获取研报"""
    try:
        url = f"http://stockpage.10jqka.com.cn/{code}/"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            html = response.text
            
            pdf_urls = re.findall(r'href="(https?://[^"]*\.pdf)"', html, re.IGNORECASE)
            
            reports = []
            for pdf_url in pdf_urls[:10]:
                reports.append({
                    'title': f'研报_{len(reports)+1}',
                    'pdf_url': pdf_url,
                })
            
            return reports
        
        return []
    except:
        return []

def try_cs_reports(code: str, company_name: str) -> list:
    """尝试从中证网获取研报"""
    try:
        url = f"https://www.cs.com.cn/sylm/jsbd/{quote(company_name)}/"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            html = response.text
            
            pdf_urls = re.findall(r'href="(https?://[^"]*\.pdf)"', html, re.IGNORECASE)
            
            reports = []
            for pdf_url in pdf_urls[:10]:
                reports.append({
                    'title': f'研报_{len(reports)+1}',
                    'pdf_url': pdf_url,
                })
            
            return reports
        
        return []
    except:
        return []

def main():
    """主函数"""
    print("="*80)
    print("多渠道下载中国金融研报")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    attempt = 0
    
    while len(existing) < TARGET_COUNT:
        attempt += 1
        print(f"\n\n第 {attempt} 轮尝试...")
        
        for industry, codes in INDUSTRIES.items():
            if len(existing) >= TARGET_COUNT:
                break
            
            print(f"\n下载 {industry} 行业研报...")
            
            for code in codes:
                if len(existing) >= TARGET_COUNT:
                    break
                
                company_name = COMPANY_NAMES.get(code, code)
                
                print(f"\n  公司: {company_name} ({code})")
                
                print(f"    方法1: 东方财富研报...")
                reports = try_eastmoney_report_list(code)
                
                if reports:
                    print(f"    找到 {len(reports)} 份研报")
                    
                    for i, report in enumerate(reports):
                        if len(existing) >= TARGET_COUNT:
                            break
                        
                        title = report['title'][:30]
                        pdf_url = report['pdf_url']
                        
                        filename = f"{industry}_{company_name}_东方财富_{i+1}.pdf"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        if os.path.exists(filepath):
                            continue
                        
                        print(f"      下载: {title}...")
                        
                        if download_pdf(pdf_url, filepath):
                            existing.append(filename)
                            downloaded += 1
                            print(f"        ✓ 下载成功")
                        
                        time.sleep(random.uniform(0.5, 1.5))
                
                print(f"    方法2: 新浪财经...")
                reports = try_sina_finance(code, company_name)
                
                if reports:
                    print(f"    找到 {len(reports)} 份研报")
                    
                    for i, report in enumerate(reports):
                        if len(existing) >= TARGET_COUNT:
                            break
                        
                        filename = f"{industry}_{company_name}_新浪_{i+1}.pdf"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        if os.path.exists(filepath):
                            continue
                        
                        print(f"      下载研报...")
                        
                        if download_pdf(report['pdf_url'], filepath):
                            existing.append(filename)
                            downloaded += 1
                            print(f"        ✓ 下载成功")
                        
                        time.sleep(random.uniform(0.5, 1.5))
                
                print(f"    方法3: 和讯网...")
                reports = try_hexun_reports(code, company_name)
                
                if reports:
                    print(f"    找到 {len(reports)} 份研报")
                    
                    for i, report in enumerate(reports):
                        if len(existing) >= TARGET_COUNT:
                            break
                        
                        filename = f"{industry}_{company_name}_和讯_{i+1}.pdf"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        if os.path.exists(filepath):
                            continue
                        
                        if download_pdf(report['pdf_url'], filepath):
                            existing.append(filename)
                            downloaded += 1
                            print(f"        ✓ 下载成功")
                        
                        time.sleep(random.uniform(0.5, 1.5))
                
                print(f"    方法4: 同花顺...")
                reports = try_10jqka_reports(code, company_name)
                
                if reports:
                    print(f"    找到 {len(reports)} 份研报")
                    
                    for i, report in enumerate(reports):
                        if len(existing) >= TARGET_COUNT:
                            break
                        
                        filename = f"{industry}_{company_name}_同花顺_{i+1}.pdf"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        if os.path.exists(filepath):
                            continue
                        
                        if download_pdf(report['pdf_url'], filepath):
                            existing.append(filename)
                            downloaded += 1
                            print(f"        ✓ 下载成功")
                        
                        time.sleep(random.uniform(0.5, 1.5))
                
                time.sleep(random.uniform(1, 3))
        
        print(f"\n本轮完成，当前总数: {len(existing)} 份")
        
        if len(existing) < TARGET_COUNT:
            wait_time = random.uniform(5, 10)
            print(f"等待 {wait_time:.1f} 秒后继续...")
            time.sleep(wait_time)
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    print("="*80)

if __name__ == "__main__":
    main()
