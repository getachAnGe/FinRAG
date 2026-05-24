"""
FinRAG 金融研报下载脚本

从东方财富等平台自动下载研报
覆盖行业：传媒、白酒、消费、半导体等
"""

import os
import time
import requests
import random
from typing import List, Dict
import json

# 研报下载配置
REPORT_CONFIG = {
    # 行业关键词映射
    "industries": {
        "传媒": ["传媒", "影视", "游戏", "广告", "出版", "视频", "直播"],
        "白酒": ["白酒", "茅台", "五粮液", "泸州老窖", "洋河", "汾酒", "酒类"],
        "消费": ["消费", "零售", "食品", "饮料", "家电", "服装", "化妆品"],
        "半导体": ["半导体", "芯片", "集成电路", "晶圆", "封测", "存储", "GPU"]
    },
    
    # 重点公司列表
    "companies": {
        "传媒": ["分众传媒", "芒果超媒", "光线传媒", "华策影视", "完美世界", "三七互娱", "吉比特"],
        "白酒": ["贵州茅台", "五粮液", "泸州老窖", "洋河股份", "山西汾酒", "今世缘", "古井贡酒"],
        "消费": ["伊利股份", "海天味业", "美的集团", "格力电器", "中国中免", "珀莱雅", "安井食品"],
        "半导体": ["中芯国际", "韦尔股份", "兆易创新", "北方华创", "紫光国微", "长电科技", "通富微电"]
    }
}

# 东方财富研报API
EASTMONEY_API = {
    "search": "https://reportapi.eastmoney.com/report/list",
    "download": "https://data.eastmoney.com/report/zw_mac.js"
}

# User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]


class ReportDownloader:
    """
    金融研报下载器
    """
    
    def __init__(self, output_dir: str = "data/raw_pdf"):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://data.eastmoney.com/report/"
        })
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.download_count = 0
        self.failed_count = 0
    
    def search_reports(self, 
                      keyword: str, 
                      page_size: int = 50,
                      max_pages: int = 5) -> List[Dict]:
        """
        搜索研报
        
        Args:
            keyword: 搜索关键词
            page_size: 每页数量
            max_pages: 最大页数
        
        Returns:
            研报列表
        """
        reports = []
        
        print(f"\n搜索关键词: {keyword}")
        
        for page in range(1, max_pages + 1):
            try:
                params = {
                    "cb": "datatable",
                    "industryCode": "*",
                    "pageSize": page_size,
                    "industry": "",
                    "rating": "",
                    "ratingChange": "",
                    "beginTime": "",
                    "endTime": "",
                    "pageNo": page,
                    "fields": "",
                    "qType": "0",
                    "orgCode": "",
                    "code": "",
                    "rcode": "",
                    "p": page,
                    "pageNo": page,
                    "pageNum": page,
                    "_": int(time.time() * 1000)
                }
                
                url = f"https://reportapi.eastmoney.com/report/list?cb=datatable&pageSize={page_size}&industryCode=*&qType=0&beginTime=&endTime=&pageNo={page}&fields=&code=&industry=&rating=&ratingChange=&orgCode=&rcode=&_={int(time.time() * 1000)}"
                
                response = self.session.get(url, timeout=30)
                text = response.text
                
                # 解析 JSONP
                if text.startswith("datatable("):
                    json_str = text[9:-2]  # 移除 datatable() 包装
                    data = json.loads(json_str)
                    
                    if "data" in data:
                        for item in data["data"]:
                            reports.append({
                                "title": item.get("title", ""),
                                "code": item.get("code", ""),
                                "name": item.get("name", ""),
                                "date": item.get("publishDate", ""),
                                "url": item.get("pdfUrl", ""),
                                "author": item.get("researcher", ""),
                                "org": item.get("orgSName", "")
                            })
                
                print(f"  第 {page} 页: 获取 {len(data.get('data', []))} 条")
                
                time.sleep(random.uniform(0.5, 1.5))  # 随机延迟
                
            except Exception as e:
                print(f"  第 {page} 页获取失败: {e}")
        
        return reports
    
    def download_report(self, report: Dict) -> bool:
        """
        下载单个研报
        
        Args:
            report: 研报信息
        
        Returns:
            是否成功
        """
        if not report.get("url"):
            return False
        
        try:
            # 生成文件名
            safe_title = "".join(c for c in report["title"] if c.isalnum() or c in " _-")[:50]
            date_str = report.get("date", "")[:10].replace("-", "")
            filename = f"{date_str}_{safe_title}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            if os.path.exists(filepath):
                print(f"  跳过已存在: {filename}")
                return True
            
            # 下载文件
            response = self.session.get(report["url"], timeout=60, stream=True)
            
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.download_count += 1
                print(f"  ✓ [{self.download_count}] {filename}")
                return True
            else:
                self.failed_count += 1
                return False
                
        except Exception as e:
            self.failed_count += 1
            print(f"  ✗ 下载失败: {report.get('title', '')[:30]} - {e}")
            return False
    
    def download_by_industry(self, 
                            industry: str,
                            target_count: int = 75) -> int:
        """
        按行业下载研报
        
        Args:
            industry: 行业名称
            target_count: 目标数量
        
        Returns:
            下载数量
        """
        print(f"\n{'='*60}")
        print(f"下载行业: {industry} (目标: {target_count} 份)")
        print('='*60)
        
        keywords = REPORT_CONFIG["industries"].get(industry, [industry])
        companies = REPORT_CONFIG["companies"].get(industry, [])
        
        all_reports = []
        
        # 按关键词搜索
        for keyword in keywords[:3]:  # 限制关键词数量
            reports = self.search_reports(keyword, page_size=50, max_pages=3)
            all_reports.extend(reports)
            time.sleep(1)
        
        # 按公司搜索
        for company in companies[:5]:  # 限制公司数量
            reports = self.search_reports(company, page_size=30, max_pages=2)
            all_reports.extend(reports)
            time.sleep(1)
        
        # 去重
        seen_titles = set()
        unique_reports = []
        for r in all_reports:
            if r["title"] not in seen_titles:
                seen_titles.add(r["title"])
                unique_reports.append(r)
        
        print(f"\n找到 {len(unique_reports)} 份研报 (去重后)")
        
        # 下载
        downloaded = 0
        for report in unique_reports:
            if downloaded >= target_count:
                break
            
            if self.download_report(report):
                downloaded += 1
            
            time.sleep(random.uniform(0.3, 0.8))  # 随机延迟
        
        return downloaded
    
    def download_all(self, total_target: int = 300):
        """
        下载所有行业研报
        
        Args:
            total_target: 总目标数量
        """
        print("\n" + "="*60)
        print("FinRAG 金融研报下载器")
        print("="*60)
        print(f"目标: {total_target} 份研报")
        print(f"输出目录: {self.output_dir}")
        
        industries = ["传媒", "白酒", "消费", "半导体"]
        per_industry = total_target // len(industries)
        
        total_downloaded = 0
        
        for industry in industries:
            downloaded = self.download_by_industry(industry, per_industry)
            total_downloaded += downloaded
            
            print(f"\n{industry} 行业完成: 下载 {downloaded} 份")
            time.sleep(2)  # 行业间延迟
        
        print("\n" + "="*60)
        print("下载完成!")
        print(f"总计下载: {total_downloaded} 份")
        print(f"失败: {self.failed_count} 份")
        print("="*60)


