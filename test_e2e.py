"""
FinRAG 端到端测试脚本 - 修复版
使用 requests 直接调用 API，绕过 SSL 问题
"""

import os
import sys
import json
import warnings
warnings.filterwarnings('ignore')

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def call_deepseek_api(prompt: str, api_key: str) -> str:
    """使用 requests 直接调用 DeepSeek API"""
    import requests
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()
    
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        return f"API 错误: {result}"

def main():
    print("=" * 60)
    print("FinRAG 端到端测试")
    print("=" * 60)
    
    # 1. 找一个 PDF 文件
    pdf_dir = "data/raw_pdf"
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("错误: 没有找到 PDF 文件")
        return
    
    test_pdf = os.path.join(pdf_dir, pdf_files[0])
    print(f"\n[1/6] 使用测试 PDF: {pdf_files[0]}")
    
    # 2. 解析 PDF
    print("\n[2/6] 解析 PDF...")
    try:
        import pdfplumber
        
        text_content = []
        with pdfplumber.open(test_pdf) as pdf:
            for i, page in enumerate(pdf.pages[:5]):  # 解析前5页
                text = page.extract_text()
                if text:
                    text_content.append({
                        "text": text,
                        "page_num": i + 1
                    })
        
        print(f"    提取了 {len(text_content)} 页文本")
        
    except Exception as e:
        print(f"    解析失败: {e}")
        return
    
    if not text_content:
        print("    没有提取到文本内容")
        return
    
    # 3. 切片
    print("\n[3/6] 切片...")
    chunks = []
    chunk_id = 0
    for page in text_content:
        text = page["text"]
        for i in range(0, len(text), 500):
            chunk_text = text[i:i+500]
            if len(chunk_text) > 50:
                chunk_id += 1
                chunks.append({
                    "id": f"chunk_{chunk_id}",
                    "text": chunk_text,
                    "page_num": page["page_num"],
                    "source": pdf_files[0]
                })
    
    print(f"    生成了 {len(chunks)} 个切片")
    
    # 4. 向量化
    print("\n[4/6] 向量化...")
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("    模型加载成功")
        
        texts = [c["text"] for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=True)
        print(f"    向量维度: {embeddings.shape[1]}")
        
    except Exception as e:
        print(f"    向量化失败: {e}")
        return
    
    # 5. 建立索引
    print("\n[5/6] 建立向量索引...")
    try:
        import faiss
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        print(f"    索引大小: {index.ntotal}")
        
    except Exception as e:
        print(f"    建立索引失败: {e}")
        return
    
    # 6. 问答测试
    print("\n[6/6] 问答测试...")
    print("-" * 40)
    
    import yaml
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_key = config.get("generator", {}).get("llm_api_key", "")
    
    questions = [
        "这份报告的主要内容是什么？",
        "公司的主要业务是什么？",
        "有哪些财务数据？"
    ]
    
    for question in questions:
        print(f"\n问题: {question}")
        
        # 检索
        query_embedding = model.encode([question])
        faiss.normalize_L2(query_embedding)
        
        k = min(3, len(chunks))
        scores, indices = index.search(query_embedding, k)
        
        # 获取相关文档
        context_docs = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(chunks):
                doc = chunks[idx].copy()
                doc["score"] = float(score)
                context_docs.append(doc)
        
        if context_docs:
            context_text = "\n\n".join([f"[文档{i+1}] {d['text']}" for i, d in enumerate(context_docs)])
            
            prompt = f"""请根据以下上下文回答问题。如果上下文中没有相关信息，请说"根据提供的文档无法回答该问题"。

上下文:
{context_text}

问题: {question}

回答:"""
            
            try:
                answer = call_deepseek_api(prompt, api_key)
                print(f"回答: {answer}")
                print(f"来源: 第 {context_docs[0]['page_num']} 页 (相似度: {context_docs[0]['score']:.3f})")
            except Exception as e:
                print(f"API 调用失败: {e}")
        else:
            print("回答: 未找到相关文档")
    
    print("\n" + "=" * 60)
    print("✅ RAG 测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
