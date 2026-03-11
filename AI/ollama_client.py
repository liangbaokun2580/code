#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 客户端模块
用于与 Ollama API 进行通信
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://192.168.1.7:31143"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def is_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get('models', [])
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], 
                       stream: bool = False, **kwargs) -> Dict[str, Any]:
        """发送聊天完成请求到 Ollama"""
        # 转换消息格式
        ollama_messages = self._convert_messages_to_ollama(messages)
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": stream
        }
        
        # 添加其他参数
        if 'temperature' in kwargs:
            payload['options'] = payload.get('options', {})
            payload['options']['temperature'] = kwargs['temperature']
        
        if 'max_tokens' in kwargs:
            payload['options'] = payload.get('options', {})
            payload['options']['num_predict'] = kwargs['max_tokens']
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()
        
        except Exception as e:
            raise Exception(f"Ollama 请求失败: {e}")
    
    def _convert_messages_to_ollama(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """将 OpenAI 格式的消息转换为 Ollama 格式"""
        ollama_messages = []
        
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')
            
            # Ollama 支持的角色: system, user, assistant
            if role in ['system', 'user', 'assistant']:
                ollama_messages.append({
                    'role': role,
                    'content': content
                })
            elif role == 'tool':
                # 将 tool 消息转换为 user 消息
                ollama_messages.append({
                    'role': 'user',
                    'content': f"Tool result: {content}"
                })
        
        return ollama_messages
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        # 简化处理，返回最后一个完整响应
        last_response = None
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    last_response = data
                except json.JSONDecodeError:
                    continue
        return last_response or {}
    
    def convert_to_openai_format(self, ollama_response: Dict[str, Any], 
                                model: str, request_id: str) -> Dict[str, Any]:
        """将 Ollama 响应转换为 OpenAI 格式"""
        message = ollama_response.get('message', {})
        content = message.get('content', '')
        
        # 计算 token 使用量（简化估算）
        prompt_tokens = ollama_response.get('prompt_eval_count', 0)
        completion_tokens = ollama_response.get('eval_count', 0)
        total_tokens = prompt_tokens + completion_tokens
        
        openai_response = {
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop" if ollama_response.get('done', False) else "length"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        }
        
        return openai_response
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取特定模型信息"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取模型信息失败: {e}")
            return None