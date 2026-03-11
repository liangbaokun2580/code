#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Function Call 结果处理数据配置文件
存储function_name对应的结果处理数据
"""

from typing import Dict, Any


FUNCTION_RESULTS: Dict[str, Dict[str, Any]] = {
    "get_weather": {
        "response": {
            "id": "chatcmpl-weather-result-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        "根据天气数据，今天北京天气晴朗，温度25°C，"
                        "湿度60%，风速5km/h。适合外出活动。"
                    )
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 30,
                "total_tokens": 80
            }
        }
    },
    "get_current_time": {
        "response": {
            "id": "chatcmpl-time-result-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "当前时间是：2024年1月15日 14:30:25 (北京时间)"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 40,
                "completion_tokens": 25,
                "total_tokens": 65
            }
        }
    },
    "calculate": {
        "response": {
            "id": "chatcmpl-calc-result-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "计算结果：2 + 2 = 4"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 35,
                "completion_tokens": 15,
                "total_tokens": 50
            }
        }
    },
    "default_function": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Function执行完成，但未找到对应的处理结果。"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    },
    "get_network_info": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "发送重启命令中...",
                    'tool_calls': [
                        {
                            'id': 'call_5Z2EECSTdVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function': {
                                'name': 'device_reboot',
                                'arguments': (
                                    '{"device_ip":"192.168.1.1|192.168.1.126", '
                                    '"device_brand": "dcn"}'
                                )
                            }
                        }
                    ]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    },
    "device_reboot": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "重启命令已发送，设备正在重启中"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    },
    "get_network_status": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "正在查看网络设备配置中...",
                    'tool_calls': [
                        {
                            'id': 'call_5ZSEECDTdVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function': {
                                'name': 'dcn_get_config',
                                'arguments': (
                                    '{"device_ip": "192.168.1.1", '
                                    '"config_type": "running"}'
                                )
                            }
                        },
                        {
                            'id': 'call_5ZSEECDTNVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function': {
                                'name': 'dcn_get_config',
                                'arguments': (
                                    '{"device_ip": "192.168.1.126", '
                                    '"config_type": "running"}'
                                )
                            }
                        }
                    ]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    },
    "dcn_get_config": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "我发现了问题所在，本机和接入层交换机和服务器之间没有路由配置，我将添加相应配置以修复这个问题。",
                    'tool_calls': [
                        {
                            'id': 'call_5aSEECDTdVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function': {
                                'name': 'dcn_modify_config',
                                'arguments': (
                                    '{"device_ip": "192.168.1.126", '
                                    '"commands": ["int vlan164","ip address 192.168.7.1 255.255.255.0","exit","interface Ethernet1/0/22","switchport access vlan 164","exit","router ospf 1","network 192.168.7.1 0.0.0.255 area 0","exit","interface Ethernet1/0/7", '
                                    '"no ip access-group ACL in"]}'
                                )
                            }
                        }
                    ]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    },
    "dcn_modify_config": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "配置修改完成，网络问题已修复，请测试网络连接。"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 50
            }
        }
    }
}