#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 服务器
符合 OpenAI API 规范的聊天完成服务
使用关键词匹配和 if...else 逻辑实现
"""

from flask import Flask, request, jsonify
import json
import random
import time
from keywords_data import KEYWORDS_DATA
from function_calls import FUNCTION_RESULTS
from config_manager import ConfigManager
from ollama_client import OllamaClient
from mode_manager import ModeManager, APIMode

app = Flask(__name__)
config_manager = ConfigManager()
mode_manager = ModeManager()
# 使用配置文件中的 base_url 初始化 ollama_client
ollama_config = mode_manager.get_ollama_config()
ollama_client = OllamaClient(base_url=ollama_config['base_url'])


class AIAPIServer:
    """AI API 服务器主类"""
    
    def __init__(self):
        self.config = ConfigManager()
    
    def extract_keywords(self, message_content):
        """从消息内容中提取关键词
        
        Args:
            message_content (str): 消息内容
            
        Returns:
            str: 匹配的关键词或"默认"
        """
        content = message_content.lower()
        
        for keyword in KEYWORDS_DATA.keys():
            if keyword in content:
                return keyword
        return "默认"
    
    def process_chat_completion(self, request_data):
        """处理聊天完成请求
        
        Args:
            request_data (dict): 请求数据
            
        Returns:
            tuple: (响应数据, 状态码)
        """
        # 验证请求
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {
                "error": {
                    "message": message,
                    "type": "invalid_request_error"
                }
            }, 400
        
        # 根据当前模式处理请求
        current_mode = mode_manager.get_current_mode()
        
        if current_mode == APIMode.OLLAMA:
            return self.process_ollama_completion(request_data)
        else:
            return self.process_ifelse_completion(request_data)
    
    def process_ifelse_completion(self, request_data):
        """处理 if...else 模式的聊天完成请求
        
        Args:
            request_data (dict): 请求数据
            
        Returns:
            tuple: (响应数据, 状态码)
        """
        # 获取最后一条用户消息
        time.sleep(random.randint(2,4))
        messages = request_data.get('messages', [])
        last_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_message = msg
                break
        
        if not last_message:
            return {
                "error": {
                    "message": "No user message found",
                    "type": "invalid_request_error"
                }
            }, 400
        
        # 提取关键词
        keyword = self.extract_keywords(last_message.get('content', ''))
        print(f"Extracted keyword: {keyword}")  # Debug print
        
        # 根据关键词获取响应数据
        if keyword in KEYWORDS_DATA:
            response_data = KEYWORDS_DATA[keyword]['response'].copy()
        else:
            response_data = KEYWORDS_DATA['默认']['response'].copy()
        
        # 更新响应数据
        response_data['id'] = self.config.generate_chat_id()
        response_data['created'] = self.config.get_current_timestamp()
        response_data['model'] = request_data.get(
            'model', self.config.model_name
        )
        
        return response_data, 200
    
    def process_ollama_completion(self, request_data):
        """处理 Ollama 模式的聊天完成请求
        
        Args:
            request_data (dict): 请求数据
            
        Returns:
            tuple: (响应数据, 状态码)
        """
        try:
            # 获取 Ollama 配置
            ollama_config = mode_manager.get_ollama_config()
            
            # 检查 Ollama 服务可用性
            if not ollama_client.is_available():
                return {
                    "error": {
                        "message": "Ollama service is not available",
                        "type": "service_unavailable_error"
                    }
                }, 503
            
            # 获取模型名称
            requested_model = request_data.get('model', 'gpt-3.5-turbo')
            model_mapping = mode_manager.get_model_mapping()
            ollama_model = model_mapping.get(
                requested_model, ollama_config['default_model']
            )
            
            # 准备请求参数
            messages = request_data.get('messages', [])
            temperature = request_data.get(
                'temperature', ollama_config.get('temperature', 0.7)
            )
            max_tokens = request_data.get(
                'max_tokens', ollama_config.get('max_tokens', 2048)
            )
            
            # 发送请求到 Ollama
            ollama_response = ollama_client.chat_completion(
                model=ollama_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 转换为 OpenAI 格式
            request_id = self.config.generate_chat_id()
            openai_response = ollama_client.convert_to_openai_format(
                ollama_response, requested_model, request_id
            )
            
            return openai_response, 200
            
        except Exception as e:
            return {
                "error": {
                    "message": f"Ollama processing error: {str(e)}",
                    "type": "internal_server_error"
                }
            }, 500
    
    def process_function_result(self, request_data):
        """处理 function call 结果
        
        Args:
            request_data (dict): 请求数据
            
        Returns:
            tuple: (响应数据, 状态码)
        """
        # 验证请求
        time.sleep(random.randint(2,4))
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {
                "error": {
                    "message": message,
                    "type": "invalid_request_error"
                }
            }, 400
        
        # 查找 tool 消息中的 function_name
        messages = request_data.get('messages', [])
        function_name = None
        
        for msg in reversed(messages):
            if msg.get('role') == 'tool':
                # 从 tool 消息中提取 function_name
                tool_call_id = msg.get('tool_call_id', '')
                # 这里可以根据实际需求解析 function_name
                # 简化处理：从消息内容或其他字段获取
                if 'name' in msg:
                    function_name = msg['name']
                elif ('weather' in tool_call_id or 
                      'weather' in msg.get('content', '').lower()):
                    function_name = 'get_weather'
                elif ('time' in tool_call_id or 
                      'time' in msg.get('content', '').lower()):
                    function_name = 'get_current_time'
                elif ('calc' in tool_call_id or 
                      'calculate' in msg.get('content', '').lower()):
                    function_name = 'calculate'
                break
        
        # 根据 function_name 获取结果
        if function_name and function_name in FUNCTION_RESULTS:
            response_data = FUNCTION_RESULTS[function_name]['response'].copy()
        else:
            response_data = FUNCTION_RESULTS['default_function']['response'].copy()
        
        # 更新响应数据
        response_data['id'] = self.config.generate_chat_id()
        response_data['created'] = self.config.get_current_timestamp()
        response_data['model'] = request_data.get(
            'model', self.config.model_name
        )
        
        return response_data, 200


# 创建 API 服务实例
api_server = AIAPIServer()


@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    """聊天完成 API 端点"""
    try:
        request_data = request.get_json()

        print(request_data['model'])
        
        if not request_data:
            return jsonify({
                "error": {
                    "message": "Invalid JSON",
                    "type": "invalid_request_error"
                }
            }), 400
        
        # 检查是否包含 tool 消息（function call 结果处理）
        # print(f"Received request data: {request_data}")  # Debug print
        messages = request_data.get('messages', [])
        has_tool_message = messages[-1].get('role') == 'tool'
        
        if has_tool_message:
            # 处理 function call 结果
            response_data, status_code = api_server.process_function_result(
                request_data
            )
        else:
            # 处理普通聊天完成
            response_data, status_code = api_server.process_chat_completion(
                request_data
            )
        
        return jsonify(response_data), status_code
    
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500


@app.route('/v1/chat/completions', methods=['POST'])
def v1_chat_completions():
    """v1 版本的聊天完成 API 端点"""
    return chat_completions()


@app.route('/v1/models', methods=['GET'])
def list_models():
    """获取可用模型列表"""
    current_mode = mode_manager.get_current_mode()
    
    try:
        models = ollama_client.list_models()

        openai_models = []
            
        for model in models:
            openai_models.append({
                "id": model.get('name', 'unknown'),
                "object": "model",
                "created": int(time.time()),
                    "owned_by": "ollama"
            })
            
        return jsonify({
            "object": "list",
            "data": openai_models
        })
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Failed to get Ollama models: {str(e)}",
                "type": "service_error"
            }
        }), 500


@app.route('/models', methods=['GET'])
def list_models_():
    """获取可用模型列表"""
    return list_models()


@app.route('/v1/tools', methods=['GET'])
def list_tools():
    """获取可用工具列表"""
    tools = config_manager.get_available_tools()
    return jsonify({
        "object": "list",
        "data": tools
    })


@app.route('/v1/mode', methods=['GET'])
def get_mode_info():
    """获取当前模式信息"""
    mode_info = mode_manager.get_mode_info()
    return jsonify(mode_info)


@app.route('/v1/mode/switch', methods=['POST'])
def switch_mode():
    """切换运行模式"""
    try:
        request_data = request.get_json() or {}
        target_mode_str = request_data.get('mode')
        
        if target_mode_str:
            # 切换到指定模式
            try:
                target_mode = APIMode(target_mode_str)
            except ValueError:
                return jsonify({
                    "error": {
                        "message": f"Invalid mode: {target_mode_str}",
                        "type": "invalid_request_error"
                    }
                }), 400
            
            # 验证模式切换可行性
            validation = mode_manager.validate_mode_switch(target_mode)
            if not validation['can_switch']:
                return jsonify({
                    "error": {
                        "message": validation['message'],
                        "type": "mode_switch_error"
                    }
                }), 400
            
            success = mode_manager.set_mode(target_mode)
            if not success:
                return jsonify({
                    "error": {
                        "message": "Failed to switch mode",
                        "type": "internal_server_error"
                    }
                }), 500
        else:
            # 自动切换模式
            target_mode = mode_manager.switch_mode()
        
        return jsonify({
            "message": f"Mode switched to {target_mode.value}",
            "current_mode": target_mode.value,
            "mode_info": mode_manager.get_mode_info()
        })
    
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Mode switch error: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500


@app.route('/v1/mode/config', methods=['GET'])
def get_mode_config():
    """获取模式配置"""
    return jsonify(mode_manager.get_mode_info())


@app.route('/v1/mode/config/reload', methods=['POST'])
def reload_mode_config():
    """重新加载 Ollama 配置"""
    try:
        mode_manager.reload_ollama_config()
        return jsonify({
            "message": "Ollama configuration reloaded successfully",
            "config": mode_manager.get_ollama_config()
        })
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Failed to reload config: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    current_mode = mode_manager.get_current_mode()
    health_status = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "mode": current_mode.value,
        "services": {
            "api_server": "running"
        }
    }
    
    # 检查 Ollama 服务状态
    if current_mode == APIMode.OLLAMA:
        try:
            ollama_available = ollama_client.is_available()
            health_status["services"]["ollama"] = (
                "running" if ollama_available else "unavailable"
            )
            if not ollama_available:
                health_status["status"] = "degraded"
        except Exception:
            health_status["services"]["ollama"] = "error"
            health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        "error": {
            "message": "Endpoint not found",
            "type": "not_found_error"
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({
        "error": {
            "message": "Internal server error",
            "type": "internal_server_error"
        }
    }), 500


if __name__ == '__main__':
    print("AI API 服务器启动中...")
    print(f"当前模式: {mode_manager.get_current_mode().value}")
    print("服务地址: http://localhost:5000")
    print("API 文档: http://localhost:5000/health")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )