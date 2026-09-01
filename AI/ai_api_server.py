#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 服务
兼容 OpenAI Chat Completions 接口，并支持 if/else 和 Ollama 两种模式。
"""

import random
import time

from flask import Flask, jsonify, request

from config_manager import ConfigManager
from function_calls import FUNCTION_RESULTS
from keywords_data import KEYWORDS_DATA
from mode_manager import APIMode, ModeManager
from ollama_client import OllamaClient

app = Flask(__name__)
config_manager = ConfigManager()
mode_manager = ModeManager()
ollama_config = mode_manager.get_ollama_config()
ollama_client = OllamaClient(base_url=ollama_config["base_url"])


class AIAPIServer:
    """AI API 服务主类。"""

    def __init__(self):
        self.config = ConfigManager()

    def extract_keywords(self, message_content: str) -> str:
        """从用户消息中提取关键词。"""
        content = (message_content or "").lower()
        for keyword in KEYWORDS_DATA.keys():
            if keyword in content:
                return keyword
        return "默认"

    def process_chat_completion(self, request_data):
        """根据当前模式处理聊天请求。"""
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {
                "error": {
                    "message": message,
                    "type": "invalid_request_error"
                }
            }, 400

        current_mode = mode_manager.get_current_mode()
        if current_mode == APIMode.OLLAMA:
            return self.process_ollama_completion(request_data)
        return self.process_ifelse_completion(request_data)

    def process_ifelse_completion(self, request_data):
        """处理关键词匹配模式。"""
        time.sleep(random.randint(2, 4))
        messages = request_data.get("messages", [])
        last_message = next(
            (msg for msg in reversed(messages) if msg.get("role") == "user"),
            None,
        )

        if not last_message:
            return {
                "error": {
                    "message": "No user message found",
                    "type": "invalid_request_error",
                }
            }, 400

        keyword = self.extract_keywords(last_message.get("content", ""))
        response_data = KEYWORDS_DATA.get(keyword, KEYWORDS_DATA["默认"])["response"].copy()
        response_data["id"] = self.config.generate_chat_id()
        response_data["created"] = self.config.get_current_timestamp()
        response_data["model"] = request_data.get("model", self.config.model_name)
        return response_data, 200

    def process_ollama_completion(self, request_data):
        """处理 Ollama 模式请求。"""
        try:
            current_ollama_config = mode_manager.get_ollama_config()
            if not ollama_client.is_available():
                return {
                    "error": {
                        "message": "Ollama service is not available",
                        "type": "service_unavailable_error",
                    }
                }, 503

            requested_model = request_data.get("model", "gpt-3.5-turbo")
            model_mapping = mode_manager.get_model_mapping()
            ollama_model = model_mapping.get(
                requested_model, current_ollama_config["default_model"]
            )

            messages = request_data.get("messages", [])
            temperature = request_data.get(
                "temperature", current_ollama_config.get("temperature", 0.7)
            )
            max_tokens = request_data.get(
                "max_tokens", current_ollama_config.get("max_tokens", 2048)
            )

            ollama_response = ollama_client.chat_completion(
                model=ollama_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            request_id = self.config.generate_chat_id()
            openai_response = ollama_client.convert_to_openai_format(
                ollama_response, requested_model, request_id
            )
            return openai_response, 200
        except Exception as exc:
            return {
                "error": {
                    "message": f"Ollama processing error: {exc}",
                    "type": "internal_server_error",
                }
            }, 500

    def _resolve_function_name(self, messages):
        """根据 tool 消息及其 tool_call_id 解析函数名。"""
        tool_message = next(
            (msg for msg in reversed(messages) if msg.get("role") == "tool"),
            None,
        )
        if not tool_message:
            return None

        if "name" in tool_message:
            return tool_message["name"]

        tool_call_id = tool_message.get("tool_call_id", "")
        tool_content = tool_message.get("content", "").lower()

        for msg in reversed(messages):
            if msg.get("role") != "assistant":
                continue
            for tool_call in msg.get("tool_calls", []):
                if tool_call.get("id") == tool_call_id:
                    return tool_call.get("function", {}).get("name")

        if "weather" in tool_call_id or "weather" in tool_content:
            return "get_weather"
        if "time" in tool_call_id or "time" in tool_content:
            return "get_current_time"
        if "calc" in tool_call_id or "calculate" in tool_content:
            return "calculate"
        if (
            "yaml" in tool_call_id
            or "script" in tool_call_id
            or "yaml" in tool_content
            or "script" in tool_content
        ):
            return "Write_YAML_script"
        if "slave1" in tool_call_id or "slave1" in tool_content:
            return "start_slave1"
        return None

    def process_function_result(self, request_data):
        """处理 function call 结果。"""
        time.sleep(random.randint(2, 4))
        is_valid, message = self.config.validate_request(request_data)
        if not is_valid:
            return {
                "error": {
                    "message": message,
                    "type": "invalid_request_error",
                }
            }, 400

        messages = request_data.get("messages", [])
        function_name = self._resolve_function_name(messages)
        response_data = FUNCTION_RESULTS.get(
            function_name, FUNCTION_RESULTS["default_function"]
        )["response"].copy()

        response_data["id"] = self.config.generate_chat_id()
        response_data["created"] = self.config.get_current_timestamp()
        response_data["model"] = request_data.get("model", self.config.model_name)
        return response_data, 200


api_server = AIAPIServer()


@app.route("/chat/completions", methods=["POST"])
def chat_completions():
    """聊天完成接口。"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                "error": {
                    "message": "Invalid JSON",
                    "type": "invalid_request_error",
                }
            }), 400

        messages = request_data.get("messages", [])
        has_tool_message = bool(messages) and messages[-1].get("role") == "tool"

        if has_tool_message:
            response_data, status_code = api_server.process_function_result(request_data)
        else:
            response_data, status_code = api_server.process_chat_completion(request_data)

        return jsonify(response_data), status_code
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"Internal server error: {exc}",
                "type": "internal_server_error",
            }
        }), 500


