# AI API 服务 - Ollama 兼容层

一个符合 OpenAI API 规范的 AI 聊天服务，支持两种运行模式：
1. **if...else 模式**：基于关键词匹配的预定义响应，支持 Function Call
2. **Ollama 模式**：集成 Ollama 本地大语言模型的智能对话

## 功能特性

- ✅ 符合 OpenAI Chat Completions API 规范
- ✅ **双模式支持**：if...else 关键词模式 + Ollama 本地模型模式
- ✅ **动态模式切换**：运行时无缝切换模式
- ✅ **Ollama 兼容层**：自动转换 OpenAI 格式到 Ollama 格式
- ✅ Function Call 支持（if...else 模式）
- ✅ 模块化数据存储（关键词和 Function Call 数据分离）
- ✅ 完整的错误处理和服务可用性检查
- ✅ 健康检查和监控端点
- ✅ 配置管理和持久化

## 项目结构

```
AI/
├── ai_api_server.py      # 主 API 服务器（集成双模式支持）
├── ollama_client.py      # Ollama 客户端和兼容层
├── mode_manager.py       # 模式管理器
├── keywords_data.py      # 关键词响应数据
├── function_calls.py     # Function Call 结果数据
├── config_manager.py     # 配置管理
├── test_client.py        # 基础测试客户端
├── test_ollama_client.py # Ollama 兼容层测试客户端
├── requirements.txt      # 项目依赖
├── mode_config.json      # 模式配置文件（自动生成）
└── README.md            # 项目说明
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python ai_api_server.py
```

服务将在 `http://localhost:5000` 启动。

### 3. 运行测试

```bash
python test_client.py
```

## API 端点

### 核心聊天 API

**POST** `/v1/chat/completions`

符合 OpenAI Chat Completions API 规范的聊天接口，根据当前模式自动路由到对应的处理逻辑。

### 模式管理 API

**GET** `/v1/mode` - 获取当前模式信息
**POST** `/v1/mode/switch` - 切换运行模式
**GET** `/v1/mode/config` - 获取模式配置
**POST** `/v1/mode/config` - 更新模式配置

#### 请求示例

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "请帮我查询北京的天气"
    }
  ]
}
```

#### 响应示例（Function Call）

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699000000,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_weather_001",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"北京\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

### 其他端点

- **GET** `/v1/models` - 获取可用模型列表
- **GET** `/v1/tools` - 获取可用工具列表
- **GET** `/health` - 健康检查（包含模式状态）

## 双模式详细说明

### if...else 模式

基于关键词匹配的预定义响应模式，使用 if...else 逻辑进行关键词匹配：

| 关键词 | 触发条件 | Function Call |
|--------|----------|---------------|
| 天气 | "天气", "weather" | `get_weather` |
| 时间 | "时间", "time", "现在几点" | `get_current_time` |
| 计算 | "计算", "算", "数学", "calculate" | `calculate` |
| 默认 | 其他所有情况 | 无 |

### Ollama 模式

集成 Ollama 本地大语言模型，提供真正的 AI 对话能力：

- **自动格式转换**：OpenAI 请求格式 ↔ Ollama 请求格式
- **模型映射**：将 OpenAI 模型名称映射到本地 Ollama 模型
- **参数传递**：支持 temperature、max_tokens 等参数
- **错误处理**：自动检测 Ollama 服务可用性
- **流式响应**：支持 Ollama 的流式输出（可选）

## 模式切换

### 切换到指定模式

```bash
curl -X POST http://localhost:5000/v1/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "ollama"}'
```

### 自动切换模式

```bash
curl -X POST http://localhost:5000/v1/mode/switch
```

### 获取当前模式信息

```bash
curl http://localhost:5000/v1/mode
```

### 更新 Ollama 配置

```bash
curl -X POST http://localhost:5000/v1/mode/config \
  -H "Content-Type: application/json" \
  -d '{
    "ollama_config": {
      "base_url": "http://localhost:11434",
      "default_model": "llama2:latest",
      "temperature": 0.8
    }
  }'
