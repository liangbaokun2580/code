# 计划：聊天输入"开启slave1"触发真实 SSH 执行（+ AI模拟服务器定义）

## 摘要
实现两处联动：

1. **网页平台真实执行**（`d:\code\AI project2 back`）：聊天框输入 **"开启slave1"** 后，真正通过 SSH 连接 `192.168.1.7` 执行 `virsh start s1`，复用已有真实执行工具 [tools/start_slave1.py](file:///d:/code/AI%20project2%20back/tools/start_slave1.py)。
2. **AI 模拟服务器定义**（`d:\code\AI`）：在 `keywords_data.py` / `function_calls.py` / `config_manager.py` 中按现有模式加入"开启slave1"关键词与 `start_slave1` 函数定义，保证模拟 API 也能响应此关键词。

## 现状分析（来自 Phase 1 探索）

### 网页平台聊天→工具执行链路
1. 前端 [chat.js](file:///d:/code/AI%20project2%20back/static/js/chat.js) 发送消息 → `POST /api/chat/sessions/<id>/messages` → [api/chat.py](file:///d:/code/AI%20project2%20back/api/chat.py#L218-L348) `send_message`
2. `send_message` 调用 `ai_service.chat_completion(...)`（[services/ai_service.py](file:///d:/code/AI%20project2%20back/services/ai_service.py#L781-L822)），返回 `response`（可含 `tool_calls`，OpenAI 格式 `[{id, type, function:{name, arguments}}]`）
3. 前端 `executeToolCalls`（[chat.js](file:///d:/code/AI%20project2%20back/static/js/chat.js#L563-L666)）→ `POST /api/chat/tools/execute` → [api/chat.py](file:///d:/code/AI%20project2%20back/api/chat.py#L412-L448) `execute_tool` → `ai_service.execute_tool_call(...)` 真实执行
4. 前端 `POST /api/chat/tools/results` → `process_tool_results` → LLM 生成最终总结

关键位置：
- [services/ai_service.py](file:///d:/code/AI%20project2%20back/services/ai_service.py#L989-L1455) `execute_tool_call`：硬编码 `elif function_name == '...'` 分支，`else` 返回"未知的工具函数"。**无 `start_slave1` 分支。**
- [services/ai_service.py](file:///d:/code/AI%20project2%20back/services/ai_service.py#L112-L779) `_get_available_tools`：chat 工具定义列表，以 `return tools` 结束。**无 `start_slave1` 定义。**
- [tools/start_slave1.py](file:///d:/code/AI%20project2%20back/tools/start_slave1.py)（已存在）：`run(params)` 要求 `params["input"] == "开启slave1"`，用 `ssh -o BatchMode=yes -o ConnectTimeout=10 192.168.1.7 virsh start s1` 真实执行，返回 `{"success","message","data"}`。

### AI 模拟服务器（`d:\code\AI`）
- [keywords_data.py](file:///d:/code/AI/keywords_data.py)：`KEYWORDS_DATA` 关键词 → 带 `tool_calls` 的模拟响应（如"天气"→`get_weather`）。
- [function_calls.py](file:///d:/code/AI/function_calls.py)：`FUNCTION_RESULTS` 函数名 → 模拟结果响应。
- [config_manager.py](file:///d:/code/AI/config_manager.py#L32-L103)：`get_available_tools` 注册工具列表。
- [ai_api_server.py](file:///d:/code/AI/ai_api_server.py#L125-L160)：`_resolve_function_name` 根据 tool 消息解析函数名，含 weather/time/calc/yaml 启发式回退。

## 修改方案

### 1. `d:\code\AI\keywords_data.py` — 添加"开启slave1"关键词
在 `KEYWORDS_DATA` 中（如"重启"条目之后）新增：

```python
"开启slave1": {
    "response": {
        "id": "chatcmpl-slave1-001",
        "object": "chat.completion",
        "created": 1699000000,
        "model": "gpt-3.5-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
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
            "prompt_tokens": 15,
            "completion_tokens": 10,
            "total_tokens": 25
        }
    }
},
```

### 2. `d:\code\AI\function_calls.py` — 添加 `start_slave1` 函数结果
在 `FUNCTION_RESULTS` 中新增：

```python
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
                "content": "slave1启动命令已发送，正在通过SSH连接192.168.1.7执行 virsh start s1"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 10,
            "total_tokens": 25
        }
    }
},
```

### 3. `d:\code\AI\config_manager.py` — 注册 `start_slave1` 工具
在 `get_available_tools()` 返回列表中（`Write_YAML_script` 之后）新增：

```python
{
    "type": "function",
    "function": {
        "name": "start_slave1",
        "description": "通过SSH连接192.168.1.7启动slave1虚拟机（执行 virsh start s1）",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "请输入：开启slave1"
                }
            },
            "required": ["input"]
        }
    }
}
```

### 4. `d:\code\AI\ai_api_server.py` — `_resolve_function_name` 增加启发式（遵循现有模式）
在 `_resolve_function_name` 的启发式回退区（yaml/script 判断之后）新增：

```python
if "slave1" in tool_call_id or "slave1" in tool_content:
    return "start_slave1"
```

> 主解析路径（tool 消息含 `name` 或 tool_call_id 匹配 assistant tool_calls）已能解析 `start_slave1`，此启发式仅作兜底，与现有 weather/time/calc/yaml 一致。

### 5. `d:\code\AI project2 back\services\ai_service.py`

**(a) 注册 `start_slave1` 工具定义**：在 `_get_available_tools` chat 工具列表中 `trace_route` 条目之后、第 777 行 `]` 之前新增（内容同第 3 步的 schema）。

**(b) 新增执行分支**：在 `execute_tool_call` 第 1451 行 `else:` 之前插入：

```python
elif function_name == 'start_slave1':
    import importlib.util
    tool_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'tools', 'start_slave1.py'
    )
    spec = importlib.util.spec_from_file_location('start_slave1_tool', tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_result = module.run(arguments)
    return {
        'success': tool_result.get('success', False),
        'result': tool_result.get('data', {}),
        'message': tool_result.get('message', '启动slave1命令已执行')
    }
```

> 复用已有真实 SSH 工具，单一数据源，返回结构与现有分支一致。

### 6. `d:\code\AI project2 back\api\chat.py` — `send_message` 确定性触发
在第 277 行调用 `ai_service.chat_completion(...)` 之前，加入关键词短路判断。当用户消息包含 **"开启slave1"** 时，跳过 LLM 决策，直接构造带 `tool_calls` 的响应，保证必然触发真实执行：

```python
# 确定性触发：输入"开启slave1"→ SSH连接192.168.1.7执行 virsh start s1
if "开启slave1" in user_message:
    ai_response = {
        'success': True,
        'response': {
            'role': 'assistant',
            'content': '正在通过SSH连接192.168.1.7启动slave1虚拟机，请稍候...',
            'finish_reason': 'tool_calls',
            'tool_calls': [{
                'id': f'call_slave1_{uuid.uuid4().hex[:8]}',
                'type': 'function',
                'function': {
                    'name': 'start_slave1',
                    'arguments': json.dumps({'input': '开启slave1'}, ensure_ascii=False)
                }
            }]
        },
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    }
else:
    ai_response = ai_service.chat_completion(
        messages=context, use_tools=True, stream=False,
        model=model, mode=mode
    )
```

> 前端 `executeToolCalls` 兼容 `toolCall.function.name` / `toolCall.function.arguments`；`send_message` 后续 tool_status 初始化（第 312-315 行）也能识别该结构。

## 触发后的完整链路
1. 用户输入"开启slave1" → `send_message` 返回带 `start_slave1` tool_call 的 assistant 消息
2. 前端 `executeToolCalls` → `POST /api/chat/tools/execute`（tool_name=start_slave1, params={"input":"开启slave1"}）
3. `execute_tool` → `execute_tool_call` 的 `start_slave1` 分支 → 运行 `tools/start_slave1.py` → 真实 SSH 到 `192.168.1.7` 执行 `virsh start s1`
4. 前端 `POST /api/chat/tools/results` → `process_tool_results` → LLM 生成最终总结

（`d:\code\AI` 模拟服务器独立生效：直接向其 API 发送含"开启slave1"的消息，会返回 `start_slave1` tool_call 及对应模拟结果。）

## 假设与决策
- 复用现有 [tools/start_slave1.py](file:///d:/code/AI%20project2%20back/tools/start_slave1.py) 原样（`ssh -o BatchMode=yes 192.168.1.7`，不带用户名 → 依赖本机对 192.168.1.7 的默认 SSH 用户/密钥配置；若未配置密钥，`BatchMode=yes` 会直接失败）。
- 网页平台采用后端确定性关键词触发（而非依赖 LLM 自主选择工具调用），保证"输入即执行"。
- 最终总结回复仍走 LLM（与现有所有工具架构一致）。
- 模拟服务器定义仅为模拟响应，不执行真实 SSH（符合其设计）。

## 验证步骤
1. 重启网页平台：在 `d:\code\AI project2 back` 下运行 `python app.py`
2. 登录 → 进入聊天页 → 发送 **"开启slave1"**
3. 检查界面：assistant 消息显示工具调用 `start_slave1`（执行中 → 已完成），随后出现 AI 总结回复
4. 检查后端日志/返回数据：`return_code`、`stdout`、`stderr`（确认 SSH 已连接 192.168.1.7 并执行 `virsh start s1`）
5. （回归）发送普通消息（如"你好"），确认不触发工具、正常走 LLM 对话
6. 模拟服务器：启动 `d:\code\AI` 的 `ai_api_server.py`，向 `/chat/completions` 发送含"开启slave1"的消息，确认返回 `start_slave1` tool_call；再发送含该 tool 结果的请求，确认返回模拟总结
7. 若 SSH 失败，检查 192.168.1.7 的密钥认证配置
