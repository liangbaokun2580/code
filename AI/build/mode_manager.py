#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式管理器
管理 if...else 模式和 Ollama 模式的切换
"""

import json
import os
from typing import Dict, Any, Optional
from enum import Enum


class APIMode(Enum):
    """API 模式枚举"""
    IF_ELSE = "if_else"  # if...else 关键词模式
    OLLAMA = "ollama"    # Ollama 模式


class ModeManager:
    """模式管理器类"""
    
    def __init__(self, ollama_config_file: str = "ollama_config.json"):
        """初始化模式管理器
        
        Args:
            ollama_config_file (str): Ollama配置文件路径
        """
        self.ollama_config_file = ollama_config_file
        self.current_mode = APIMode.IF_ELSE  # 默认使用 if...else 模式
        self.ollama_config = self._load_ollama_config()
    
    def _load_ollama_config(self) -> Dict[str, Any]:
        """从只读配置文件加载 Ollama 设置
        
        Returns:
            Dict[str, Any]: Ollama配置字典
        """
        default_config = {
            "base_url": "http://localhost:11434",
            "default_model": "llama2:latest",
            "temperature": 0.8,
            "max_tokens": 2048,
            "timeout": 30,
            "model_mapping": {
                "gpt-3.5-turbo": "llama2:latest",
                "gpt-4": "llama2:13b",
                "gpt-4-turbo": "llama2:70b"
            }
        }
        
        if os.path.exists(self.ollama_config_file):
            try:
                with open(self.ollama_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                print(f"加载 Ollama 配置文件失败，使用默认配置: {e}")
        else:
            print(f"Ollama 配置文件 {self.ollama_config_file} 不存在，使用默认配置")
        
        return default_config
    
    def reload_ollama_config(self) -> None:
        """重新加载 Ollama 配置（只读）"""
        self.ollama_config = self._load_ollama_config()
    
    def get_current_mode(self) -> APIMode:
        """获取当前模式
        
        Returns:
            APIMode: 当前模式
        """
        return self.current_mode
    
    def set_mode(self, mode: APIMode) -> bool:
        """设置当前模式（内存中，不持久化）
        
        Args:
            mode (APIMode): 目标模式
            
        Returns:
            bool: 设置是否成功
        """
        try:
            self.current_mode = mode
            return True
        except Exception as e:
            print(f"设置模式失败: {e}")
            return False
    
    def switch_mode(self) -> APIMode:
        """切换模式（内存中，不持久化）
        
        Returns:
            APIMode: 切换后的模式
        """
        if self.current_mode == APIMode.IF_ELSE:
            self.current_mode = APIMode.OLLAMA
        else:
            self.current_mode = APIMode.IF_ELSE
        
        return self.current_mode
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """获取 Ollama 配置
        
        Returns:
            Dict[str, Any]: Ollama配置副本
        """
        return self.ollama_config.copy()
    
    def update_ollama_config(self, config: Dict[str, Any]) -> bool:
        """更新 Ollama 配置（只读模式，不允许修改）
        
        Args:
            config (Dict[str, Any]): 新配置
            
        Returns:
            bool: 更新是否成功
        """
        print("Ollama 配置为只读模式，无法修改。请直接编辑 ollama_config.json 文件。")
        return False
    
    def get_mode_info(self) -> Dict[str, Any]:
        """获取模式信息
        
        Returns:
            Dict[str, Any]: 模式信息字典
        """
        return {
            'current_mode': self.current_mode.value,
            'available_modes': [mode.value for mode in APIMode],
            'ollama_config': self.ollama_config,
            'mode_descriptions': {
                'if_else': (
                    '基于关键词匹配的 if...else 模式，'
                    '支持预定义响应和 Function Call'
                ),
                'ollama': '使用 Ollama 本地大语言模型的智能对话模式'
            }
        }
    
    def validate_mode_switch(self, target_mode: APIMode) -> Dict[str, Any]:
        """验证模式切换的可行性
        
        Args:
            target_mode (APIMode): 目标模式
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            'can_switch': True,
            'message': '',
            'warnings': []
        }
        
        if target_mode == APIMode.OLLAMA:
            # 检查 Ollama 服务可用性
            from ollama_client import OllamaClient
            
            try:
                ollama_client = OllamaClient(self.ollama_config['base_url'])
                if not ollama_client.is_available():
                    result['can_switch'] = False
                    result['message'] = (
                        f"Ollama 服务不可用，请检查 "
                        f"{self.ollama_config['base_url']} 是否正常运行"
                    )
                else:
                    models = ollama_client.list_models()
                    if not models:
                        result['warnings'].append(
                            "未找到可用的 Ollama 模型，请先下载模型"
                        )
                    elif self.ollama_config['default_model'] not in [
                        m.get('name', '') for m in models
                    ]:
                        result['warnings'].append(
                            f"默认模型 {self.ollama_config['default_model']} 不存在"
                        )
            except Exception as e:
                result['can_switch'] = False
                result['message'] = f"检查 Ollama 服务时出错: {e}"
        
        return result
    
    def get_model_mapping(self) -> Dict[str, str]:
        """获取模型映射关系
        
        Returns:
            Dict[str, str]: 模型映射字典
        """
        if self.current_mode == APIMode.OLLAMA:
            # 使用配置文件中的模型映射
            return self.ollama_config.get('model_mapping', {
                'gpt-3.5-turbo': self.ollama_config['default_model'],
                'gpt-4': self.ollama_config['default_model']
            })
        else:
            # if...else 模式使用固定映射
            return {
                'gpt-3.5-turbo': 'gpt-3.5-turbo',
                'gpt-4': 'gpt-4'
            }