```

## Function Call 工作流程（if...else 模式）

1. **用户发送包含关键词的消息**
   ```json
   {
     "model": "gpt-3.5-turbo",
     "messages": [
       {"role": "user", "content": "请查询北京天气"}
     ]
   }
   ```

2. **服务返回 Function Call 请求**
   ```json
   {
     "choices": [{
       "message": {
         "role": "assistant",
         "tool_calls": [{
           "function": {"name": "get_weather"}
         }]
       }
     }]
   }
   ```

3. **客户端执行 Function 并返回结果**
   ```json
   {
     "model": "gpt-3.5-turbo",
     "messages": [
       {"role": "user", "content": "请查询北京天气"},
       {"role": "assistant", "tool_calls": [...]},
       {
         "role": "tool",
         "tool_call_id": "call_weather_001",
         "name": "get_weather",
         "content": "{\"temperature\": \"25°C\"}"
       }
     ]
   }
   ```

4. **服务返回最终响应**
   ```json
   {
     "choices": [{
       "message": {
         "role": "assistant",
         "content": "根据天气数据，今天北京天气晴朗..."
       }
     }]
   }
   ```

## 数据配置

### 关键词数据 (`keywords_data.py`)

存储关键词对应的响应数据，包括 Function Call 定义。

### Function Call 结果 (`function_calls.py`)

存储 Function Call 执行后的响应数据，根据 `function_name` 进行匹配。

## 使用示例

### if...else 模式测试

```bash
# 运行基础测试客户端
python test_client.py
```

### Ollama 模式测试

```bash
# 运行 Ollama 兼容层测试客户端
python test_ollama_client.py
```

### 手动测试模式切换

```python
import requests

# 切换到 Ollama 模式
response = requests.post('http://localhost:5000/v1/mode/switch', 
                        json={'mode': 'ollama'})
print(response.json())

# 发送聊天请求（将使用 Ollama）
chat_response = requests.post('http://localhost:5000/v1/chat/completions',
                             json={
                                 'model': 'gpt-3.5-turbo',
                                 'messages': [{'role': 'user', 'content': '你好'}]
                             })
print(chat_response.json())
```

## 自定义扩展

### 添加新关键词（if...else 模式）

在 `keywords_data.py` 中添加新的关键词和响应：

```python
KEYWORDS_DATA = {
    "新关键词": {
        "keywords": ["关键词1", "关键词2"],
        "response": {
            # OpenAI 格式响应
        }
    }
}
```

### 添加新 Function Call（if...else 模式）

1. 在 `config_manager.py` 中添加工具定义
2. 在 `function_calls.py` 中添加结果数据
3. 在 `keywords_data.py` 中关联关键词

### 配置 Ollama 模型

```bash
# 拉取新模型
ollama pull llama2:13b

# 更新默认模型配置
curl -X POST http://localhost:5000/v1/mode/config \
  -H "Content-Type: application/json" \
  -d '{"ollama_config": {"default_model": "llama2:13b"}}'
```

## 错误处理

### 通用错误

- **400 Bad Request**: 请求格式错误
- **500 Internal Server Error**: 服务器内部错误
- **404 Not Found**: 端点不存在

### Ollama 特定错误

- **503 Service Unavailable**: Ollama 服务不可用
- **404 Model Not Found**: 指定的模型不存在
- **408 Request Timeout**: Ollama 请求超时

所有错误都会返回标准的 JSON 格式：

```json
{
  "error": {
    "message": "错误描述",
    "type": "错误类型",
    "code": "错误代码",
    "mode": "当前模式"
  }
}
```

## 注意事项

### Ollama 模式要求

1. **Ollama 服务必须运行**：确保 Ollama 在 `http://localhost:11434` 运行
2. **模型已下载**：使用 `ollama pull <model_name>` 下载所需模型
3. **网络连接**：确保服务器可以访问 Ollama API

### 性能考虑

- **if...else 模式**：响应速度极快，适合简单交互
- **Ollama 模式**：响应时间取决于模型大小和硬件性能
- **模式切换**：无需重启服务，但建议在低负载时进行

## 开发调试

### 启用调试模式

```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### 查看日志

服务会输出详细的请求和响应日志，便于调试。包括：
- 当前运行模式
- Ollama 服务状态
- 请求路由信息
- 错误详情

启动服务时会显示所有可用端点：

```
Starting AI API Server...
Available endpoints:
  POST /v1/chat/completions - Chat completions
  GET  /v1/models - List models
  GET  /v1/tools - List tools
  GET  /health - Health check

Server running on http://localhost:5000
```

## 许可证

本项目仅供学习和演示使用。