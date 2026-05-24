"""
FinRAG 真实研报下载器
从东方财富、巨潮资讯等网站下载真实PDF研报
"""

import os
import sys
import time
import random
import requests
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = r"d:\学习学习学习\论文\项目-rag\FinRAG\data\raw_pdf"
TARGET_COUNT = 300

# 行业和公司配置
INDUSTRIES = {
    "传媒": ["分众传媒", "芒果超媒", "光线传媒", "华策影视", "完美世界", "三七互娱", "吉比特", "昆仑万维", "巨人网络", "恺英网络"],
    "白酒": ["贵州茅台", "五粮液", "泸州老窖", "洋河股份", "山西汾酒", "今世缘", "古井贡酒", "酒鬼酒", "水井坊", "舍得酒业"],
    "消费": ["伊利股份", "海天味业", "美的集团", "格力电器", "中国中免", "珀莱雅", "安井食品", "三只松鼠", "良品铺子", "永辉超市"],
    "半导体": ["中芯国际", "韦尔股份", "兆易创新", "北方华创", "紫光国微", "长电科技", "通富微电", "华天科技", "晶方科技", "卓胜微"]
}

# 公司代码映射
COMPANY_CODES = {
    "分众传媒": "002027", "芒果超媒": "300413", "光线传媒": "300251", "华策影视": "300133",
    "完美世界": "002624", "三七互娱": "002555", "吉比特": "603444", "昆仑万维": "300418",
    "巨人网络": "002517", "恺英网络": "002517",
    "贵州茅台": "600519", "五粮液": "000858", "泸州老窖": "000568", "洋河股份": "002304",
    "山西汾酒": "600809", "今世缘": "603369", "古井贡酒": "000596", "酒鬼酒": "000799",
    "水井坊": "600779", "舍得酒业": "600702",
    "伊利股份": "600887", "海天味业": "603288", "美的集团": "000333", "格力电器": "000651",
    "中国中免": "601888", "珀莱雅": "603605", "安井食品": "603345", "三只松鼠": "300783",
    "良品铺子": "603719", "永辉超市": "601933",
    "中芯国际": "688981", "韦尔股份": "603501", "兆易创新": "603986", "北方华创": "002371",
    "紫光国微": "002049", "长电科技": "600584", "通富微电": "002156", "华天科技": "002185",
    "晶方科技": "603005", "卓胜微": "300782"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class RealReportDownloader:
    """真实研报下载器"""
    
    def __init__(self, output_dir: str, target_count: int):
        self.output_dir = output_dir
        self.target_count = target_count
        self.session = requests.Session()
        self.downloaded = 0
        self.failed = 0
        
        # 统计已有文件
        self.existing = set()
        for f in os.listdir(output_dir):
            if f.endswith('.pdf'):
                self.existing.add(f)
        
        print(f"已有研报: {len(self.existing)} 份")
        print(f"目标数量: {target_count} 份")
    
    def get_headers(self) -> Dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/pdf,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
    
    def download_from_eastmoney(self, company: str, code: str) -> int:
        """从东方财富下载研报"""
        downloaded = 0
        
        # 东方财富研报API
        url = f"https://reportapi.eastmoney.com/report/list"
        
        try:
            params = {
                "cb": "datatable",
                "industryCode": "*",
                "pageSize": 30,
                "industry": "",
                "rating": "",
                "ratingChange": "",
                "beginTime": "",
                "endTime": "",
                "pageNo": 1,
                "fields": "",
                "qType": "0",
                "orgCode": "",
                "code": code,
                "rcode": "",
                "_": int(time.time() * 1000)
            }
            
            headers = self.get_headers()
            headers["Referer"] = f"https://data.eastmoney.com/report/stock.jshtml?code={code}"
            
            response = self.session.get(url, params=params, headers=headers, timeout=30, verify=False)
            text = response.text
            
            # 解析JSONP
            match = re.search(r'datatable\((.*)\)', text)
            if match:
                data = json.loads(match.group(1))
                
                for item in data.get("data", []):
                    if self.downloaded + len(self.existing) >= self.target_count:
                        break
                    
                    title = item.get("title", "")
                    pdf_url = item.get("pdfUrl", "")
                    
                    if not pdf_url:
                        continue
                    
                    # 生成文件名
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
                    date_str = item.get("publishDate", "")[:10].replace("-", "")
                    filename = f"EM_{date_str}_{company}_{safe_title}.pdf"
                    
                    if filename in self.existing:
                        continue
                    
                    filepath = os.path.join(self.output_dir, filename)
                    
                    # 下载PDF
                    try:
                        pdf_response = self.session.get(pdf_url, headers=self.get_headers(), timeout=60, stream=True, verify=False)
                        
                        if pdf_response.status_code == 200:
                            content = pdf_response.content
                            
                            # 检查是否为真实PDF
                            if len(content) > 10000 and content[:4] == b'%PDF':
                                with open(filepath, "wb") as f:
                                    f.write(content)
                                
                                self.existing.add(filename)
                                self.downloaded += 1
                                downloaded += 1
                                print(f"✓ [{len(self.existing)}/{self.target_count}] {company}: {filename[:40]}...")
                            else:
                                self.failed += 1
                        
                        time.sleep(random.uniform(0.3, 0.8))
                        
                    except Exception as e:
                        self.failed += 1
        
        except Exception as e:
            print(f"  获取{company}研报列表失败: {e}")
        
        return downloaded
    
    def download_from_cninfo(self, company: str, code: str) -> int:
        """从巨潮资讯下载研报"""
        downloaded = 0
        
        # 巨潮资讯API
        url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        
        try:
            data = {
                "stock": f"{code},gssh{code}",
                "tabName": "fulltext",
                "pageSize": 30,
                "pageNum": 1,
                "column": "szse",
                "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh",
                "isHLtitle": "true"
            }
            
            headers = self.get_headers()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Referer"] = "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search"
            
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            result = response.json()
            
            for item in result.get("announcements", []):
                if self.downloaded + len(self.existing) >= self.target_count:
                    break
                
                title = item.get("announcementTitle", "")
                adj_url = item.get("adjunctUrl", "")
                
                if not adj_url:
                    continue
                
                pdf_url = f"http://static.cninfo.com.cn/{adj_url}"
                
                # 生成文件名
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
                date_str = item.get("announcementTime", "")[:10].replace("-", "")
                filename = f"CN_{date_str}_{company}_{safe_title}.pdf"
                
                if filename in self.existing:
                    continue
                
                filepath = os.path.join(self.output_dir, filename)
                
                # 下载PDF
                try:
                    pdf_response = self.session.get(pdf_url, headers=self.get_headers(), timeout=60, stream=True)
                    
                    if pdf_response.status_code == 200:
                        content = pdf_response.content
                        
                        if len(content) > 10000 and content[:4] == b'%PDF':
                            with open(filepath, "wb") as f:
                                f.write(content)
                            
                            self.existing.add(filename)
                            self.downloaded += 1
                            downloaded += 1
                            print(f"✓ [{len(self.existing)}/{self.target_count}] {company}: {filename[:40]}...")
                        else:
                            self.failed += 1
                    
                    time.sleep(random.uniform(0.3, 0.8))
                    
                except Exception as e:
                    self.failed += 1
        
        except Exception as e:
            print(f"  巨潮资讯获取{company}研报失败: {e}")
        
        return downloaded
    
    def run(self):
        """运行下载"""
        print("\n" + "="*60)
        print("FinRAG 真实研报下载器")
        print("="*60)
        
        total_needed = self.target_count - len(self.existing)
        print(f"还需下载: {total_needed} 份")
        print("="*60)
        
        # 遍历所有公司和行业
        for industry, companies in INDUSTRIES.items():
            if len(self.existing) >= self.target_count:
                break
            
            print(f"\n行业: {industry}")
            
            for company in companies:
                if len(self.existing) >= self.target_count:
                    break
                
                code = COMPANY_CODES.get(company, "")
                if not code:
                    continue
                
                print(f"  下载 {company} ({code}) 研报...")
                
                # 从东方财富下载
                count = self.download_from_eastmoney(company, code)
                
                # 从巨潮资讯下载
                if len(self.existing) < self.target_count:
                    count += self.download_from_cninfo(company, code)
                
                print(f"    下载: {count} 份")
                
                time.sleep(random.uniform(1, 2))
        
        # 最终统计
        print("\n" + "="*60)
        print("下载完成!")
        print(f"总计: {len(self.existing)} 份研报")
        print(f"本次下载: {self.downloaded} 份")
        print(f"失败: {self.failed} 次")
        print("="*60)
        
        return len(self.existing)


if __name__ == "__main__":
    downloader = RealReportDownloader(OUTPUT_DIR, TARGET_COUNT)
    downloader.run()
