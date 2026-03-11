#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 测试客户端
演示如何使用 AI API 服务进行聊天和 function call
"""

import requests
import json
import time

class AIAPIClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer your-api-key-here'  # 可选
        })
    
    def chat_completion(self, messages, model="gpt-3.5-turbo", tools=None):
        """发送聊天完成请求"""
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        if tools:
            payload["tools"] = tools
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def get_models(self):
        """获取可用模型列表"""
        url = f"{self.base_url}/v1/models"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def get_tools(self):
        """获取可用工具列表"""
        url = f"{self.base_url}/v1/tools"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def health_check(self):
        """健康检查"""
        url = f"{self.base_url}/health"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None

def test_basic_chat():
    """测试基本聊天功能"""
    print("\n=== 测试基本聊天功能 ===")
    client = AIAPIClient()
    
    # 测试普通对话
    messages = [
        {"role": "user", "content": "你好，请介绍一下自己"}
    ]
    
    response = client.chat_completion(messages)
    if response:
        print("响应:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print("请求失败")

def test_weather_function_call():
    """测试天气 function call"""
    print("\n=== 测试天气 Function Call ===")
    client = AIAPIClient()
    
    # 第一步：发送天气查询请求
    messages = [
        {"role": "user", "content": "请帮我查询北京的天气情况"}
    ]
    
    response = client.chat_completion(messages)
    if response and 'choices' in response:
        choice = response['choices'][0]
        message = choice['message']
        
        print("第一步 - Function Call 请求:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # 检查是否有 tool_calls
        if 'tool_calls' in message and message['tool_calls']:
            tool_call = message['tool_calls'][0]
            function_name = tool_call['function']['name']
            
            # 模拟执行 function call
            print(f"\n执行 function: {function_name}")
            
            # 第二步：发送 function call 结果
            messages.append(message)  # 添加助手的 tool_calls 消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "name": function_name,
                "content": json.dumps({
                    "location": "北京",
                    "temperature": "25°C",
                    "humidity": "60%",
                    "wind_speed": "5km/h",
                    "condition": "晴朗"
                }, ensure_ascii=False)
            })
            
            # 发送包含 tool 结果的请求
            final_response = client.chat_completion(messages)
            if final_response:
                print("\n第二步 - Function Call 结果处理:")
                print(json.dumps(final_response, indent=2, ensure_ascii=False))

def test_time_function_call():
    """测试时间 function call"""
    print("\n=== 测试时间 Function Call ===")
    client = AIAPIClient()
    
    messages = [
        {"role": "user", "content": "现在几点了？"}
    ]
    
    response = client.chat_completion(messages)
    if response and 'choices' in response:
        choice = response['choices'][0]
        message = choice['message']
        
        print("第一步 - Function Call 请求:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        if 'tool_calls' in message and message['tool_calls']:
            tool_call = message['tool_calls'][0]
            function_name = tool_call['function']['name']
            
            print(f"\n执行 function: {function_name}")
            
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "name": function_name,
                "content": json.dumps({
                    "current_time": "2024年1月15日 14:30:25",
                    "timezone": "Asia/Shanghai"
                }, ensure_ascii=False)
            })
            
            final_response = client.chat_completion(messages)
            if final_response:
                print("\n第二步 - Function Call 结果处理:")
                print(json.dumps(final_response, indent=2, ensure_ascii=False))

def test_calculate_function_call():
    """测试计算 function call"""
    print("\n=== 测试计算 Function Call ===")
    client = AIAPIClient()
    
    messages = [
        {"role": "user", "content": "请帮我计算 2+2 等于多少"}
    ]
    
    response = client.chat_completion(messages)
    if response and 'choices' in response:
        choice = response['choices'][0]
        message = choice['message']
        
        print("第一步 - Function Call 请求:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        if 'tool_calls' in message and message['tool_calls']:
            tool_call = message['tool_calls'][0]
            function_name = tool_call['function']['name']
            
            print(f"\n执行 function: {function_name}")
            
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "name": function_name,
                "content": json.dumps({
                    "expression": "2+2",
                    "result": 4
                }, ensure_ascii=False)
            })
            
            final_response = client.chat_completion(messages)
            if final_response:
                print("\n第二步 - Function Call 结果处理:")
                print(json.dumps(final_response, indent=2, ensure_ascii=False))

def test_api_endpoints():
    """测试其他 API 端点"""
    print("\n=== 测试其他 API 端点 ===")
    client = AIAPIClient()
    
    # 测试健康检查
    print("健康检查:")
    health = client.health_check()
    if health:
        print(json.dumps(health, indent=2, ensure_ascii=False))
    
    # 测试模型列表
    print("\n模型列表:")
    models = client.get_models()
    if models:
        print(json.dumps(models, indent=2, ensure_ascii=False))
    
    # 测试工具列表
    print("\n工具列表:")
    tools = client.get_tools()
    if tools:
        print(json.dumps(tools, indent=2, ensure_ascii=False))

def main():
    """主测试函数"""
    print("AI API 服务测试客户端")
    print("确保 AI API 服务正在运行在 http://localhost:5000")
    
    # 等待用户确认
    input("\n按 Enter 键开始测试...")
    
    try:
        # 运行所有测试
        test_api_endpoints()
        test_basic_chat()
        test_weather_function_call()
        test_time_function_call()
        test_calculate_function_call()
        
        print("\n=== 所有测试完成 ===")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()