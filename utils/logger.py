"""
FinRAG 日志管理模块
"""

import os
import logging
import yaml
from datetime import datetime


def setup_logging(config_path: str = None):
    """
    配置日志系统
    
    Args:
        config_path: 配置文件路径
    """
    log_config = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "logs/finrag.log"
    }
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if "logging" in config:
                log_config.update(config["logging"])
    
    os.makedirs(os.path.dirname(log_config["file"]), exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_config["level"]),
        format=log_config["format"],
        handlers=[
            logging.FileHandler(log_config["file"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("FinRAG")
