"""
FinRAG 文件操作辅助模块
"""

import os
import json
import yaml
import glob
from typing import List, Dict, Any


def load_config(config_path: str) -> Dict:
    """
    加载 YAML 配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(file_path: str) -> Any:
    """
    加载 JSON 文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        JSON 数据
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, file_path: str):
    """
    保存 JSON 文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_pdf_files(directory: str) -> List[str]:
    """
    获取目录下所有 PDF 文件
    
    Args:
        directory: 目录路径
    
    Returns:
        PDF 文件路径列表
    """
    return glob.glob(os.path.join(directory, "*.pdf"))


def ensure_dir(directory: str):
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)
