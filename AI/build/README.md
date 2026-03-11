# AI API 服务

一个兼容 OpenAI API 格式的智能 API 服务，支持双模式运行：关键词匹配的 if...else 模式和 Ollama 本地大模型模式。

## 功能特性

### 🔄 双模式支持
- **if...else 模式**：基于关键词匹配的快速响应模式
- **Ollama 模式**：集成本地大语言模型的智能对话模式
- **动态切换**：支持运行时模式切换，无需重启服务

### 🛠️ Function Call 支持
- 天气查询 (`get_weather`)
- 时间获取 (`get_current_time`)
- 数学计算 (`calculate`)
- 网络信息 (`get_network_info`)
- 设备重启 (`device_reboot`)
- 网络状态 (`get_network_status`)
- DCN 配置管理 (`dcn_get_config`, `dcn_modify_config`)

### 📡 OpenAI 兼容 API
- 完全兼容 OpenAI Chat Completions API
- 支持流式和非流式响应
- 支持 tools/function calling
- 标准的错误处理和响应格式

## 项目结构

```
build/
├── ai_api_server.py          # 主服务器文件
├── config_manager.py         # 配置管理器
├── mode_manager.py           # 模式管理器
├── ollama_client.py          # Ollama 客户端
├── keywords_data.py          # 关键词数据
├── function_calls.py         # Function Call 数据
├── test_client.py            # API 测试客户端
├── test_ollama_client.py     # Ollama 兼容性测试
├── ollama_config.json        # Ollama 配置文件
├── requirements.txt          # Python 依赖
└── README.md                 # 项目文档
```

## 安装和运行

### 1. 环境准备

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `ollama_config.json` 文件，配置 Ollama 服务：

```json
{
  "base_url": "http://localhost:11434",
  "default_model": "llama2",
  "temperature": 0.7,
  "max_tokens": 2048,
  "timeout": 30,
  "model_mapping": {
    "gpt-3.5-turbo": "llama2",
    "gpt-4": "llama2:13b",
    "gpt-4-turbo": "mistral"
  }
}
```

### 3. 启动服务

```bash
# 启动 AI API 服务
python ai_api_server.py

# 服务将在 http://localhost:5000 启动
```

### 4. 安装 Ollama（可选）

如果要使用 Ollama 模式，需要先安装 Ollama：

```bash
# 下载并安装 Ollama
# 访问 https://ollama.ai 获取安装包

# 拉取模型
ollama pull llama2
ollama pull mistral
```

## API 使用

### 聊天 API

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

### 模式管理 API

```bash
# 获取当前模式
curl http://localhost:5000/v1/mode

# 切换模式
curl -X POST http://localhost:5000/v1/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "ollama"}'

# 获取模式配置
curl http://localhost:5000/v1/mode/config

# 重新加载配置
curl -X POST http://localhost:5000/v1/mode/reload
```

### 其他 API

```bash
# 获取模型列表
curl http://localhost:5000/v1/models

# 获取工具列表
curl http://localhost:5000/v1/tools

# 健康检查
curl http://localhost:5000/health
```

## 测试

### 基础功能测试

```bash
# 运行基础 API 测试
python test_client.py

# 运行 Ollama 兼容性测试
python test_ollama_client.py
```

### Function Call 测试

```python
# 天气查询示例
messages = [
    {"role": "user", "content": "北京今天天气怎么样？"}
]

# 时间查询示例
messages = [
    {"role": "user", "content": "现在几点了？"}
]

# 计算示例
messages = [
    {"role": "user", "content": "帮我计算 2+2"}
]
```

## 配置说明

### Ollama 配置

- `base_url`: Ollama 服务地址
- `default_model`: 默认使用的模型
- `temperature`: 生成温度（0-1）
- `max_tokens`: 最大生成长度
- `timeout`: 请求超时时间（秒）
- `model_mapping`: OpenAI 模型到 Ollama 模型的映射

### 模式说明

1. **if...else 模式**
   - 基于关键词匹配
   - 响应速度快
   - 适合固定场景
   - 支持预定义的 Function Call

2. **Ollama 模式**
   - 使用本地大语言模型
   - 智能对话能力
   - 需要 Ollama 服务支持
   - 支持多种开源模型

## 开发指南

### 添加新的 Function Call

1. 在 `function_calls.py` 中添加新的函数定义
2. 在 `keywords_data.py` 中添加对应的关键词映射
3. 在 `config_manager.py` 中注册新的工具

### 自定义关键词响应

编辑 `keywords_data.py` 文件，添加新的关键词和响应：

```python
KEYWORDS_DATA = {
    "新关键词": {
        "response": "自定义响应内容",
        "tool_calls": [...]  # 可选的工具调用
    }
}
```

## 故障排除

### 常见问题

1. **Ollama 连接失败**
   - 检查 Ollama 服务是否启动
   - 验证 `ollama_config.json` 中的 URL 配置
   - 确认防火墙设置

2. **模型不存在**
   - 使用 `ollama list` 查看已安装模型
   - 使用 `ollama pull <model>` 下载所需模型

3. **端口冲突**
   - 修改 `ai_api_server.py` 中的端口配置
   - 检查端口是否被其他服务占用

### 日志调试

服务启动时会显示详细的日志信息，包括：
- 模式切换状态
- Ollama 连接状态
- 请求处理过程
- 错误信息

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持双模式运行
- 完整的 OpenAI API 兼容性
- Function Call 支持
- 完善的测试套件