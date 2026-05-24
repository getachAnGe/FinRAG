import json
import os

def verify_answers():
    print("Loading eval dataset...")
    with open('data/eval/eval_dataset_precise.json', 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    
    print("Loading all chunks...")
    with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
    
    chunk_dict = {c['id']: c for c in all_chunks}
    
    samples = eval_data['samples']
    fact_samples = [s for s in samples if s['query_type'] == 'fact']
    
    print(f"\n=== 验证 {len(fact_samples)} 条事实型问题 ===")
    
    verified_count = 0
    missing_count = 0
    missing_details = []
    
    for i, sample in enumerate(fact_samples, 1):
        query = sample['query']
        answer = sample['ground_truth_answer']
        chunk_id = sample['ground_truth_chunk_id']
        company = sample['company']
        indicator = sample['indicator']
        
        if chunk_id in chunk_dict:
            chunk_text = chunk_dict[chunk_id]['text']
            
            answer_numeric = ''.join([c for c in answer if c.isdigit() or c in '.%'])
            
            if answer in chunk_text or answer_numeric in chunk_text:
                status = "✅"
                verified_count += 1
            else:
                status = "❌"
                missing_count += 1
                missing_details.append({
                    'index': i,
                    'query': query,
                    'answer': answer,
                    'chunk_id': chunk_id
                })
        else:
            status = "❌ chunk不存在"
            missing_count += 1
            missing_details.append({
                'index': i,
                'query': query,
                'answer': answer,
                'chunk_id': chunk_id,
                'error': 'chunk不存在'
            })
        
        if i <= 20 or i % 10 == 0 or status == "❌":
            print(f"{i}. {status} [{company}] {indicator}: {answer}")
    
    print(f"\n=== 验证结果 ===")
    print(f"✅ 答案存在: {verified_count}/{len(fact_samples)}")
    print(f"❌ 答案缺失: {missing_count}/{len(fact_samples)}")
    
    if missing_count > 0:
        print("\n=== 缺失详情 ===")
        for detail in missing_details[:10]:
            print(f"{detail['index']}. {detail['query']}")
            print(f"   期望答案: {detail['answer']}")
            print(f"   Chunk ID: {detail['chunk_id']}")
            if 'error' in detail:
                print(f"   错误: {detail['error']}")
            print()
    
    return verified_count, missing_count

if __name__ == "__main__":
    verify_answers()
