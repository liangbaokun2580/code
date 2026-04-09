#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 兼容层测试客户端
测试模式切换和 Ollama 集成功能
"""

import requests
import json
import time

class OllamaCompatibilityTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def test_mode_info(self):
        """测试获取模式信息"""
        print("\n=== 测试模式信息 ===")
        try:
            response = self.session.get(f"{self.base_url}/v1/mode")
            response.raise_for_status()
            data = response.json()
            print("模式信息:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception as e:
            print(f"获取模式信息失败: {e}")
            return None
    
    def test_mode_switch(self, target_mode=None):
        """测试模式切换"""
        print(f"\n=== 测试模式切换 {'到 ' + target_mode if target_mode else '(自动切换)'} ===")
        try:
            payload = {}
            if target_mode:
                payload['mode'] = target_mode
            
            response = self.session.post(f"{self.base_url}/v1/mode/switch", json=payload)
            response.raise_for_status()
            data = response.json()
            print("切换结果:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception as e:
            print(f"模式切换失败: {e}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    print("错误详情:", json.dumps(error_data, indent=2, ensure_ascii=False))
                except:
                    pass
            return None
    
    def test_mode_config(self):
        """测试获取模式配置"""
        print("\n=== 测试模式配置 ===")
        try:
            response = self.session.get(f"{self.base_url}/v1/mode/config")
            response.raise_for_status()
            data = response.json()
            print("配置信息:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception as e:
            print(f"获取配置失败: {e}")
            return None
    
    def test_mode_config_reload(self):
        """测试 Ollama 配置重新加载"""
        print("\n=== 测试 Ollama 配置重新加载 ===")
        try:
            response = self.session.post(f"{self.base_url}/v1/mode/config/reload")
            response.raise_for_status()
            data = response.json()
            print("配置重新加载响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception as e:
            print(f"配置重新加载失败: {e}")
            return None
    
    def test_health_check(self):
        """测试健康检查"""
        print("\n=== 测试健康检查 ===")
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            print("健康状态:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception as e:
            print(f"健康检查失败: {e}")
            return None
    
    def test_chat_in_ifelse_mode(self):
        """测试 if...else 模式下的聊天"""
        print("\n=== 测试 if...else 模式聊天 ===")
        
        test_messages = [
            "你好，请介绍一下自己",
            "请帮我查询北京的天气",
            "现在几点了？",
            "请计算 10 + 20"
        ]
        
        for message in test_messages:
            print(f"\n发送消息: {message}")
            try:
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "user", "content": message}
                    ]
                }
                
                response = self.session.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                
                choice = data.get('choices', [{}])[0]
                message_data = choice.get('message', {})
                
                if 'tool_calls' in message_data:
                    print("收到 Function Call:")
                    print(json.dumps(message_data['tool_calls'], indent=2, ensure_ascii=False))
                else:
                    print(f"收到回复: {message_data.get('content', '')}")
                
            except Exception as e:
                print(f"聊天请求失败: {e}")
    
    def test_chat_in_ollama_mode(self):
        """测试 Ollama 模式下的聊天"""
        print("\n=== 测试 Ollama 模式聊天 ===")
        
        test_messages = [
            "Hello, can you introduce yourself?",
            "What is the capital of France?",
            "Tell me a short joke"
        ]
        
        for message in test_messages:
            print(f"\n发送消息: {message}")
            try:
                payload = {
                    "model": "llama3.1",
                    "messages": [
                        {"role": "user", "content": message}
                    ]
                }
                
                response = self.session.post(f"{self.base_url}/chat/completions", json=payload)
                
                if response.status_code == 503:
                    print("Ollama 服务不可用")
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2, ensure_ascii=False))
                    break
                
                response.raise_for_status()
                data = response.json()
                
                choice = data.get('choices', [{}])[0]
                message_data = choice.get('message', {})
                content = message_data.get('content', '')
                
                print(f"收到回复: {content[:200]}{'...' if len(content) > 200 else ''}")
                
            except Exception as e:
                print(f"聊天请求失败: {e}")
                if hasattr(e, 'response') and e.response:
                    try:
                        error_data = e.response.json()
                        print("错误详情:", json.dumps(error_data, indent=2, ensure_ascii=False))
                    except:
                        pass
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("Ollama 兼容层综合测试")
        print("=" * 50)
        
        # 1. 健康检查
        self.test_health_check()
        
        # 2. 获取当前模式信息
        mode_info = self.test_mode_info()
        current_mode = mode_info.get('current_mode') if mode_info else 'unknown'
        
        # 3. 测试配置获取
        self.test_mode_config()
        
        # 4. 测试 if...else 模式
        if current_mode != 'if_else':
            print("\n切换到 if...else 模式进行测试")
            self.test_mode_switch('if_else')
        
        self.test_chat_in_ifelse_mode()
        
        # 5. 测试 Ollama 模式
        print("\n切换到 Ollama 模式进行测试")
        switch_result = self.test_mode_switch('ollama')
        
        if switch_result and switch_result.get('success'):
            self.test_chat_in_ollama_mode()
        else:
            print("无法切换到 Ollama 模式，跳过 Ollama 测试")
        
        # 6. 测试配置重新加载
        print("\n测试配置重新加载")
        self.test_mode_config_reload()
        
        # 7. 测试自动模式切换
        print("\n测试自动模式切换")
        self.test_mode_switch()
        
        print("\n=== 综合测试完成 ===")

def main():
    """主函数"""
    print("Ollama 兼容层测试工具")
    print("确保 AI API 服务正在运行在 http://localhost:5000")
    
    # 等待用户确认
    input("\n按 Enter 键开始测试...")
    
    tester = OllamaCompatibilityTester()
    
    try:
        tester.run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()