# 关键词数据配置文件
# 存储关键词对应的响应数据和function call数据

KEYWORDS_DATA = {
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
                    "content": "我是一个AI助手，可以帮助您处理各种问题。请告诉我您需要什么帮助？"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
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
                    "content": "正在为您重启交换机...",
                    'tool_calls': [
                        {
                            'id': 'call_5Z2EECDTdVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function':
                            {
                                'name': 'get_network_status',
                                'arguments': '{"include_details":true}'
                            }
                        },
                        {
                            'id': 'call_5Z2EECDTdVeEI52jhdVZvIxT',
                            'type': 'function',
                            'function':
                            {
                                'name': 'get_network_info',
                                'arguments': ''
                            }
                        }
                    ]
                },
                "finish_reason": "stop"
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
                    "content": "我将尝试检查网络连接并修复问题。请稍等片刻。",
                    'tool_calls': [
                        {
                            'id': 'call_5ZSEECDTdVeEI52jhdhZvIxT',
                            'type': 'function',
                            'function':
                            {
                                'name': 'get_network_info',
                                'arguments': ''
                            }
                        },
                        {
                            'id': 'call_5Z2EECDTdVeEIB2jhdVZvIxT',
                            'type': 'function',
                            'function':
                            {
                                'name': 'get_network_status',
                                'arguments': '{"include_details":true}'
                            }
                        }
                    ]
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