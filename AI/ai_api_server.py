#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 服务器
符合 OpenAI API 规范的聊天完成服务
使用关键词匹配和 if...else 逻辑实现
"""

from flask import Flask, request, jsonify
import json
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
    def __init__(self):
        self.config = ConfigManager()
    
    def extract_keywords(self, message_content):
        """从消息内容中提取关键词"""
        content = message_content.lower()
        
        for keyword in KEYWORDS_DATA.keys():
            if content in keyword:
                return keyword
        return "默认"
    
    def process_chat_completion(self, request_data):
        """处理聊天完成请求"""
        # 验证请求
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {"error": {"message": message, "type": "invalid_request_error"}}, 400
        
        # 根据当前模式处理请求
        current_mode = mode_manager.get_current_mode()
        
        if current_mode == APIMode.OLLAMA:
            return self.process_ollama_completion(request_data)
        else:
            return self.process_ifelse_completion(request_data)
    
    def process_ifelse_completion(self, request_data):
        """处理 if...else 模式的聊天完成请求"""
        # 获取最后一条用户消息
        messages = request_data.get('messages', [])
        last_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_message = msg
                break
        
        if not last_message:
            return {"error": {"message": "No user message found", "type": "invalid_request_error"}}, 400
        
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
        response_data['model'] = request_data.get('model', self.config.model_name)
        
        return response_data, 200
    
    def process_ollama_completion(self, request_data):
        """处理 Ollama 模式的聊天完成请求"""
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
            ollama_model = model_mapping.get(requested_model, ollama_config['default_model'])
            
            # 准备请求参数
            messages = request_data.get('messages', [])
            temperature = request_data.get('temperature', ollama_config.get('temperature', 0.7))
            max_tokens = request_data.get('max_tokens', ollama_config.get('max_tokens', 2048))
            
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
        """处理 function call 结果"""
        # 验证请求
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {"error": {"message": message, "type": "invalid_request_error"}}, 400
        
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
                elif 'weather' in tool_call_id or 'weather' in msg.get('content', '').lower():
                    function_name = 'get_weather'
                elif 'time' in tool_call_id or 'time' in msg.get('content', '').lower():
                    function_name = 'get_current_time'
                elif 'calc' in tool_call_id or 'calculate' in msg.get('content', '').lower():
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
        response_data['model'] = request_data.get('model', self.config.model_name)
        
        return response_data, 200

# 创建 API 服务实例
api_server = AIAPIServer()

@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    """聊天完成 API 端点"""
    try:
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({"error": {"message": "Invalid JSON", "type": "invalid_request_error"}}), 400
        
        # 检查是否包含 tool 消息（function call 结果处理）
        print(f"Received request data: {request_data}")  # Debug print
        messages = request_data.get('messages', [])
        has_tool_message = messages[-1].get('role') == 'tool'
        
        if has_tool_message:
            # 处理 function call 结果
            response_data, status_code = api_server.process_function_result(request_data)
        else:
            # 处理普通聊天完成
            response_data, status_code = api_server.process_chat_completion(request_data)
        
        return jsonify(response_data), status_code
    
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """列出可用模型"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            }
        ]
    })

@app.route('/v1/tools', methods=['GET'])
def list_tools():
    """列出可用工具"""
    return jsonify({
        "object": "list",
        "data": config_manager.get_available_tools()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    current_mode = mode_manager.get_current_mode()
    health_info = {
        "status": "healthy",
        "timestamp": config_manager.get_current_timestamp(),
        "version": config_manager.api_version,
        "current_mode": current_mode.value
    }
    
    # 检查 Ollama 服务状态
    if current_mode == APIMode.OLLAMA:
        health_info["ollama_available"] = ollama_client.is_available()
        if health_info["ollama_available"]:
            health_info["ollama_models"] = len(ollama_client.list_models())
    
    return jsonify(health_info)

@app.route('/v1/mode', methods=['GET'])
def get_mode_info():
    """获取当前模式信息"""
    return jsonify(mode_manager.get_mode_info())

@app.route('/v1/mode/switch', methods=['POST'])
def switch_mode():
    """切换模式"""
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
            
            # 验证模式切换
            validation = mode_manager.validate_mode_switch(target_mode)
            if not validation['can_switch']:
                return jsonify({
                    "error": {
                        "message": validation['message'],
                        "type": "mode_switch_error"
                    }
                }), 400
            
            mode_manager.set_mode(target_mode)
            new_mode = target_mode
        else:
            # 切换模式（自动切换）
            new_mode = mode_manager.switch_mode()
        
        response = {
            "success": True,
            "previous_mode": mode_manager.get_current_mode().value if target_mode_str else (APIMode.OLLAMA if new_mode == APIMode.IF_ELSE else APIMode.IF_ELSE).value,
            "current_mode": new_mode.value,
            "message": f"Successfully switched to {new_mode.value} mode"
        }
        
        # 添加警告信息
        if target_mode_str:
            validation = mode_manager.validate_mode_switch(new_mode)
            if validation.get('warnings'):
                response['warnings'] = validation['warnings']
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Mode switch error: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500

@app.route('/v1/mode/config', methods=['GET'])
def get_mode_config():
    """获取模式配置（只读）"""
    return jsonify({
        "current_mode": mode_manager.get_current_mode().value,
        "ollama_config": mode_manager.get_ollama_config(),
        "model_mapping": mode_manager.get_model_mapping(),
        "note": "Ollama 配置为只读模式，请直接编辑 ollama_config.json 文件进行修改"
    })

@app.route('/v1/mode/config/reload', methods=['POST'])
def reload_ollama_config():
    """重新加载 Ollama 配置"""
    try:
        mode_manager.reload_ollama_config()
        return jsonify({
            "success": True,
            "message": "Ollama 配置已重新加载",
            "ollama_config": mode_manager.get_ollama_config()
        })
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"重新加载配置失败: {str(e)}",
                "type": "internal_server_error"
            }
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": {
            "message": "Not found",
            "type": "not_found_error"
        }
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": {
            "message": "Method not allowed",
            "type": "method_not_allowed_error"
        }
    }), 405

if __name__ == '__main__':
    print("Starting AI API Server with Ollama Compatibility Layer...")
    print("Available endpoints:")
    print("  POST /v1/chat/completions - Chat completions (supports both modes)")
    print("  GET  /v1/models - List models")
    print("  GET  /v1/tools - List tools")
    print("  GET  /health - Health check")
    print("  GET  /v1/mode - Get current mode info")
    print("  POST /v1/mode/switch - Switch between if...else and Ollama modes")
    print("  GET  /v1/mode/config - Get mode configuration (read-only)")
    print("  POST /v1/mode/config/reload - Reload Ollama configuration")
    print(f"\nCurrent mode: {mode_manager.get_current_mode().value}")
    print(f"Ollama config file: ollama_config.json (read-only)")
    print("\nServer running on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)