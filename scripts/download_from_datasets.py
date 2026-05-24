"""
从公开数据集下载金融研报
使用公开可访问的研报资源
"""
import os
import time
import random
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def download_pdf(url: str, filepath: str, max_retries: int = 3) -> bool:
    """下载PDF"""
    for attempt in range(max_retries):
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
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

def main():
    """主函数"""
    print("="*80)
    print("从公开数据集下载金融研报")
    print("="*80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf') and f.startswith(('传媒_', '白酒_', '消费_', '半导体_'))]
    print(f"\n已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*80)
    
    downloaded = 0
    
    print("\n尝试从公开数据集下载...")
    
    public_datasets = [
        ("arXiv金融论文", "https://arxiv.org/pdf/{}.pdf"),
        ("SSRN金融研究", "https://papers.ssrn.com/sol3/Delivery.cfm/{}.pdf"),
        ("RePEc经济学论文", "https://econpapers.repec.org/paper/{}.pdf"),
    ]
    
    arxiv_ids = [
        "2301.00001", "2301.00002", "2301.00003", "2301.00004", "2301.00005",
        "2302.00001", "2302.00002", "2302.00003", "2302.00004", "2302.00005",
        "2303.00001", "2303.00002", "2303.00003", "2303.00004", "2303.00005",
        "2304.00001", "2304.00002", "2304.00003", "2304.00004", "2304.00005",
    ]
    
    for arxiv_id in arxiv_ids:
        if len(existing) >= TARGET_COUNT:
            break
        
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = f"金融研究_{arxiv_id}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        print(f"\n[{len(existing)+1}/{TARGET_COUNT}] 下载 {filename}...")
        
        if download_pdf(url, filepath):
            existing.append(filename)
            downloaded += 1
            print(f"  ✓ 下载成功")
        else:
            print(f"  ✗ 下载失败")
        
        time.sleep(random.uniform(1, 3))
    
    print("\n" + "="*80)
    print("下载统计:")
    print(f"  本次下载: {downloaded} 份")
    print(f"  总计文件: {len(existing)} 份")
    
    if len(existing) < TARGET_COUNT:
        print(f"\n还差 {TARGET_COUNT - len(existing)} 份")
    
    print("="*80)

if __name__ == "__main__":
    main()
