#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 服务包

一个兼容 OpenAI API 格式的智能 API 服务，支持双模式运行：
- if...else 模式：基于关键词匹配的快速响应
- Ollama 模式：集成本地大语言模型的智能对话

主要模块:
- ai_api_server: 主服务器
- config_manager: 配置管理
- mode_manager: 模式管理
- ollama_client: Ollama 客户端
- keywords_data: 关键词数据
- function_calls: Function Call 数据
"""

__version__ = "1.0.0"
__author__ = "AI API Team"
__email__ = "support@ai-api.com"
__description__ = "兼容 OpenAI API 的智能服务"

# 导入主要组件
try:
    from .ai_api_server import app, AIAPIServer
    from .config_manager import ConfigManager
    from .mode_manager import ModeManager, APIMode
    from .ollama_client import OllamaClient
    
    __all__ = [
        'app',
        'AIAPIServer',
        'ConfigManager', 
        'ModeManager',
        'APIMode',
        'OllamaClient'
    ]
    
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ['__version__', '__author__', '__email__', '__description__']


def get_version():
    """获取版本信息
    
    Returns:
        str: 版本号
    """
    return __version__


def get_info():
    """获取包信息
    
    Returns:
        dict: 包的详细信息
    """
    return {
        'name': 'ai-api-service',
        'version': __version__,
        'author': __author__,
        'email': __email__,
        'description': __description__,
        'python_requires': '>=3.7',
        'dependencies': [
            'Flask>=2.3.0',
            'requests>=2.31.0',
            'Werkzeug>=2.3.0'
        ]
    }