@app.route("/v1/chat/completions", methods=["POST"])
def v1_chat_completions():
    return chat_completions()


@app.route("/v1/models", methods=["GET"])
def list_models():
    try:
        models = ollama_client.list_models()
        openai_models = [
            {
                "id": model.get("name", "unknown"),
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
            }
            for model in models
        ]
        return jsonify({
            "object": "list",
            "data": openai_models,
        })
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"Failed to get Ollama models: {exc}",
                "type": "service_error",
            }
        }), 500


@app.route("/models", methods=["GET"])
def list_models_():
    return list_models()


@app.route("/v1/tools", methods=["GET"])
def list_tools():
    return jsonify({
        "object": "list",
        "data": config_manager.get_available_tools(),
    })


@app.route("/v1/mode", methods=["GET"])
def get_mode_info():
    return jsonify(mode_manager.get_mode_info())


@app.route("/v1/mode/switch", methods=["POST"])
def switch_mode():
    try:
        request_data = request.get_json() or {}
        target_mode_str = request_data.get("mode")

        if target_mode_str:
            try:
                target_mode = APIMode(target_mode_str)
            except ValueError:
                return jsonify({
                    "error": {
                        "message": f"Invalid mode: {target_mode_str}",
                        "type": "invalid_request_error",
                    }
                }), 400

            validation = mode_manager.validate_mode_switch(target_mode)
            if not validation["can_switch"]:
                return jsonify({
                    "error": {
                        "message": validation["message"],
                        "type": "mode_switch_error",
                    }
                }), 400

            success = mode_manager.set_mode(target_mode)
            if not success:
                return jsonify({
                    "error": {
                        "message": "Failed to switch mode",
                        "type": "internal_server_error",
                    }
                }), 500
        else:
            target_mode = mode_manager.switch_mode()

        return jsonify({
            "message": f"Mode switched to {target_mode.value}",
            "current_mode": target_mode.value,
            "mode_info": mode_manager.get_mode_info(),
        })
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"Mode switch error: {exc}",
                "type": "internal_server_error",
            }
        }), 500


@app.route("/v1/mode/config", methods=["GET"])
def get_mode_config():
    return jsonify(mode_manager.get_mode_info())


@app.route("/v1/mode/config/reload", methods=["POST"])
def reload_mode_config():
    try:
        mode_manager.reload_ollama_config()
        return jsonify({
            "message": "Ollama configuration reloaded successfully",
            "config": mode_manager.get_ollama_config(),
        })
    except Exception as exc:
        return jsonify({
            "error": {
                "message": f"Failed to reload config: {exc}",
                "type": "internal_server_error",
            }
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    current_mode = mode_manager.get_current_mode()
    health_status = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "mode": current_mode.value,
        "services": {
            "api_server": "running",
        },
    }

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
    return jsonify({
        "error": {
            "message": "Endpoint not found",
            "type": "not_found_error",
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": {
            "message": "Internal server error",
            "type": "internal_server_error",
        }
    }), 500


if __name__ == "__main__":
    print("AI API 服务启动中...")
    print(f"当前模式: {mode_manager.get_current_mode().value}")
    print("服务地址: http://localhost:5000")
    print("健康检查: http://localhost:5000/health")
    app.run(host="0.0.0.0", port=5000, debug=True)
