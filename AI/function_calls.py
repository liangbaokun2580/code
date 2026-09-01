#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Function Call 结果处理数据配置文件
存储function_name对应的结果处理数据
"""

from pathlib import Path
from typing import Dict, Any


def _read_write_yaml_script_output() -> str:
    """Load the YAML snippets returned by Write_YAML_script."""
    project_root = Path(__file__).resolve().parent.parent / "AI project2 back"
    yaml_files = [
        "trusted-repo-template.yaml",
        "trusted-repo-constraint.yaml",
        "bad-pod.yaml",
    ]

    parts = []
    for filename in yaml_files:
        yaml_path = project_root / filename
        content = yaml_path.read_text(encoding="utf-8").rstrip()

        parts.append(f"{filename}\n\n```yaml\n{content}\n```")

    return "\n\n".join(parts)


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
                                    '{"device_ip":"192.168.1.11|192.168.1.126", '
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
    "start_slave1": {
        "response": {
            "id": "chatcmpl-slave1-result-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "slave1启动命令已发送，Slave1正在启动中。"
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
                                    '{"device_ip": "192.168.1.11", '
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
                                    '{"device_ip": "10.1.50.126", '
                                    '"commands": ["interface Ethernet1/0/3","no ip access-group ACL in"]}'
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
    },
    "Write_YAML_script": {
        "response": {
            "id": "chatcmpl-func-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": _read_write_yaml_script_output()
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
