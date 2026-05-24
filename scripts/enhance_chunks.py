import json
import re

def extract_company_name(source: str) -> str:
    """
    从来源文件名中提取公司名
    
    Args:
        source: 来源文件名，格式如 "半导体_北方华创_同花顺_5.pdf"
    
    Returns:
        公司名，如 "北方华创"
    """
    parts = source.replace('.pdf', '').split('_')
    if len(parts) >= 2:
        return parts[1]
    return ""

def enhance_chunk_text(chunk: dict) -> str:
    """
    增强chunk文本，添加来源信息和公司名
    
    Args:
        chunk: 原始chunk
    
    Returns:
        增强后的文本
    """
    source = chunk.get('source', '')
    page_num = chunk.get('page_num', '')
    company_name = extract_company_name(source)
    
    original_text = chunk.get('text', '')
    
    if company_name:
        prefix = f"【公司：{company_name}】"
        suffix = f"【来源：{source} 页码：{page_num}】"
        
        enhanced_text = f"{prefix} {original_text} {suffix}"
        
        for _ in range(2):
            enhanced_text = f"{company_name} {enhanced_text}"
        
        return enhanced_text
    else:
        return original_text

def main():
    print("Loading chunks...")
    with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
    
    print(f"Total chunks: {len(all_chunks)}")
    print("Enhancing chunk texts...")
    
    for i, chunk in enumerate(all_chunks):
        chunk['text'] = enhance_chunk_text(chunk)
        
        if (i + 1) % 1000 == 0:
            print(f"Processed {i+1}/{len(all_chunks)} chunks")
    
    print("Saving enhanced chunks...")
    with open('data/chunks/all_chunks_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    main()
