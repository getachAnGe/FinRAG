"""
从中国金融网站下载真实研报
尝试多种方法下载A股财务报告和券商研报
"""
import os
import time
import random
import requests
import urllib3
import re
from urllib.parse import quote

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

def download_pdf(url: str, filepath: str, max_retries: int = 3) -> bool:
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
            
            time.sleep(random.uniform(2, 5))
        except:
            time.sleep(random.uniform(2, 5))
    
    return False

def try_eastmoney_reports(code: str, company_name: str) -> list:
    """尝试从东方财富获取研报"""
    try:
        url = f"https://reportapi.eastmoney.com/report/list?cb=&pageNo=1&pageSize=50&code={code}&industryCode=*&qType=0"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://data.eastmoney.com/",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            text = response.text
            
            json_match = re.search(r'\((.*?)\)', text, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group(1))
                
                reports = []
                
                if 'data' in data:
                    for item in data['data']:
                        title = item.get('title', '')
                        pdf_url = item.get('pdfUrl', '')
                        
                        if pdf_url and pdf_url.startswith('http'):
                            reports.append({
                                'title': title,
                                'pdf_url': pdf_url,
                            })
                
                return reports[:10]
        
        return []
    except:
        return []

def try_cninfo_announcements(code: str, company_name: str) -> list:
    """尝试从巨潮资讯获取公告"""
    try:
        url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        
        data = {
            "stock": f"{code},gssh{code}",
            "tabName": "fulltext",
            "pageSize": 50,
            "pageNum": 1,
            "column": "szse" if code.startswith(("0", "3")) else "sse",
            "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh",
            "isHLtitle": "true",
        }
        
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        response = requests.post(url, data=data, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            announcements = []
            
            if 'announcements' in result:
                for item in result['announcements']:
                    title = item.get('announcementTitle', '')
                    adjunct_url = item.get('adjunctUrl', '')
                    
                    if adjunct_url:
                        pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}"
                        
                        announcements.append({
                            'title': title,
                            'pdf_url': pdf_url,
                        })
            
            return announcements[:10]
        
        return []
    except:
        return []

def main():
    """主函数"""
    print("="*80)
    print("从中国金融网站下载真实研报")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    for industry, codes in INDUSTRIES.items():
        print(f"\n下载 {industry} 行业研报...")
        
        for code in codes:
            if len(existing) >= TARGET_COUNT:
                break
            
            company_name = COMPANY_NAMES.get(code, code)
            
            print(f"\n  公司: {company_name} ({code})")
            
            print(f"    尝试东方财富研报...")
            reports = try_eastmoney_reports(code, company_name)
            
            if reports:
                print(f"    找到 {len(reports)} 份研报")
                
                for i, report in enumerate(reports):
                    if len(existing) >= TARGET_COUNT:
                        break
                    
                    title = report['title'][:30]
                    pdf_url = report['pdf_url']
                    
                    filename = f"{industry}_{company_name}_研报_{i+1}.pdf"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        continue
                    
                    print(f"      下载: {title}...")
                    
                    if download_pdf(pdf_url, filepath):
                        existing.append(filename)
                        downloaded += 1
                        print(f"        ✓ 下载成功")
                    
                    time.sleep(random.uniform(1, 3))
            
            print(f"    尝试巨潮资讯公告...")
            announcements = try_cninfo_announcements(code, company_name)
            
            if announcements:
                print(f"    找到 {len(announcements)} 份公告")
                
                for i, ann in enumerate(announcements):
                    if len(existing) >= TARGET_COUNT:
                        break
                    
                    title = ann['title'][:30]
                    pdf_url = ann['pdf_url']
                    
                    filename = f"{industry}_{company_name}_公告_{i+1}.pdf"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        continue
                    
                    print(f"      下载: {title}...")
                    
                    if download_pdf(pdf_url, filepath):
                        existing.append(filename)
                        downloaded += 1
                        print(f"        ✓ 下载成功")
                    
                    time.sleep(random.uniform(1, 3))
            
            time.sleep(random.uniform(2, 5))
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份")
    else:
        print("\n✓ 已达到目标数量！")
    
    print("="*80)

if __name__ == "__main__":
    main()
