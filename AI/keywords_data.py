#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词数据配置文件
存储关键词对应的响应数据和 function call 数据
"""

from typing import Any, Dict


def _yaml_tool_response(call_id: str, arguments: str = "") -> Dict[str, Any]:
    return {
        "id": "chatcmpl-yaml-001",
        "object": "chat.completion",
        "created": 1699000000,
        "model": "gpt-3.5-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "正在输出 YAML 脚本，请稍后。",
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "Write_YAML_script",
                        "arguments": arguments
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }


KEYWORDS_DATA: Dict[str, Dict[str, Any]] = {
    "天气": {
        "response": {
            "id": "chatcmpl-weather-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_weather_001",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "北京"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 15,
                "total_tokens": 35
            }
        }
    },
    "时间": {
        "response": {
            "id": "chatcmpl-time-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_time_001",
                        "type": "function",
                        "function": {
                            "name": "get_current_time",
                            "arguments": '{"timezone": "Asia/Shanghai"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 18,
                "completion_tokens": 12,
                "total_tokens": 30
            }
        }
    },
    "计算": {
        "response": {
            "id": "chatcmpl-calc-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_calc_001",
                        "type": "function",
                        "function": {
                            "name": "calculate",
                            "arguments": '{"expression": "2+2"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 25
            }
        }
    },
    "重启": {
        "response": {
            "id": "chatcmpl-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "正在为您检查网络状态。",
                    "tool_calls": [
                        {
                            "id": "call_reboot_status_001",
                            "type": "function",
                            "function": {
                                "name": "get_network_status",
                                "arguments": '{"include_details": true}'
                            }
                        },
                        {
                            "id": "call_reboot_info_001",
                            "type": "function",
                            "function": {
                                "name": "get_network_info",
                                "arguments": ""
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    },
    "slave1": {
        "response": {
            "id": "chatcmpl-slave1-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content":"我将尝试启动Slave1，请稍等。",
                    "tool_calls": [{
                        "id": "call_slave1_001",
                        "type": "function",
                        "function": {
                            "name": "start_slave1",
                            "arguments": '{"input": "开启slave1"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    },
    "修复": {
        "response": {
            "id": "chatcmpl-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "我将尝试检查网络连接并修复问题，请稍等。",
                    "tool_calls": [
                        {
                            "id": "call_fix_info_001",
                            "type": "function",
                            "function": {
                                "name": "get_network_info",
                                "arguments": ""
                            }
                        },
                        {
                            "id": "call_fix_status_001",
                            "type": "function",
                            "function": {
                                "name": "get_network_status",
                                "arguments": '{"include_details": true}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    },
    "脚本": {
        "response": _yaml_tool_response("call_yaml_script_001")
    },
    "yaml": {
        "response": _yaml_tool_response("call_yaml_script_002")
    },
    "yml": {
        "response": _yaml_tool_response("call_yaml_script_003")
    },
    "script": {
        "response": _yaml_tool_response("call_yaml_script_004")
    },
    "默认": {
        "response": {
            "id": "chatcmpl-default-001",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "我是一个 AI 助手，可以帮助您处理各种问题。请告诉我您需要什么帮助？"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    }
}
