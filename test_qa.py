"""
FinRAG 交互式问答
"""

import os
import sys
import json
import warnings
warnings.filterwarnings('ignore')

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import yaml
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

OUTPUT_DIR = "data/processed"


def call_deepseek_api(prompt: str, api_key: str) -> str:
    """调用DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 800
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()
    
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        return f"API错误: {result}"


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 交互式问答系统")
    print("="*60)
    
    # 加载配置
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_key = config.get("generator", {}).get("llm_api_key", "")
    
    # 加载模型和数据
    print("\n加载模型和数据...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    index = faiss.read_index(os.path.join(OUTPUT_DIR, "faiss_index.bin"))
    
    with open(os.path.join(OUTPUT_DIR, "chunks.json"), 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"✓ 加载完成: {len(chunks)} 个切片")
    
    # 测试问题（与研报内容相关）
    questions = [
        "万达电影2024年的业绩如何？",
        "电影行业2024年的发展情况怎么样？",
        "万达电影的主要业务是什么？",
        "万达电影2025年的展望如何？",
        "电影票房2024年同比变化多少？"
    ]
    
    print("\n" + "="*60)
    print("开始问答测试")
    print("="*60)
    
    for question in questions:
        print(f"\n问题: {question}")
        print("-"*40)
        
        # 向量化问题
        query_embedding = model.encode([question])
        faiss.normalize_L2(query_embedding)
        
        # 检索
        k = 3
        scores, indices = index.search(query_embedding, k)
        
        # 获取相关文档
        context_docs = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(chunks):
                doc = chunks[idx].copy()
                doc["score"] = float(score)
                context_docs.append(doc)
        
        if context_docs:
            # 构建上下文
            context_text = "\n\n".join([
                f"[文档{i+1}] {d['text']}"
                for i, d in enumerate(context_docs)
            ])
            
            # 生成回答
            prompt = f"""请根据以下上下文回答问题。如果上下文中没有相关信息，请说"根据提供的文档无法回答该问题"。

上下文:
{context_text}

问题: {question}

回答:"""
            
            try:
                answer = call_deepseek_api(prompt, api_key)
                print(f"回答: {answer}")
                print(f"\n来源: {context_docs[0]['source']} 第{context_docs[0]['page_num']}页")
                print(f"相似度: {context_docs[0]['score']:.3f}")
            except Exception as e:
                print(f"API调用失败: {e}")
        else:
            print("回答: 未找到相关文档")
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()