def create_sample_reports(output_dir: str, count: int = 300):
    """
    创建示例研报信息文件
    
    由于网络限制，创建一个包含研报下载链接的文件
    用户可以手动下载或使用下载工具
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("创建研报下载清单")
    print("="*60)
    
    # 研报下载来源
    sources = {
        "东方财富研报中心": "https://data.eastmoney.com/report/",
        "同花顺研报": "https://stockpage.10jqka.com.cn/000001/",
        "巨潮资讯": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&lastPage=index",
        "慧博投研": "https://www.hibor.com.cn/"
    }
    
    # 重点公司研报链接模板
    companies = {
        "传媒": ["分众传媒(002027)", "芒果超媒(300413)", "光线传媒(300251)", "华策影视(300133)"],
        "白酒": ["贵州茅台(600519)", "五粮液(000858)", "泸州老窖(000568)", "洋河股份(002304)"],
        "消费": ["伊利股份(600887)", "海天味业(603288)", "美的集团(000333)", "格力电器(000651)"],
        "半导体": ["中芯国际(688981)", "韦尔股份(603501)", "兆易创新(603986)", "北方华创(002371)"]
    }
    
    # 创建下载指南
    guide_path = os.path.join(output_dir, "研报下载指南.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write("# FinRAG 金融研报下载指南\n\n")
        f.write(f"目标: 下载约 {count} 份研报\n\n")
        
        f.write("## 下载来源\n\n")
        for name, url in sources.items():
            f.write(f"- [{name}]({url})\n")
        
        f.write("\n## 重点公司列表\n\n")
        for industry, company_list in companies.items():
            f.write(f"### {industry}\n\n")
            for company in company_list:
                f.write(f"- {company}\n")
            f.write("\n")
        
        f.write("## 下载步骤\n\n")
        f.write("1. 访问东方财富研报中心: https://data.eastmoney.com/report/\n")
        f.write("2. 在搜索框输入公司名称或行业关键词\n")
        f.write("3. 筛选条件: 选择「深度报告」「行业研究」\n")
        f.write("4. 点击下载按钮保存 PDF 文件\n")
        f.write("5. 将下载的 PDF 文件放入 `data/raw_pdf/` 目录\n\n")
        
        f.write("## 推荐下载清单\n\n")
        f.write("| 行业 | 数量 | 重点公司 |\n")
        f.write("|------|------|----------|\n")
        f.write("| 传媒 | 75 | 分众传媒、芒果超媒、光线传媒 |\n")
        f.write("| 白酒 | 75 | 贵州茅台、五粮液、泸州老窖 |\n")
        f.write("| 消费 | 75 | 伊利股份、海天味业、美的集团 |\n")
        f.write("| 半导体 | 75 | 中芯国际、韦尔股份、兆易创新 |\n")
    
    print(f"✓ 已创建下载指南: {guide_path}")
    
    # 创建公司代码列表
    codes_path = os.path.join(output_dir, "company_codes.txt")
    with open(codes_path, "w", encoding="utf-8") as f:
        for industry, company_list in companies.items():
            f.write(f"# {industry}\n")
            for company in company_list:
                code = company.split("(")[1].replace(")", "")
                f.write(f"{code}\n")
            f.write("\n")
    
    print(f"✓ 已创建公司代码列表: {codes_path}")
    
    print("\n" + "="*60)
    print("请按照下载指南手动下载研报")
    print("或将已有的研报 PDF 文件放入 data/raw_pdf/ 目录")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 金融研报下载")
    parser.add_argument("--output", type=str, default="data/raw_pdf", help="输出目录")
    parser.add_argument("--count", type=int, default=300, help="目标数量")
    parser.add_argument("--guide", action="store_true", help="只生成下载指南")
    
    args = parser.parse_args()
    
    if args.guide:
        create_sample_reports(args.output, args.count)
    else:
        # 先创建指南
        create_sample_reports(args.output, args.count)
        
        # 尝试自动下载
        print("\n提示: 由于网络限制，建议手动下载研报")
        print("运行 'python download_reports.py --guide' 只生成下载指南")
