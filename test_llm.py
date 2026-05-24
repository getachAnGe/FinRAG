"""
FinRAG 简化测试脚本
直接测试 LLM 功能，无需 Embedding 模型
"""

import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI

def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_llm():
    """测试 LLM"""
    config = load_config()
    
    gen_config = config.get("generator", {})
    
    client = OpenAI(
        api_key=gen_config.get("llm_api_key", ""),
        base_url=gen_config.get("llm_api_base", "https://api.deepseek.com/v1")
    )
    
    print("=" * 60)
    print("FinRAG LLM 测试")
    print("=" * 60)
    print(f"模型: {gen_config.get('llm_model', 'deepseek-chat')}")
    print(f"API: {gen_config.get('llm_api_base', '')}")
    print("=" * 60)
    
    questions = [
        "你好，请介绍一下你自己",
        "什么是RAG？请简单解释",
        "金融研报分析中，毛利率如何计算？"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n问题 {i}: {question}")
        print("-" * 40)
        
        try:
            response = client.chat.completions.create(
                model=gen_config.get("llm_model", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": "你是一个专业的金融分析助手。"},
                    {"role": "user", "content": question}
                ],
                temperature=gen_config.get("temperature", 0.1),
                max_tokens=gen_config.get("max_tokens", 500)
            )
            
            answer = response.choices[0].message.content
            print(f"回答: {answer}")
            
        except Exception as e:
            print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

def interactive_mode():
    """交互模式"""
    config = load_config()
    gen_config = config.get("generator", {})
    
    client = OpenAI(
        api_key=gen_config.get("llm_api_key", ""),
        base_url=gen_config.get("llm_api_base", "https://api.deepseek.com/v1")
    )
    
    print("\n" + "=" * 60)
    print("FinRAG 交互模式 (输入 quit 退出)")
    print("=" * 60)
    
    messages = [
        {"role": "system", "content": "你是一个专业的金融分析助手，请基于事实回答问题。"}
    ]
    
    while True:
        try:
            question = input("\n请输入问题: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("再见!")
                break
            
            if not question:
                continue
            
            messages.append({"role": "user", "content": question})
            
            response = client.chat.completions.create(
                model=gen_config.get("llm_model", "deepseek-chat"),
                messages=messages,
                temperature=gen_config.get("temperature", 0.1),
                max_tokens=gen_config.get("max_tokens", 1024)
            )
            
            answer = response.choices[0].message.content
            print(f"\n回答: {answer}")
            
            messages.append({"role": "assistant", "content": answer})
            
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinRAG 简化测试")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        test_llm()
