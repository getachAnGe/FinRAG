import json
import re

def find_metrics_in_chunk(chunk):
    text = chunk.get('text', '')
    source = chunk.get('source', '')
    page_num = chunk.get('page_num', '')
    
    results = []
    
    patterns = [
        (r'(?:营业收入|营业总收入)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '营业收入'),
        (r'(?:归属于上市公司股东的净利润|归属于母公司所有者的净利润|净利润)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '净利润'),
        (r'(?:加权平均净资产收益率|净资产收益率|ROE)[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '净资产收益率'),
        (r'(?:基本每股收益|每股收益)[：:\s]*?([\d,]+(?:\.\d+)?)\s*元', '每股收益'),
        (r'毛利率[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '毛利率'),
        (r'(?:研发投入|研发费用)[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '研发投入'),
        (r'总资产[：:\s]*?([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)', '总资产'),
        (r'资产负债率[：:\s]*?([\d,]+(?:\.\d+)?)\s*%', '资产负债率'),
    ]
    
    for pattern, indicator in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            value = match[0]
            unit = match[1] if len(match) > 1 else ''
            results.append({
                'value': value + unit,
                'indicator': indicator
            })
    
    return results

def extract_company_name(source):
    if not source:
        return ""
    if source.startswith('H3_'):
        return ""
    parts = source.replace('.pdf', '').split('_')
    if len(parts) >= 2:
        return parts[1]
    return ""

def has_chinese(text):
    return any('\u4e00' <= c <= '\u9fff' for c in text)

def main():
    print("Loading chunks...")
    with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
    
    print(f"Total chunks: {len(all_chunks)}")
    print("Scanning for financial metrics...")
    
    eval_samples = []
    
    for chunk in all_chunks:
        source = chunk.get('source', '')
        if not has_chinese(source) or source.startswith('H3_'):
            continue
        
        company = extract_company_name(source)
        if not company:
            continue
        
        metrics = find_metrics_in_chunk(chunk)
        if metrics:
            for metric in metrics:
                query = f"在{source.replace('.pdf', '')}第{chunk['page_num']}页中，{company}的{metric['indicator']}是多少？"
                
                eval_samples.append({
                    'query': query,
                    'query_type': 'fact',
                    'ground_truth_answer': metric['value'],
                    'ground_truth_chunk_id': chunk['id'],
                    'source_file': source,
                    'page_num': chunk['page_num'],
                    'company': company,
                    'indicator': metric['indicator']
                })
    
    print(f"Found {len(eval_samples)} valid (question, answer, chunk_id) triples")
    
    unique_samples = []
    seen = set()
    for sample in eval_samples:
        key = (sample['company'], sample['indicator'], sample['ground_truth_answer'])
        if key not in seen and len(sample['ground_truth_answer']) >= 3:
            seen.add(key)
            unique_samples.append(sample)
    
    print(f"Unique samples after deduplication: {len(unique_samples)}")
    
    result = {
        'metadata': {
            'total_samples': len(unique_samples),
            'fact_samples': len(unique_samples),
            'description': '从chunk中实际提取的评测集，确保答案真实存在'
        },
        'samples': unique_samples[:100]
    }
    
    with open('data/eval/eval_dataset_correct.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Saved to data/eval/eval_dataset_correct.json")
    
    print("\n验证前10条：")
    for i, sample in enumerate(unique_samples[:10], 1):
        print(f"{i}. [{sample['company']}] {sample['indicator']}: {sample['ground_truth_answer']}")

if __name__ == "__main__":
    main()
