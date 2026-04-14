#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理文件
管理API服务的基本配置信息
"""

import time
import uuid
from typing import Dict, List, Any, Tuple


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.api_version = "v1"
        self.model_name = "gpt-3.5-turbo"
        self.max_tokens = 4096
        self.temperature = 0.7
        
    def generate_chat_id(self) -> str:
        """生成聊天完成ID
        
        Returns:
            str: 生成的聊天ID
        """
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"chatcmpl-{unique_id}-{timestamp}"
    
    def get_current_timestamp(self) -> int:
        """获取当前时间戳
        
        Returns:
            int: 当前时间戳
        """
        return int(time.time())
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用的工具列表
        
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定地点的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "城市名称"
                            }
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前时间",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "时区，默认为Asia/Shanghai"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "执行数学计算",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "数学表达式"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]
    
    def validate_request(self, request_data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证请求数据格式
        
        Args:
            request_data (Dict[str, Any]): 请求数据
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        required_fields = ['model', 'messages']
        for field in required_fields:
            if field not in request_data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(request_data['messages'], list):
            return False, "Messages must be a list"
        
        if len(request_data['messages']) == 0:
            return False, "Messages cannot be empty"
        
        return True, "Valid request"