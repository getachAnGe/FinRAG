"""
FinRAG 完整流程运行脚本
1. 离线处理：解析PDF → 切片 → 向量化 → 建立索引
2. 在线查询：检索 → LLM生成
"""

import os
import sys
import json
import time
import warnings
warnings.filterwarnings('ignore')

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import yaml
import numpy as np

OUTPUT_DIR = "data/processed"
PDF_DIR = "data/raw_pdf"


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
        "max_tokens": 500
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()
    
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        return f"API错误: {result}"


def step1_parse_pdfs():
    """步骤1: 解析PDF文件"""
    print("\n" + "="*60)
    print("步骤1: 解析PDF文件")
    print("="*60)
    
    import pdfplumber
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 只处理原始的H3_AP开头的真实研报
    all_files = os.listdir(PDF_DIR)
    pdf_files = [f for f in all_files if f.endswith('.pdf') and f.startswith('H3_AP')]
    print(f"找到 {len(pdf_files)} 个真实研报PDF文件")
    
    all_chunks = []
    chunk_id = 0
    
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):  # 解析所有页
                    text = page.extract_text()
                    
                    if text and len(text) > 50:
                        # 简单切片：每500字符一个块
                        for j in range(0, len(text), 500):
                            chunk_text = text[j:j+500]
                            if len(chunk_text) > 50:
                                chunk_id += 1
                                all_chunks.append({
                                    "id": f"chunk_{chunk_id}",
                                    "text": chunk_text,
                                    "source": pdf_file,
                                    "page_num": page_num
                                })
            
            if (i + 1) % 5 == 0:
                print(f"  已处理: {i+1}/{len(pdf_files)} 个PDF, 生成 {len(all_chunks)} 个切片")
                
        except Exception as e:
            print(f"  处理失败: {pdf_file} - {e}")
    
    # 保存切片
    chunks_file = os.path.join(OUTPUT_DIR, "chunks.json")
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False)
    
    print(f"\n✓ 解析完成: {len(pdf_files)} 个PDF → {len(all_chunks)} 个切片")
    print(f"  保存到: {chunks_file}")
    
    return all_chunks


def step2_build_index(chunks):
    """步骤2: 向量化并建立索引"""
    print("\n" + "="*60)
    print("步骤2: 向量化并建立索引")
    print("="*60)
    
    from sentence_transformers import SentenceTransformer
    import faiss
    
    print("加载向量化模型...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    print("✓ 模型加载完成")
    
    print(f"向量化 {len(chunks)} 个文本块...")
    texts = [c["text"] for c in chunks]
    
    # 分批处理
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)
        
        if (i + batch_size) % 500 == 0:
            print(f"  已处理: {min(i+batch_size, len(texts))}/{len(texts)}")
    
    embeddings = np.vstack(all_embeddings)
    print(f"✓ 向量化完成: {embeddings.shape}")
    
    # 建立FAISS索引
    print("建立FAISS索引...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    # 保存索引
    index_file = os.path.join(OUTPUT_DIR, "faiss_index.bin")
    faiss.write_index(index, index_file)
    
    # 保存ID映射
    id_map = [c["id"] for c in chunks]
    id_file = os.path.join(OUTPUT_DIR, "id_map.json")
    with open(id_file, 'w', encoding='utf-8') as f:
        json.dump(id_map, f)
    
    # 保存文档数据
    doc_file = os.path.join(OUTPUT_DIR, "documents.json")
    with open(doc_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False)
    
    print(f"✓ 索引建立完成: {index.ntotal} 个向量")
    print(f"  索引文件: {index_file}")
    
    return model, index, chunks


def step3_online_query(model, index, chunks, api_key):
    """步骤3: 在线查询"""
    print("\n" + "="*60)
    print("步骤3: 在线查询测试")
    print("="*60)
    
    import faiss
    
    questions = [
        "贵州茅台的业绩如何？",
        "半导体行业的发展趋势是什么？",
        "美的集团的财务数据怎么样？",
        "白酒行业的竞争格局如何？",
        "分众传媒的主要业务是什么？"
    ]
    
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
                f"[文档{i+1}] (来源: {d['source']}, 第{d['page_num']}页)\n{d['text']}"
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
                print(f"\n来源: {context_docs[0]['source']} 第{context_docs[0]['page_num']}页 (相似度: {context_docs[0]['score']:.3f})")
            except Exception as e:
                print(f"API调用失败: {e}")
        else:
            print("回答: 未找到相关文档")


def main():
    """主函数"""
    print("="*60)
    print("FinRAG 完整流程运行")
    print("="*60)
    
    # 加载配置
    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_key = config.get("generator", {}).get("llm_api_key", "")
    
    # 检查是否已有处理好的数据
    chunks_file = os.path.join(OUTPUT_DIR, "chunks.json")
    index_file = os.path.join(OUTPUT_DIR, "faiss_index.bin")
    
    if os.path.exists(chunks_file) and os.path.exists(index_file):
        print("\n发现已有处理数据，跳过离线处理")
        print("如需重新处理，请删除 data/processed 目录")
        
        # 加载已有数据
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        from sentence_transformers import SentenceTransformer
        import faiss
        
        print("\n加载模型和索引...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        index = faiss.read_index(index_file)
        
        print(f"✓ 加载完成: {len(chunks)} 个切片, {index.ntotal} 个向量")
    else:
        # 离线处理
        print("\n开始离线处理...")
        chunks = step1_parse_pdfs()
        model, index, chunks = step2_build_index(chunks)
    
    # 在线查询
    step3_online_query(model, index, chunks, api_key)
    
    print("\n" + "="*60)
    print("✅ 完整流程运行完成!")
    print("="*60)


if __name__ == "__main__":
    main()
