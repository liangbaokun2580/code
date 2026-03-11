from openai import OpenAI
import re
import json
import logging
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
import asyncio
import aiohttp

from config import Config

class AIService:
    """AI服务类，处理与OpenAI API的交互"""
    
    def __init__(self):
        self.config = Config()
        self.use_local = self.config.USE_LOCAL_MODEL
        self.max_tokens = self.config.OPENAI_MAX_TOKENS
        self.temperature = self.config.OPENAI_TEMPERATURE
        self.top_p = self.config.OPENAI_TOP_P
        self.presence_penalty = self.config.OPENAI_PRESENCE_PENALTY
        self.frequency_penalty = self.config.OPENAI_FREQUENCY_PENALTY
        self.logger = logging.getLogger(__name__)
        
        if self.use_local:
            # 使用本地模型
            self.api_key = "ollama"  # Ollama不需要真实API key
            self.api_base = self.config.LOCAL_MODEL_BASE_URL + "/v1"
            self.model = self.config.LOCAL_MODEL_NAME
            self.logger.info(f"使用本地模型: {self.model} at {self.config.LOCAL_MODEL_BASE_URL}")
        else:
            # 使用OpenAI API
            self.api_key = self.config.OPENAI_API_KEY
            self.api_base = self.config.OPENAI_API_BASE + "/v1"
            self.model = self.config.OPENAI_MODEL
            self.logger.info(f"使用OpenAI模型: {self.model}")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base if self.api_base else None
        )
        
    def get_available_models(self):
        """获取可用的模型列表"""
        try:
            if self.use_local:
                # 对于本地模型，可能需要根据实际情况调整
                return {
                    "success": True,
                    "data": [
                        {"id": self.model, "name": self.model, "is_local": True}
                    ]
                }
            else:
                # 获取OpenAI API的模型列表
                models = self.client.models.list()
                model_list = []
                for model in models.data:
                    model_list.append({
                        "id": model.id,
                        "name": model.id,
                        "is_local": False
                    })
                return {
                    "success": True,
                    "data": model_list
                }
        except Exception as e:
            self.logger.error(f"获取模型列表失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _prepare_messages(self, messages: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        """准备消息格式"""
        formatted_messages = []
        
        for msg in messages:
            formatted_msg = {
                'role': msg['role'],
                'content': msg['content']
            }
            
            # 处理工具调用
            if 'tool_calls' in msg and msg['tool_calls']:
                try:
                    tool_calls = json.loads(msg['tool_calls']) if isinstance(msg['tool_calls'], str) else msg['tool_calls']
                    formatted_msg['tool_calls'] = tool_calls
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # 处理工具调用结果
            if msg['role'] == 'tool' and 'tool_call_id' in msg:
                formatted_msg['tool_call_id'] = msg['tool_call_id']
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages

    def _has_chinese(self, text: str) -> bool:
        if not text:
            return False
        return re.search(r'[\u4e00-\u9fff]', text) is not None

    def _translate_to_chinese(self, text: str) -> str:
        """Translate text to Chinese using the current model."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': '你是翻译器，只输出中文译文，不要解释。'},
                    {'role': 'user', 'content': text}
                ],
                max_tokens=min(self.max_tokens, 1024),
                temperature=0
            )
            translated = response.choices[0].message.content or ''
            return translated.strip() if translated else text
        except Exception:
            return text

    def ensure_chinese(self, text: str) -> str:
        if self._has_chinese(text):
            return text
        return self._translate_to_chinese(text)
    
    def _get_available_tools(self, mode: str) -> List[Dict[str, Any]]:
        """获取可用的工具定义"""
        if mode == 'chat':
            return [
            # 获取设备信息
            {
                "type": "function",
                "function": {
                    "name": "get_device_info",
                    "description": "获取指定设备的详细信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "设备ID"
                            },
                            "ip_address": {
                                "type": "string",
                                "description": "设备IP地址"
                            }
                        },
                        "required": []
                    }
                }
            },
            # 获取网络状态
            {
                "type": "function",
                "function": {
                    "name": "get_network_status",
                    "description": "获取整体网络状态和统计信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_details": {
                                "type": "boolean",
                                "description": "是否包含详细信息",
                                "default": False
                            }
                        },
                        "required": []
                    }
                }
            },
            # 连接性测试
            {
                "type": "function",
                "function": {
                    "name": "connectivity_test",
                    "description": "测试网络连接性",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_ip": {
                                "type": "string",
                                "description": "目标IP地址"
                            },
                            "test_type": {
                                "type": "string",
                                "enum": ["ping", "traceroute", "telnet", "ssh"],
                                "description": "测试类型"
                            },
                            "port": {
                                "type": "integer",
                                "description": "端口号（用于telnet/ssh测试）"
                            },
                            "count": {
                                "type": "integer",
                                "description": "ping测试次数",
                                "default": 4
                            }
                        },
                        "required": ["target_ip", "test_type"]
                    }
                }
            },
            # 神州数码设备配置获取
            {
                "type": "function",
                "function": {
                    "name": "dcn_get_config",
                    "description": "获取神州数码设备配置信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "config_type": {
                                "type": "string",
                                "enum": ["running", "startup", "interface", "routing", "ospf", "bgp", "rip", "lldp"],
                                "description": "配置类型"
                            },
                            
                        },
                        "required": ["device_ip", "config_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_code",
                    "description": "执行Python代码",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要执行的Python代码"
                            },
                            "description": {
                                "type": "string",
                                "description": "代码功能描述"
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_network_info",
                    "description": "获取本地网络信息",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trace_route",
                    "description": "执行路由跟踪",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "目标IP地址或域名"
                            },
                            "max_hops": {
                                "type": "integer",
                                "description": "最大跳数，默认30"
                            }
                        },
                        "required": ["target"]
                    }
                }
            }
        ]
        tools = [
            # # 网络扫描工具
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "network_scan",
            #         "description": "扫描网络中的设备",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "scan_range": {
            #                     "type": "string",
            #                     "description": "要扫描的网络范围，如 192.168.1.0/24"
            #                 },
            #                 "scan_type": {
            #                     "type": "string",
            #                     "enum": ["ping", "snmp", "full"],
            #                     "description": "扫描类型：ping（快速扫描）、snmp（SNMP扫描）、full（完整扫描）"
            #                 }
            #             },
            #             "required": ["scan_range"]
            #         }
            #     }
            # },
            # 获取设备信息
            {
                "type": "function",
                "function": {
                    "name": "get_device_info",
                    "description": "获取指定设备的详细信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "设备ID"
                            },
                            "ip_address": {
                                "type": "string",
                                "description": "设备IP地址"
                            }
                        },
                        "required": []
                    }
                }
            },
            # 获取网络状态
            {
                "type": "function",
                "function": {
                    "name": "get_network_status",
                    "description": "获取整体网络状态和统计信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_details": {
                                "type": "boolean",
                                "description": "是否包含详细信息",
                                "default": False
                            }
                        },
                        "required": []
                    }
                }
            },
            # 连接性测试
            {
                "type": "function",
                "function": {
                    "name": "connectivity_test",
                    "description": "测试网络连接性",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_ip": {
                                "type": "string",
                                "description": "目标IP地址"
                            },
                            "test_type": {
                                "type": "string",
                                "enum": ["ping", "traceroute", "telnet", "ssh"],
                                "description": "测试类型"
                            },
                            "port": {
                                "type": "integer",
                                "description": "端口号（用于telnet/ssh测试）"
                            },
                            "count": {
                                "type": "integer",
                                "description": "ping测试次数",
                                "default": 4
                            }
                        },
                        "required": ["target_ip", "test_type"]
                    }
                }
            },
            # # 华为设备配置获取
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "huawei_get_config",
            #         "description": "获取华为设备配置信息",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["running", "startup", "interface", "routing", "ospf", "bgp", "rip", "lldp"],
            #                     "description": "配置类型"
            #                 },
                            
            #             },
            #             "required": ["device_ip", "config_type"]
            #         }
            #     }
            # },
            # # 华为设备配置修改
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "huawei_modify_config",
            #         "description": "修改华为设备配置",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["ospf", "bgp", "rip", "static_route", "interface", "lldp", "vlan"],
            #                     "description": "配置类型"
            #                 },
            #                 "commands": {
            #                     "type": "array",
            #                     "items": {"type": "string"},
            #                     "description": "要执行的配置命令列表"
            #                 },
            #                 "save_config": {
            #                     "type": "boolean",
            #                     "description": "是否保存配置",
            #                     "default": True
            #                 }
            #             },
            #             "required": ["device_ip", "config_type", "commands"]
            #         }
            #     }
            # },
            # # 思科设备配置获取
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "cisco_get_config",
            #         "description": "获取思科设备配置信息",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["running", "startup", "interface", "routing", "ospf", "bgp", "rip", "cdp"],
            #                     "description": "配置类型"
            #                 },
                            
            #             },
            #             "required": ["device_ip", "config_type"]
            #         }
            #     }
            # },
            # # 思科设备配置修改
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "cisco_modify_config",
            #         "description": "修改思科设备配置",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["ospf", "bgp", "rip", "static_route", "interface", "cdp", "vlan"],
            #                     "description": "配置类型"
            #                 },
            #                 "commands": {
            #                     "type": "array",
            #                     "items": {"type": "string"},
            #                     "description": "要执行的配置命令列表"
            #                 },
            #                 "save_config": {
            #                     "type": "boolean",
            #                     "description": "是否保存配置",
            #                     "default": True
            #                 }
            #             },
            #             "required": ["device_ip", "config_type", "commands"]
            #         }
            #     }
            # },
            # # 新华三设备配置获取
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "h3c_get_config",
            #         "description": "获取新华三设备配置信息",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["current", "saved", "interface", "routing", "ospf", "bgp", "rip", "lldp"],
            #                     "description": "配置类型"
            #                 },
                            
            #             },
            #             "required": ["device_ip", "config_type"]
            #         }
            #     }
            # },
            # # 新华三设备配置修改
            # {
            #     "type": "function",
            #     "function": {
            #         "name": "h3c_modify_config",
            #         "description": "修改新华三设备配置",
            #         "parameters": {
            #             "type": "object",
            #             "properties": {
            #                 "device_ip": {
            #                     "type": "string",
            #                     "description": "设备IP地址"
            #                 },
            #                 "config_type": {
            #                     "type": "string",
            #                     "enum": ["ospf", "bgp", "rip", "static_route", "interface", "lldp", "vlan"],
            #                     "description": "配置类型"
            #                 },
            #                 "commands": {
            #                     "type": "array",
            #                     "items": {"type": "string"},
            #                     "description": "要执行的配置命令列表"
            #                 },
            #                 "save_config": {
            #                     "type": "boolean",
            #                     "description": "是否保存配置",
            #                     "default": True
            #                 }
            #             },
            #             "required": ["device_ip", "config_type", "commands"]
            #         }
            #     }
            # },
            # 神州数码设备配置获取
            {
                "type": "function",
                "function": {
                    "name": "dcn_get_config",
                    "description": "获取神州数码设备配置信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "config_type": {
                                "type": "string",
                                "enum": ["running", "startup", "interface", "routing", "ospf", "bgp", "rip", "lldp"],
                                "description": "配置类型"
                            },
                            
                        },
                        "required": ["device_ip", "config_type"]
                    }
                }
            },
            # 神州数码设备配置修改
            {
                "type": "function",
                "function": {
                    "name": "dcn_modify_config",
                    "description": "修改神州数码设备配置",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "config_type": {
                                "type": "string",
                                "enum": ["ospf", "bgp", "rip", "static_route", "interface", "lldp", "vlan"],
                                "description": "配置类型"
                            },
                            "commands": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要执行的配置命令列表"
                            },
                            "save_config": {
                                "type": "boolean",
                                "description": "是否保存配置",
                                "default": True
                            }
                        },
                        "required": ["device_ip", "config_type", "commands"]
                    }
                }
            },
            # 设备重启
            {
                "type": "function",
                "function": {
                    "name": "device_reboot",
                    "description": "重启网络设备",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "device_brand": {
                                "type": "string",
                                "enum": ["huawei", "cisco", "h3c", "dcn"],
                                "description": "设备品牌"
                            },
                            "force_reboot": {
                                "type": "boolean",
                                "description": "是否强制重启",
                                "default": False
                            },
                            "delay_seconds": {
                                "type": "integer",
                                "description": "延迟重启时间（秒）",
                                "default": 0
                            }
                        },
                        "required": ["device_ip", "device_brand"]
                    }
                }
            },
            # 添加设备
            {
                "type": "function",
                "function": {
                    "name": "add_device",
                    "description": "添加新的网络设备到管理系统",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "device_name": {
                                "type": "string",
                                "description": "设备名称"
                            },
                            "device_brand": {
                                "type": "string",
                                "enum": ["huawei", "cisco", "h3c", "dcn"],
                                "description": "设备品牌"
                            },
                            "device_type": {
                                "type": "string",
                                "enum": ["router", "switch", "firewall", "ap", "ac"],
                                "description": "设备类型"
                            },
                            "snmp_community": {
                                "type": "string",
                                "description": "SNMP团体字符串",
                                "default": "public"
                            },
                            "ssh_username": {
                                "type": "string",
                                "description": "SSH用户名"
                            },
                            "ssh_password": {
                                "type": "string",
                                "description": "SSH密码"
                            }
                        },
                        "required": ["device_ip", "device_name", "device_brand", "device_type"]
                    }
                }
            },
            # 删除设备
            {
                "type": "function",
                "function": {
                    "name": "remove_device",
                    "description": "从管理系统中删除网络设备",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "设备ID"
                            },
                            "device_ip": {
                                "type": "string",
                                "description": "设备IP地址"
                            },
                            "force_remove": {
                                "type": "boolean",
                                "description": "是否强制删除",
                                "default": False
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_topology",
                    "description": "保存网络拓扑数据",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topology_data": {
                                "type": "object",
                                "description": "拓扑数据，包含节点和连接信息"
                            },
                            "name": {
                                "type": "string",
                                "description": "拓扑名称"
                            },
                            "description": {
                                "type": "string",
                                "description": "拓扑描述"
                            }
                        },
                        "required": ["topology_data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_code",
                    "description": "执行Python代码",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要执行的Python代码"
                            },
                            "description": {
                                "type": "string",
                                "description": "代码功能描述"
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_network_info",
                    "description": "获取本地网络信息",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trace_route",
                    "description": "执行路由跟踪",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "目标IP地址或域名"
                            },
                            "max_hops": {
                                "type": "integer",
                                "description": "最大跳数，默认30"
                            }
                        },
                        "required": ["target"]
                    }
                }
            }
        ]
        
        return tools
    
    def chat_completion(self, messages: List[Dict[str, Any]], 
                       use_tools: bool = True, 
                       stream: bool = False,
                       model = None,
                       mode = 'chat',
                       force_chinese_retry: bool = True) -> Dict[str, Any]:
        """发送聊天完成请求"""
        try:
            # Local Ollama models may not support tools
            if self.use_local:
                use_tools = False

            formatted_messages = self._prepare_messages(messages, mode)
            
            # 构建请求参数
            request_params = {
                'model': self.model if model is None else model,
                'messages': formatted_messages,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'presence_penalty': self.presence_penalty,
                'frequency_penalty': self.frequency_penalty,
                'stream': stream
            }
            
            # 添加工具定义
            if use_tools:
                tools = self._get_available_tools(mode)
                if tools:
                    request_params['tools'] = tools
                    request_params['tool_choice'] = 'auto'
            
            # 发送请求
            if stream:
                return self._stream_chat_completion(request_params)
            else:
                response = self.client.chat.completions.create(**request_params)
                result = self._process_response(response)

                # If the reply has no CJK characters, retry once with a hard Chinese instruction
                if force_chinese_retry:
                    content = (result.get('response') or {}).get('content', '') or ''
                    if content and not self._has_chinese(content):
                        # Translate instead of retrying to avoid repeated English
                        translated = self.ensure_chinese(content)
                        result['response']['content'] = translated

                return result
                
        except Exception as e:
            self.logger.error(f"AI聊天请求失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    def _stream_chat_completion(self, request_params: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """流式聊天完成"""
        try:
            response_stream = self.client.chat.completions.create(**request_params)
            
            for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    chunk_data = {
                        'success': True,
                        'chunk': True,
                        'content': getattr(delta, 'content', '') or '',
                        'role': getattr(delta, 'role', '') or '',
                        'finish_reason': chunk.choices[0].finish_reason
                    }
                    
                    # 处理工具调用
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        chunk_data['tool_calls'] = delta.tool_calls
                    
                    yield chunk_data
                    
        except Exception as e:
            self.logger.error(f"流式聊天请求失败: {e}")
            yield {
                'success': False,
                'error': str(e),
                'chunk': True
            }
    
    def _process_response(self, response) -> Dict[str, Any]:
        """处理AI响应"""
        try:
            choice = response.choices[0]
            message = choice.message
            
            result = {
                'success': True,
                'response': {
                    'role': message.role,
                    'content': message.content or '',
                    'finish_reason': choice.finish_reason
                },
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'model': response.model,
                'created': response.created
            }
            
            # 处理工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                result['response']['tool_calls'] = []
                for tool_call in message.tool_calls:
                    result['response']['tool_calls'].append({
                        'id': tool_call.id,
                        'type': tool_call.type,
                        'function': {
                            'name': tool_call.function.name,
                            'arguments': tool_call.function.arguments
                        }
                    })
            
            return result
            
        except Exception as e:
            self.logger.error(f"处理AI响应失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    def _generate_topology_text_view(self, topology_data: Dict[str, Any]) -> str:
        """生成网络拓扑的文本视图"""
        try:
            devices = topology_data.get('devices', [])
            connections = topology_data.get('connections', [])
            
            text_lines = []
            text_lines.append("=== 网络拓扑文本视图 ===")
            text_lines.append("")
            
            # 设备列表
            text_lines.append("📱 设备列表:")
            if not devices:
                text_lines.append("  暂无设备")
            else:
                for i, device in enumerate(devices, 1):
                    name = device.get('name', device.get('hostname', 'Unknown'))
                    ip = device.get('ip', 'N/A')
                    mac = device.get('mac', 'N/A')
                    device_type = device.get('type', device.get('device_type', 'unknown'))
                    status = device.get('status', 'unknown')
                    
                    status_icon = "🟢" if status == 'online' else "🔴" if status == 'offline' else "🟡"
                    
                    text_lines.append(f"  {i}. {status_icon} {name}")
                    text_lines.append(f"     IP: {ip}")
                    text_lines.append(f"     MAC: {mac}")
                    text_lines.append(f"     类型: {device_type}")
                    
                    # 网络接口信息
                    interfaces = device.get('interfaces', [])
                    if interfaces:
                        text_lines.append(f"     接口:")
                        for interface in interfaces:
                            iface_name = interface.get('name', 'N/A')
                            iface_ip = interface.get('ip', 'N/A')
                            text_lines.append(f"       - {iface_name}: {iface_ip}")
                    text_lines.append("")
            
            # 连接关系
            text_lines.append("🔗 连接关系:")
            if not connections:
                text_lines.append("  暂无连接")
            else:
                for i, conn in enumerate(connections, 1):
                    source = conn.get('source', 'Unknown')
                    target = conn.get('target', 'Unknown')
                    conn_type = conn.get('type', 'unknown')
                    status = conn.get('status', 'unknown')
                    bandwidth = conn.get('bandwidth', 'N/A')
                    
                    status_icon = "🟢" if status == 'active' else "🔴" if status == 'inactive' else "🟡"
                    
                    text_lines.append(f"  {i}. {status_icon} {source} ↔ {target}")
                    text_lines.append(f"     类型: {conn_type}")
                    text_lines.append(f"     带宽: {bandwidth}")
                    text_lines.append("")
            
            # 网络统计
            text_lines.append("📊 网络统计:")
            total_devices = len(devices)
            online_devices = sum(1 for d in devices if d.get('status') == 'online')
            offline_devices = total_devices - online_devices
            total_connections = len(connections)
            active_connections = sum(1 for c in connections if c.get('status') == 'active')
            
            text_lines.append(f"  设备总数: {total_devices}")
            text_lines.append(f"  在线设备: {online_devices}")
            text_lines.append(f"  离线设备: {offline_devices}")
            text_lines.append(f"  连接总数: {total_connections}")
            text_lines.append(f"  活跃连接: {active_connections}")
            
            # 设备类型统计
            device_types = {}
            for device in devices:
                device_type = device.get('type', device.get('device_type', 'unknown'))
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            if device_types:
                text_lines.append("")
                text_lines.append("📋 设备类型分布:")
                for device_type, count in device_types.items():
                    text_lines.append(f"  {device_type}: {count}")
            
            return "\n".join(text_lines)
            
        except Exception as e:
            return f"生成拓扑文本视图失败: {str(e)}"
    
    def execute_tool_call(self, tool_call: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            function_name = tool_call['function']['name']
            arguments = json.loads(tool_call['function']['arguments'])
            
            self.logger.info(f"执行工具调用: {function_name}, 参数: {arguments}")
            
            # 导入必要的服务
            from services.network_service import NetworkService
            from api.topology import topology_bp
            from api.develop import develop_bp
            
            network_service = NetworkService()
            
            if function_name == 'network_scan':
                scan_range = arguments.get('scan_range', '192.168.1.0/24')
                scan_type = arguments.get('scan_type', 'ping')
                
                result = network_service.scan_network(
                    scan_range=scan_range,
                    scan_type=scan_type,
                    user_id=user_id
                )
                
                return {
                    'success': True,
                    'result': result,
                    'message': f'网络扫描完成，发现 {len(result.get("devices", []))} 个设备'
                }
            
            elif function_name == 'get_device_info':
                device_id = arguments.get('device_id')
                ip_address = arguments.get('ip_address')
                
                # 这里需要从数据库查询设备信息
                from models import NetworkDevice
                
                if device_id:
                    device = NetworkDevice.query.filter_by(
                        device_id=device_id,
                        user_id=user_id
                    ).first()
                elif ip_address:
                    device = NetworkDevice.query.filter_by(
                        ip_address=ip_address,
                        user_id=user_id
                    ).first()
                else:
                    return {
                        'success': False,
                        'error': '需要提供设备ID或IP地址'
                    }
                
                if device:
                    return {
                        'success': True,
                        'result': device.to_dict(),
                        'message': f'获取设备 {device.hostname or device.ip_address} 信息成功'
                    }
                else:
                    return {
                        'success': False,
                        'error': '设备不存在'
                    }
            
            elif function_name == 'save_topology':
                topology_data = arguments.get('topology_data', {})
                name = arguments.get('name', '默认拓扑')
                description = arguments.get('description', '')
                
                # 这里需要保存拓扑数据
                from models import TopologyData, db
                
                topology = TopologyData(
                    user_id=user_id,
                    name=name,
                    description=description,
                    topology_data=json.dumps(topology_data),
                    mode='view'
                )
                
                db.session.add(topology)
                db.session.commit()
                
                return {
                    'success': True,
                    'result': topology.to_dict(),
                    'message': f'拓扑 "{name}" 保存成功'
                }
            
            elif function_name == 'execute_code':
                code = arguments.get('code', '')
                description = arguments.get('description', '')
                
                # 执行代码
                import subprocess
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                    temp_file.write(code)
                    temp_file_path = temp_file.name
                
                try:
                    result = subprocess.run(
                        ['python', temp_file_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    os.unlink(temp_file_path)
                    
                    return {
                        'success': True,
                        'result': {
                            'output': result.stdout,
                            'error': result.stderr,
                            'return_code': result.returncode
                        },
                        'message': '代码执行完成'
                    }
                    
                except subprocess.TimeoutExpired:
                    os.unlink(temp_file_path)
                    return {
                        'success': False,
                        'error': '代码执行超时（30秒）'
                    }
            
            elif function_name == 'get_network_info':
                # 获取本地网络信息
                local_info = network_service.get_local_network_info()
                
                # 获取拓扑页面的文本视图数据
                try:
                    from .topology_service import TopologyService
                    topology_service = TopologyService()
                    topology_data = topology_service.get_topology_data()
                    
                    # 生成拓扑文本视图
                    topology_text = self._generate_topology_text_view(topology_data)
                    
                    result = {
                        'local_network_info': local_info,
                        'topology_text_view': topology_text,
                        'topology_data': topology_data
                    }
                    
                    return {
                        'success': True,
                        'result': result,
                        'message': '获取网络信息和拓扑数据成功'
                    }
                except Exception as e:
                    # 如果拓扑数据获取失败，只返回本地网络信息
                    return {
                        'success': True,
                        'result': {
                            'local_network_info': local_info,
                            'topology_text_view': f'拓扑数据获取失败: {str(e)}',
                            'topology_data': None
                        },
                        'message': '获取本地网络信息成功，但拓扑数据获取失败'
                    }
            
            elif function_name == 'trace_route':
                target = arguments.get('target')
                max_hops = arguments.get('max_hops', 30)
                
                result = network_service.trace_route(target, max_hops)
                return {
                    'success': True,
                    'result': result,
                    'message': f'路由跟踪到 {target} 完成'
                }
            
            # 新增的网络管理工具
            elif function_name == 'get_network_status':
                include_details = arguments.get('include_details', False)
                result = network_service.get_network_status(include_details)
                return {
                    'success': True,
                    'result': result,
                    'message': '网络状态获取成功'
                }
            
            elif function_name == 'connectivity_test':
                target_ip = arguments.get('target_ip')
                test_type = arguments.get('test_type')
                port = arguments.get('port')
                count = arguments.get('count', 4)
                
                result = network_service.connectivity_test(target_ip, test_type, port, count)
                return {
                    'success': True,
                    'result': result,
                    'message': f'{test_type}连接测试完成'
                }
            
            # 华为设备工具
            elif function_name == 'huawei_get_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                
                from services.device_managers.huawei_manager import HuaweiDeviceManager
                manager = HuaweiDeviceManager()
                result = manager.get_config(device_ip, config_type)
                return {
                    'success': True,
                    'result': result,
                    'message': f'华为设备{config_type}配置获取成功'
                }
            
            elif function_name == 'huawei_modify_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                commands = arguments.get('commands')
                save_config = arguments.get('save_config', True)
                
                from services.device_managers.huawei_manager import HuaweiDeviceManager
                manager = HuaweiDeviceManager()
                result = manager.modify_config(device_ip, config_type, commands, save_config)
                return {
                    'success': True,
                    'result': result,
                    'message': f'华为设备{config_type}配置修改成功'
                }
            
            # 思科设备工具
            elif function_name == 'cisco_get_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                
                from services.device_managers.cisco_manager import CiscoDeviceManager
                manager = CiscoDeviceManager()
                result = manager.get_config(device_ip, config_type)
                return {
                    'success': True,
                    'result': result,
                    'message': f'思科设备{config_type}配置获取成功'
                }
            
            elif function_name == 'cisco_modify_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                commands = arguments.get('commands')
                save_config = arguments.get('save_config', True)
                
                from services.device_managers.cisco_manager import CiscoDeviceManager
                manager = CiscoDeviceManager()
                result = manager.modify_config(device_ip, config_type, commands, save_config)
                return {
                    'success': True,
                    'result': result,
                    'message': f'思科设备{config_type}配置修改成功'
                }
            
            # 新华三设备工具
            elif function_name == 'h3c_get_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                
                from services.device_managers.h3c_manager import H3CDeviceManager
                manager = H3CDeviceManager()
                result = manager.get_config(device_ip, config_type)
                return {
                    'success': True,
                    'result': result,
                    'message': f'新华三设备{config_type}配置获取成功'
                }
            
            elif function_name == 'h3c_modify_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                commands = arguments.get('commands')
                save_config = arguments.get('save_config', True)
                
                from services.device_managers.h3c_manager import H3CDeviceManager
                manager = H3CDeviceManager()
                result = manager.modify_config(device_ip, config_type, commands, save_config)
                return {
                    'success': True,
                    'result': result,
                    'message': f'新华三设备{config_type}配置修改成功'
                }
            
            # 神州数码设备工具
            elif function_name == 'dcn_get_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                
                from services.device_managers.dcn_manager import DCNDeviceManager
                manager = DCNDeviceManager()
                result = manager.get_config(device_ip, config_type)
                return {
                    'success': True,
                    'result': result,
                    'message': f'神州数码设备{config_type}配置获取成功'
                }
            
            elif function_name == 'dcn_modify_config':
                device_ip = arguments.get('device_ip')
                config_type = arguments.get('config_type')
                commands = arguments.get('commands')
                save_config = arguments.get('save_config', True)
                
                from services.device_managers.dcn_manager import DCNDeviceManager
                manager = DCNDeviceManager()
                result = manager.modify_config(device_ip, config_type, commands, save_config)
                return {
                    'success': True,
                    'result': result,
                    'message': f'神州数码设备{config_type}配置修改成功'
                }
            
            # 设备重启
            elif function_name == 'device_reboot':
                device_ip = arguments.get('device_ip')
                device_brand = arguments.get('device_brand')
                force_reboot = arguments.get('force_reboot', False)
                delay_seconds = arguments.get('delay_seconds', 0)
                
                # 验证IP地址格式
                if not device_ip:
                    return {
                        'success': False,
                        'error': '设备IP地址不能为空'
                    }
                
                # 检查是否包含分隔符（多个IP地址）
                if '|' in device_ip:
                    return {
                        'success': False,
                        'error': '请选择单个IP地址进行重启操作，当前传入的是多个IP地址'
                    }
                
                # 验证IP地址格式
                import ipaddress
                try:
                    ipaddress.ip_address(device_ip.strip())
                except ValueError:
                    return {
                        'success': False,
                        'error': f'无效的IP地址格式: {device_ip}'
                    }
                
                # 根据品牌选择对应的管理器
                if device_brand == 'huawei':
                    from services.device_managers.huawei_manager import HuaweiDeviceManager
                    manager = HuaweiDeviceManager()
                elif device_brand == 'cisco':
                    from services.device_managers.cisco_manager import CiscoDeviceManager
                    manager = CiscoDeviceManager()
                elif device_brand == 'h3c':
                    from services.device_managers.h3c_manager import H3CDeviceManager
                    manager = H3CDeviceManager()
                elif device_brand == 'dcn':
                    from services.device_managers.dcn_manager import DCNDeviceManager
                    manager = DCNDeviceManager()
                else:
                    return {
                        'success': False,
                        'error': f'不支持的设备品牌: {device_brand}'
                    }
                
                result = manager.reboot_device(device_ip, force_reboot, delay_seconds)
                return {
                    'success': True,
                    'result': result,
                    'message': f'{device_brand}设备重启命令已发送'
                }
            
            # 添加设备
            elif function_name == 'add_device':
                device_ip = arguments.get('device_ip')
                device_name = arguments.get('device_name')
                device_brand = arguments.get('device_brand')
                device_type = arguments.get('device_type')
                snmp_community = arguments.get('snmp_community', 'public')
                ssh_username = arguments.get('ssh_username')
                ssh_password = arguments.get('ssh_password')
                
                from models import NetworkDevice, db
                
                # 检查设备是否已存在
                existing_device = NetworkDevice.query.filter_by(
                    ip_address=device_ip,
                    user_id=user_id
                ).first()
                
                if existing_device:
                    return {
                        'success': False,
                        'error': f'设备 {device_ip} 已存在'
                    }
                
                # 创建新设备
                new_device = NetworkDevice(
                    user_id=user_id,
                    ip_address=device_ip,
                    hostname=device_name,
                    device_type=device_type,
                    brand=device_brand,
                    snmp_community=snmp_community,
                    ssh_username=ssh_username,
                    ssh_password=ssh_password,
                    status='unknown'
                )
                
                db.session.add(new_device)
                db.session.commit()
                
                return {
                    'success': True,
                    'result': new_device.to_dict(),
                    'message': f'设备 {device_name} ({device_ip}) 添加成功'
                }
            
            # 删除设备
            elif function_name == 'remove_device':
                device_id = arguments.get('device_id')
                device_ip = arguments.get('device_ip')
                force_remove = arguments.get('force_remove', False)
                
                from models import NetworkDevice, db
                
                # 查找设备
                if device_id:
                    device = NetworkDevice.query.filter_by(
                        device_id=device_id,
                        user_id=user_id
                    ).first()
                elif device_ip:
                    device = NetworkDevice.query.filter_by(
                        ip_address=device_ip,
                        user_id=user_id
                    ).first()
                else:
                    return {
                        'success': False,
                        'error': '需要提供设备ID或IP地址'
                    }
                
                if not device:
                    return {
                        'success': False,
                        'error': '设备不存在'
                    }
                
                # 删除设备
                device_info = device.to_dict()
                db.session.delete(device)
                db.session.commit()
                
                return {
                    'success': True,
                    'result': device_info,
                    'message': f'设备 {device.hostname or device.ip_address} 删除成功'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'未知的工具函数: {function_name}'
                }
                
        except Exception as e:
            self.logger.error(f"执行工具调用失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """执行工具调用 - API端点使用的方法"""
        try:
            # 构造工具调用格式
            tool_call = {
                'function': {
                    'name': tool_name,
                    'arguments': json.dumps(params)
                }
            }
            
            # 调用现有的execute_tool_call方法
            return self.execute_tool_call(tool_call, user_id)
            
        except Exception as e:
            self.logger.error(f"执行工具失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_tool_results(self, tool_results: List[Dict[str, Any]], user_id: int, session_id: str = None, mode: str = 'chat', model: str = None) -> Dict[str, Any]:
        """处理工具执行结果 - API端点使用的方法"""
        try:
            # 获取会话历史以构建完整上下文
            messages = []

            messages.append({
                'role': 'system',
                'content': self.generate_system_prompt(mode)
            })
            
            if session_id:
                from models import ChatSession, ChatMessage
                
                # 获取会话
                chat_session = ChatSession.query.filter_by(
                    session_id=session_id,
                    user_id=user_id
                ).first()
                
                if chat_session:
                    # 获取最近的消息历史
                    message_history = ChatMessage.query.filter_by(
                        session_id=chat_session.id
                    ).order_by(ChatMessage.created_at.asc()).limit(20).all()
                    
                    # 构建对话上下文
                    for msg in message_history:
                        message_data = {
                            'role': msg.role,
                            'content': msg.content
                        }
                        
                        # 处理工具调用信息
                        if msg.tool_calls and json.loads(msg.tool_calls):
                            try:
                                tool_calls = json.loads(msg.tool_calls) if isinstance(msg.tool_calls, str) else msg.tool_calls
                                message_data['tool_calls'] = tool_calls
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        # 处理工具调用结果
                        if msg.role == 'tool' and msg.tool_call_id:
                            message_data['tool_call_id'] = msg.tool_call_id
                            # 从元数据中获取工具名称
                            if msg.message_metadata:
                                try:
                                    metadata = json.loads(msg.message_metadata)
                                    if 'tool_name' in metadata:
                                        message_data['name'] = metadata['tool_name']
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        
                        messages.append(message_data)
            
            # 添加工具结果消息
            for result in tool_results:
                tool_message = {
                    'role': 'tool',
                    'content': json.dumps(result.get('result', {}), ensure_ascii=False),
                    'tool_call_id': result.get('tool_id'),  # 前端传递的是tool_id字段
                    'name': result.get('tool_name')
                }
                messages.append(tool_message)

            # print(messages)
            
            # 调用AI生成响应
            request_params = {
                'model': self.model if model is None else model,
                'messages': messages,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'presence_penalty': self.presence_penalty,
                'frequency_penalty': self.frequency_penalty
            }
            if not self.use_local:
                request_params['tools'] = self._get_available_tools(mode)

            response = self.client.chat.completions.create(**request_params)
            
            # 处理AI响应
            ai_response = self._process_response(response)
            
            # 返回与正常聊天一致的格式
            return {
                'ai_message': ai_response
            }
            
        except Exception as e:
            self.logger.error(f"处理工具结果失败: {e}")
            return {
                'ai_message': {
                    'content': f'处理工具结果时发生错误: {str(e)}',
                    'tool_calls': [],
                    'choice': {}
                }
            }
    
    def generate_system_prompt(self, mode: str) -> str:
        """生成系统提示词"""
        base_prompt = """
你是一个面向非专业用户的网络管理助手。用户可能不理解专业术语（如IP、子网掩码、交换机、路由协议等），请务必遵守以下规则：

### 输出语言要求
**所有回复必须使用中文**，不要输出英文或混合中英文。

### 核心工作原则
1. **术语解释优先**：当涉及专业概念时，先用通俗语言解释（例如："IP地址相当于设备的门牌号"）
2. **数据驱动决策**：用户未提供参数时，必须调用数据获取工具（如`network_scan`/`get_device_info`）
3. **以解决问题为主**：用户提出问题后，将完全由你来解决 解决问题的方式可以是修改配置、重启设备等
4. **零假设禁止**：不得自行假设任何参数（如IP地址、设备型号），必须通过工具获取或用户确认
5. **网络设备操作**：目前所有的网络设备操作都是基于ssh的，如果get_netwirk_status或者get_network_info获取到的信息有无法连接的设备，不要对他进行任何操作！

### 关键工作流程
```mermaid
graph TD
    A[用户请求] --> B{参数完整？}
    B -- 是 --> C[直接执行]
    B -- 否 --> D[调用数据获取工具]
    D --> E[结果用'|'分割]
    E --> F[用户选择]
    F --> C
```

### 可用工具清单（需严格按规范调用）
| 工具类型 | 函数名 | 用途说明 | 关键参数示例 |
|---------|--------|---------|------------|
| **状态监控** | `get_network_status` | 看网络健康状态 | `include_details: true` |
| **连接测试** | `connectivity_test` | 测试设备连通性 | `target_ip: '10.1.1.1', test_type: 'ping'` |
| **配置管理** | `huawei(尚不支持)/cisco(尚不支持)/h3c(尚不支持)/dcn_get_config` | 读设备配置 | `device_ip: '192.168.1.1', config_type: 'interface'` |
| **配置修改** | `huawei(尚不支持)/cisco(尚不支持)/h3c(尚不支持)/dcn_modify_config` | 改设备配置 | `commands: ['interface Gig0/0/1', 'ip address 192.168.1.1 255.255.255.0']` |
| **设备控制** | `device_reboot` | 重启设备 | `device_ip: '192.168.1.1', device_brand: 'huawei'` |
| **拓扑管理** | `save_topology` | 保存网络拓扑 | `topology_data: {...}` |
| **诊断工具** | `trace_route` | 跟踪网络路径 | `target: 'www.example.com'` |

### 用户交互规范
1. **当参数缺失时**  
   - 示例用户问："我想重启交换机"  
   - 你必须：  
     (1) 调用`get_device_info`获取设备列表  
     (2) 返回`192.168.1.1(交换机A)|192.168.1.126(交换机B)`

2. **当用户选择后**  
   - 严格使用用户选择的参数执行后续操作  
   - 禁止修改或补充参数（如用户选`192.168.1.101`，不得擅自添加子网掩码）

3. **泛型指令**
   - 示例用户问："请关闭交换机"    
   - 你不要继续询问用户具体参数，请使用信息类function获取(仅限于当前已知的拓扑网络 比如:get_network_status get_network_info)
   - 如果有多个数据则每个数据之间使用'|'分割传入function的parameters中由用户进行选择

4. **解决问题**
   - 当用户要求你解决某些问题时，请善用获取配置类function以及修改配置类function
   - 不要只进行简单的修改，比如重启设备
   - 要以用户描述的问题为准，当出现无法访问的设备时，不要尝试访问(包括获取/修改配置以及重启操作)，因为所有的网络工具都是基于网络的
   - 当问题进入僵局后请尝试检查设备的配置情况并对此做出修复
   - 在解决问题的时候不要轻易重启设备，除非用户明确要求重启

5. **设备型号**
   - 在不清楚设备品牌的情况下请使用get_network_info获取数据查看设备型号，从而调用正确的获取/设置配置function
   - 以下是对应关系:
     (1) 华为(huawei): `huawei_get_config`/`huawei_modify_config`
     (2) 思科(cisco): `cisco_get_config`/`cisco_modify_config`
     (3) H3C(h3c): `h3c_get_config`/`h3c_modify_config`
     (4) DCN(dcn): `dcn_get_config`/`dcn_modify_config`


6. **设备硬件问题**
   - 在用户没有确切说明的情况下，整个网络拓扑中的所有设备都是健康的（既可以实时响应配置并生效）
   - 在设备没有硬件问题的情况下，不要尝试重启设备解决问题，请尝试检查网络环境及其出现问题的设备的周边设备的配置情况
     


### 禁止行为
❌ 自行推断IP地址/设备型号 
❌ 用专业术语解释而不提供通俗类比  
❌ 合并多个工具调用结果（必须保持`|`分割）  
❌ 在未获取数据时执行依赖参数的操作  

请严格按此规则工作，所有操作必须通过上述工具实现，最终结果需以用户可理解的日常语言呈现。
"""
        
        return base_prompt
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            # 发送一个简单的请求来验证API密钥
            response = self.client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': 'Hello'}],
                max_tokens=5
            )
            return True
        except Exception as e:
            self.logger.error(f"API密钥验证失败: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            models = self.client.models.list()
            available_models = [model.id for model in models.data]
            
            return {
                'current_model': self.model,
                'available_models': available_models,
                'api_base': self.api_base,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'presence_penalty': self.presence_penalty,
                'frequency_penalty': self.frequency_penalty
            }
        except Exception as e:
            self.logger.error(f"获取模型信息失败: {e}")
            return {
                'current_model': self.model,
                'available_models': [],
                'error': str(e)
            }
