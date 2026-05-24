"""
FinRAG 研报下载器 - 巨潮资讯版
从巨潮资讯下载真实公告PDF
"""

import os
import time
import random
import requests
import urllib3
import re
import json
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

# 公司代码列表
COMPANY_CODES = [
    # 传媒
    "002027", "300413", "300251", "300133", "002624", "002555", "603444", "300418", "002517",
    # 白酒
    "600519", "000858", "000568", "002304", "600809", "603369", "000596", "000799", "600779", "600702",
    # 消费
    "600887", "603288", "000333", "000651", "601888", "603605", "603345", "300783", "603719", "601933",
    # 半导体
    "688981", "603501", "603986", "002371", "002049", "600584", "002156", "002185", "603005", "300782"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "http://www.cninfo.com.cn/",
    }


def search_cninfo(code: str, page: int = 1) -> list:
    """搜索巨潮资讯公告"""
    url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    
    data = {
        "stock": f"{code},gssh{code}",
        "tabName": "fulltext",
        "pageSize": 30,
        "pageNum": page,
        "column": "szse" if code.startswith("0") or code.startswith("3") else "sse",
        "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh",
        "isHLtitle": "true",
        "seDate": "",
        "showTitle": ""
    }
    
    headers = get_headers()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=30)
        result = response.json()
        
        announcements = []
        for item in result.get("announcements", []):
            title = item.get("announcementTitle", "")
            adjunct_url = item.get("adjunctUrl", "")
            date = item.get("announcementTime", "")
            
            if adjunct_url:
                announcements.append({
                    "title": title,
                    "url": f"http://static.cninfo.com.cn/{adjunct_url}",
                    "date": date
                })
        
        return announcements
    
    except Exception as e:
        print(f"搜索失败 {code}: {e}")
        return []


def download_pdf(url: str, filepath: str) -> bool:
    """下载PDF"""
    try:
        response = requests.get(url, headers=get_headers(), timeout=60, stream=True)
        
        if response.status_code == 200:
            content = response.content
            
            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(filepath, "wb") as f:
                    f.write(content)
                return True
        
        return False
    
    except:
        return False


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 研报下载器 - 巨潮资讯版")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 统计已有文件
    existing = set()
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.pdf'):
            existing.add(f)
    
    print(f"已有研报: {len(existing)} 份")
    print(f"目标数量: {TARGET_COUNT} 份")
    print("="*60)
    
    downloaded = 0
    
    for code in COMPANY_CODES:
        if len(existing) >= TARGET_COUNT:
            break
        
        print(f"\n搜索代码: {code}")
        
        # 搜索公告
        announcements = search_cninfo(code)
        
        for ann in announcements:
            if len(existing) >= TARGET_COUNT:
                break
            
            # 生成文件名
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', ann["title"])[:40]
            date_str = str(ann["date"])[:10].replace("-", "")
            filename = f"CNINFO_{date_str}_{code}_{safe_title}.pdf"
            
            if filename in existing:
                continue
            
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # 下载
            if download_pdf(ann["url"], filepath):
                existing.add(filename)
                downloaded += 1
                print(f"✓ [{len(existing)}/{TARGET_COUNT}] {filename[:50]}...")
            
            time.sleep(random.uniform(0.3, 0.6))
        
        time.sleep(random.uniform(0.5, 1))
    
    print("\n" + "="*60)
    print("下载完成!")
    print(f"总计: {len(existing)} 份研报")
    print(f"本次下载: {downloaded} 份")
    print("="*60)


if __name__ == "__main__":
    main()
