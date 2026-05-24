"""
从SEC EDGAR下载真实财务报告
SEC EDGAR是美国证券交易委员会的公开数据库
"""
import os
import time
import random
import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SEC_COMPANIES = {
    "传媒": [
        ("DIS", "华特迪士尼", "0001744489"),
        ("NFLX", "奈飞", "0001065280"),
        ("CMCSA", "康卡斯特", "0001166691"),
        ("VIA", "维亚康姆", "0001412788"),
        ("T", "AT&T", "0000732717"),
    ],
    "白酒": [
        ("STZ", "星座品牌", "0001043006"),
        ("BUD", "百威英博", "0001679273"),
        ("DEO", "帝亚吉欧", "0000320193"),
        ("SAM", "波士顿啤酒", "0001043006"),
        ("TAP", "摩森康胜", "0001158449"),
    ],
    "消费": [
        ("PG", "宝洁", "0000080424"),
        ("KO", "可口可乐", "0000021344"),
        ("PEP", "百事", "0000077476"),
        ("WMT", "沃尔玛", "0000104169"),
        ("COST", "好市多", "0000909832"),
    ],
    "半导体": [
        ("INTC", "英特尔", "0000050863"),
        ("AMD", "超微半导体", "0000002488"),
        ("NVDA", "英伟达", "0001045810"),
        ("TXN", "德州仪器", "0000097476"),
        ("QCOM", "高通", "0000804328"),
    ],
}

def download_file(url: str, filepath: str) -> bool:
    """下载文件"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        
        if response.status_code == 200:
            content = response.content
            
            if len(content) > 10000:
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    except Exception as e:
        print(f"    下载失败: {str(e)[:50]}")
        return False

def get_company_filings(cik: str, filing_type: str = "10-K") -> list:
    """获取公司提交的文件列表"""
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            filings = []
            
            if 'filings' in data and 'recent' in data['filings']:
                recent = data['filings']['recent']
                
                forms = recent.get('form', [])
                accession_numbers = recent.get('accessionNumber', [])
                filing_dates = recent.get('filingDate', [])
                
                for i, form in enumerate(forms):
                    if form == filing_type:
                        filings.append({
                            'form': form,
                            'accession_number': accession_numbers[i],
                            'filing_date': filing_dates[i],
                        })
            
            return filings[:5]
        
        return []
    except Exception as e:
        print(f"    获取文件列表失败: {str(e)[:50]}")
        return []

def download_filing_document(cik: str, accession_number: str, company_name: str, industry: str) -> bool:
    """下载文件文档"""
    try:
        accession_number_clean = accession_number.replace('-', '')
        
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_clean}/"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            html = response.text
            
            if '.pdf' in html.lower():
                import re
                
                pdf_matches = re.findall(r'href="([^"]*\.pdf)"', html, re.IGNORECASE)
                
                if pdf_matches:
                    pdf_url = f"https://www.sec.gov{pdf_matches[0]}"
                    
                    filename = f"{industry}_{company_name}_{accession_number[:10]}.pdf"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    print(f"    找到PDF: {filename}")
                    
                    if download_file(pdf_url, filepath):
                        print(f"      ✓ 下载成功")
                        return True
        
        return False
    except Exception as e:
        print(f"    下载文档失败: {str(e)[:50]}")
        return False

def main():
    """主函数"""
    print("="*80)
    print("从SEC EDGAR下载真实财务报告")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    for industry, companies in SEC_COMPANIES.items():
        print(f"\n下载 {industry} 行业财务报告...")
        
        for ticker, company_name, cik in companies:
            if len(existing) >= TARGET_COUNT:
                break
            
            print(f"\n  公司: {company_name} ({ticker})")
            print(f"  CIK: {cik}")
            
            filings = get_company_filings(cik, "10-K")
            
            print(f"  找到 {len(filings)} 份年报")
            
            for filing in filings:
                if len(existing) >= TARGET_COUNT:
                    break
                
                print(f"\n    文件: {filing['form']} - {filing['filing_date']}")
                
                if download_filing_document(cik, filing['accession_number'], company_name, industry):
                    downloaded += 1
                    existing.append(f"{industry}_{company_name}_{filing['accession_number'][:10]}.pdf")
                
                time.sleep(random.uniform(1, 3))
            
            time.sleep(random.uniform(2, 5))
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份")
    
    print("="*80)

if __name__ == "__main__":
    main()
