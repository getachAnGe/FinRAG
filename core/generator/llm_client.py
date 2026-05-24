"""
FinRAG 大模型客户端模块

支持多种 LLM 后端：
1. OpenAI API (DeepSeek, Qwen 等)
2. 本地模型
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Generator
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """
    大模型客户端
    
    支持：
    1. OpenAI 兼容 API
    2. 流式输出
    3. 多轮对话
    """
    
    def __init__(self, 
                 model_type: str = "openai",
                 model_name: str = "deepseek-chat",
                 api_base: str = "https://api.deepseek.com/v1",
                 api_key: str = None,
                 temperature: float = 0.1,
                 max_tokens: int = 2048):
        """
        初始化 LLM 客户端
        
        Args:
            model_type: 模型类型 (openai/local)
            model_name: 模型名称
            api_base: API 基础 URL
            api_key: API 密钥
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        """
        self.model_type = model_type
        self.model_name = model_name
        self.api_base = api_base
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """
        初始化客户端
        """
        if self.model_type == "openai":
            try:
                from openai import OpenAI
                
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base
                )
                logger.info(f"[OK] OpenAI 客户端初始化完成，模型: {self.model_name}")
                
            except ImportError:
                logger.warning("[!] openai 库未安装，将使用备用方案")
                self.client = None
        else:
            logger.info("[*] 使用本地模型模式")
    
    def generate(self, 
                prompt: str, 
                system_prompt: str = None) -> str:
        """
        生成回复
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
        
        Returns:
            生成的回复
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages)
    
    def chat(self, messages: List[Dict]) -> str:
        """
        多轮对话
        
        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
        
        Returns:
            助手回复
        """
        if self.client is not None:
            return self._openai_chat(messages)
        else:
            return self._fallback_chat(messages)
    
    def _openai_chat(self, messages: List[Dict]) -> str:
        """
        使用 OpenAI API 进行对话
        
        Args:
            messages: 消息列表
        
        Returns:
            回复内容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"[!] API 调用失败: {e}")
            return f"抱歉，生成回复时出现错误: {str(e)}"
    
    def _fallback_chat(self, messages: List[Dict]) -> str:
        """
        备用对话方案
        
        Args:
            messages: 消息列表
        
        Returns:
            回复内容
        """
        last_message = messages[-1]["content"] if messages else ""
        
        return f"[模拟回复] 我理解您的问题是: {last_message[:100]}...\n\n由于未配置有效的 LLM 后端，这是模拟回复。请配置 API 密钥以启用真实回复。"
    
    def stream_generate(self, 
                       prompt: str, 
                       system_prompt: str = None) -> Generator[str, None, None]:
        """
        流式生成回复
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
        
        Yields:
            生成的文本片段
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        if self.client is not None:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                logger.error(f"[!] 流式生成失败: {e}")
                yield f"抱歉，生成回复时出现错误: {str(e)}"
        else:
            response = self._fallback_chat(messages)
            for char in response:
                yield char
                time.sleep(0.01)
    
    def generate_with_context(self,
                             question: str,
                             context: List[Dict],
                             system_prompt: str = None) -> str:
        """
        基于上下文生成回复
        
        Args:
            question: 用户问题
            context: 上下文文档列表
            system_prompt: 系统提示词
        
        Returns:
            生成的回复
        """
        context_text = self._format_context(context)
        
        prompt = f"""请根据以下上下文信息回答问题。

上下文信息：
{context_text}

问题：{question}

请基于上下文信息回答，如果上下文中没有相关信息，请明确说明。"""
        
        return self.generate(prompt, system_prompt)
    
    def _format_context(self, context: List[Dict]) -> str:
        """
        格式化上下文
        
        Args:
            context: 上下文列表
        
        Returns:
            格式化后的文本
        """
        formatted = []
        
        for i, doc in enumerate(context, 1):
            text = doc.get("text", "")
            source = doc.get("source", "未知来源")
            page = doc.get("page_num", "")
            
            formatted.append(f"[Source {i}] (来源: {source}, 第 {page} 页)\n{text}")
        
        return "\n\n".join(formatted)


class DeepSeekClient(LLMClient):
    """
    DeepSeek 客户端
    """
    
    def __init__(self, 
                 api_key: str = None,
                 model_name: str = "deepseek-chat",
                 **kwargs):
        """
        初始化 DeepSeek 客户端
        
        Args:
            api_key: API 密钥
            model_name: 模型名称
        """
        super().__init__(
            model_type="openai",
            model_name=model_name,
            api_base="https://api.deepseek.com/v1",
            api_key=api_key,
            **kwargs
        )


class QwenClient(LLMClient):
    """
    通义千问客户端
    """
    
    def __init__(self, 
                 api_key: str = None,
                 model_name: str = "qwen-turbo",
                 **kwargs):
        """
        初始化通义千问客户端
        
        Args:
            api_key: API 密钥
            model_name: 模型名称
        """
        super().__init__(
            model_type="openai",
            model_name=model_name,
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
            **kwargs
        )
