"""
继续从SEC EDGAR下载真实财务报告
增加更多公司和报告类型
"""
import os
import time
import random
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SEC_COMPANIES_EXTENDED = {
    "传媒": [
        ("DIS", "华特迪士尼", "0001744489"),
        ("NFLX", "奈飞", "0001065280"),
        ("CMCSA", "康卡斯特", "0001166691"),
        ("T", "AT&T", "0000732717"),
        ("VIA", "维亚康姆", "0001412788"),
        ("FOXA", "福克斯", "0001308734"),
        ("CBS", "哥伦比亚广播", "0000813828"),
        ("TWX", "时代华纳", "0001105605"),
        ("DISCA", "探索传播", "0001437287"),
        ("SIRI", "天狼星XM", "0001090735"),
    ],
    "白酒": [
        ("STZ", "星座品牌", "0001043006"),
        ("BUD", "百威英博", "0001679273"),
        ("DEO", "帝亚吉欧", "0000320193"),
        ("TAP", "摩森康胜", "0001158449"),
        ("SAM", "波士顿啤酒", "0001043006"),
        ("BF-B", "布朗福曼", "0000087388"),
        ("CCU", "康帕斯集团", "0001031297"),
        ("FMX", "Fomento Economico", "0001056092"),
        ("ABEV", "Ambev", "0001535909"),
        ("HEINY", "喜力", "0001010539"),
    ],
    "消费": [
        ("PG", "宝洁", "0000080424"),
        ("KO", "可口可乐", "0000021344"),
        ("PEP", "百事", "0000077476"),
        ("WMT", "沃尔玛", "0000104169"),
        ("COST", "好市多", "0000909832"),
        ("CL", "高露洁", "0000021665"),
        ("KMB", "金佰利", "0000055785"),
        ("GIS", "通用磨坊", "0000058073"),
        ("K", "家乐氏", "0000055067"),
        ("SJM", "盛美家", "0000103128"),
        ("HSY", "好时", "0000047111"),
        ("CPB", "金宝汤", "0000037740"),
        ("HRL", "荷美尔食品", "0000064822"),
        ("CHD", "切迟杜尔", "0000035527"),
        ("CLX", "高乐氏", "0000026673"),
    ],
    "半导体": [
        ("INTC", "英特尔", "0000050863"),
        ("AMD", "超微半导体", "0000002488"),
        ("NVDA", "英伟达", "0001045810"),
        ("TXN", "德州仪器", "0000097476"),
        ("QCOM", "高通", "0000804328"),
        ("MU", "美光科技", "0000723125"),
        ("AMAT", "应用材料", "0000006281"),
        ("LRCX", "拉姆研究", "0000732581"),
        ("KLAC", "科磊", "0000319855"),
        ("ADI", "亚德诺半导体", "0000006281"),
        ("AVGO", "博通", "0001420528"),
        ("MRVL", "美满电子", "0001043006"),
        ("ON", "安森美半导体", "0001103642"),
        ("SWKS", "思佳讯", "0001116703"),
        ("QRVO", "威讯联合半导体", "0001579241"),
    ],
}

def download_file(url: str, filepath: str) -> bool:
    """下载文件"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        
        if response.status_code == 200:
            content = response.content
            
            if len(content) > 10000:
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    except:
        return False

def get_company_filings(cik: str, filing_types: list = ["10-K", "10-Q"]) -> list:
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
                primary_documents = recent.get('primaryDocument', [])
                
                for i, form in enumerate(forms):
                    if form in filing_types:
                        filings.append({
                            'form': form,
                            'accession_number': accession_numbers[i],
                            'filing_date': filing_dates[i],
                            'primary_document': primary_documents[i] if i < len(primary_documents) else '',
                        })
            
            return filings[:10]
        
        return []
    except:
        return []

def main():
    """主函数"""
    print("="*80)
    print("继续从SEC EDGAR下载真实财务报告")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    for industry, companies in SEC_COMPANIES_EXTENDED.items():
        print(f"\n下载 {industry} 行业财务报告...")
        
        for ticker, company_name, cik in companies:
            if len(existing) >= TARGET_COUNT:
                break
            
            print(f"\n  公司: {company_name} ({ticker})")
            
            filings = get_company_filings(cik, ["10-K", "10-Q"])
            
            print(f"  找到 {len(filings)} 份报告")
            
            for filing in filings:
                if len(existing) >= TARGET_COUNT:
                    break
                
                accession_number_clean = filing['accession_number'].replace('-', '')
                primary_doc = filing['primary_document']
                
                if primary_doc:
                    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_clean}/{primary_doc}"
                    
                    filename = f"{industry}_{company_name}_{filing['form']}_{filing['filing_date']}.html"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        continue
                    
                    print(f"    下载: {filing['form']} - {filing['filing_date']}")
                    
                    if download_file(url, filepath):
                        downloaded += 1
                        existing.append(filename)
                        print(f"      ✓ 下载成功")
                
                time.sleep(random.uniform(0.3, 0.8))
            
            time.sleep(random.uniform(0.5, 1.5))
    
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
