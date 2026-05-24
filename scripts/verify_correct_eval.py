import json
import re

def contains_answer(chunk_text, answer):
    if answer in chunk_text:
        return True
    
    answer_no_comma = answer.replace(',', '')
    if answer_no_comma in chunk_text:
        return True
    
    match = re.search(r'[\d,]+(?:\.\d+)?', answer)
    if match:
        numeric_part = match.group()
        numeric_part_no_comma = numeric_part.replace(',', '')
        if numeric_part in chunk_text or numeric_part_no_comma in chunk_text:
            return True
    
    return False

def main():
    print("Loading eval dataset...")
    with open('data/eval/eval_dataset_correct.json', 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    
    print("Loading chunks...")
    with open('data/chunks/all_chunks.json', 'r', encoding='utf-8') as f:
        chunks = {c['id']: c for c in json.load(f)}
    
    samples = eval_data['samples']
    verified = 0
    missing = 0
    
    for i, sample in enumerate(samples, 1):
        chunk_id = sample['ground_truth_chunk_id']
        answer = sample['ground_truth_answer']
        
        if chunk_id in chunks:
            chunk_text = chunks[chunk_id]['text']
            if contains_answer(chunk_text, answer):
                status = '✅'
                verified += 1
            else:
                status = '❌'
                missing += 1
        else:
            status = '❌'
            missing += 1
        
        if i <= 20 or status == '❌':
            print(f'{i}. {status} [{sample["company"]}] {sample["indicator"]}: {answer}')
    
    print(f'\n=== 验证结果 ===')
    print(f'✅ 答案存在: {verified}/{len(samples)}')
    print(f'❌ 答案缺失: {missing}/{len(samples)}')

if __name__ == "__main__":
    main()
