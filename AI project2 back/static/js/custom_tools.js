/**
 * 自定义工具页面的JavaScript功能
 */

class CustomToolsManager {
    constructor() {
        // DOM元素
        this.toolsList = document.getElementById('toolsList');
        this.codeEditor = document.getElementById('codeEditor');
        this.toolOutput = document.getElementById('toolOutput');
        this.parametersForm = document.getElementById('parametersForm');
        this.currentToolName = document.getElementById('currentToolName');
        this.saveToolBtn = document.getElementById('saveToolBtn');
        this.deleteToolBtn = document.getElementById('deleteToolBtn');
        this.runToolBtn = document.getElementById('runToolBtn');
        this.clearOutputBtn = document.getElementById('clearOutputBtn');
        
        // 表单元素
        this.toolName = document.getElementById('toolName');
        this.toolDescription = document.getElementById('toolDescription');
        this.toolCategory = document.getElementById('toolCategory');
        this.toolVersion = document.getElementById('toolVersion');
        this.toolAuthor = document.getElementById('toolAuthor');
        
        // 新建工具模态框元素
        this.newToolName = document.getElementById('newToolName');
        this.newToolDescription = document.getElementById('newToolDescription');
        this.newToolCategory = document.getElementById('newToolCategory');
        this.confirmCreateTool = document.getElementById('confirmCreateTool');
        
        // 状态变量
        this.tools = [];
        this.currentTool = null;
        this.editor = null;
        this.isEditing = false;
        
        // 初始化
        this.init();
    }
    
    /**
     * 初始化工具管理器
     */
    init() {
        // 初始化CodeMirror编辑器
        this.initCodeEditor();
        
        // 绑定事件
        this.bindEvents();
        
        // 加载工具列表
        this.loadTools();
    }
    
    /**
     * 初始化代码编辑器
     */
    initCodeEditor() {
        this.editor = CodeMirror(this.codeEditor, {
            mode: 'python',
            theme: 'dracula',
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            indentWithTabs: false,
            lineWrapping: true,
            matchBrackets: true,
            styleActiveLine: true,
            extraKeys: {
                'Tab': function(cm) {
                    cm.replaceSelection('    ', 'end');
                }
            }
        });
        
        // 设置编辑器初始内容
        this.editor.setValue('# 在这里编写您的自定义工具代码\n');
        
        // 标记为已修改时启用保存按钮
        this.editor.on('change', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
            }
        });
    }
    
    /**
     * 绑定事件处理函数
     */
    bindEvents() {
        // 创建工具按钮点击事件
        document.getElementById('createToolBtn').addEventListener('click', () => {
            $('#createToolModal').modal('show');
        });
        
        // 确认创建工具按钮点击事件
        this.confirmCreateTool.addEventListener('click', this.handleCreateTool.bind(this));
        
        // 保存工具按钮点击事件
        this.saveToolBtn.addEventListener('click', this.saveTool.bind(this));
        
        // 删除工具按钮点击事件
        this.deleteToolBtn.addEventListener('click', this.deleteTool.bind(this));
        
        // 运行工具按钮点击事件
        this.runToolBtn.addEventListener('click', this.runTool.bind(this));
        
        // 清空输出按钮点击事件
        this.clearOutputBtn.addEventListener('click', () => {
            this.toolOutput.textContent = '准备就绪，等待运行工具...';
        });
        
        // 工具分类点击事件
        document.querySelectorAll('.list-group-item[data-category]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // 更新激活状态
                document.querySelectorAll('.list-group-item[data-category]').forEach(el => {
                    el.classList.remove('active');
                });
                item.classList.add('active');
                
                // 过滤工具列表
                const category = item.dataset.category;
                this.filterToolsByCategory(category);
            });
        });
        
        // 表单元素变更事件
        this.toolName.addEventListener('input', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
                this.currentToolName.textContent = this.toolName.value || '未命名工具';
            }
        });
        
        this.toolDescription.addEventListener('input', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
            }
        });
        
        this.toolCategory.addEventListener('change', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
            }
        });
        
        this.toolVersion.addEventListener('input', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
            }
        });
        
        this.toolAuthor.addEventListener('input', () => {
            if (this.currentTool) {
                this.saveToolBtn.disabled = false;
            }
        });
    }
    
    /**
     * 加载工具列表
     */
    loadTools() {
        // 清空工具列表
        this.toolsList.innerHTML = '<div class="list-group-item text-center text-muted"><i class="fas fa-spinner fa-spin me-2"></i>加载中...</div>';
        
        // 发送API请求获取工具列表
        ApiClient.get('/api/custom_tools/list')
            .then(response => {
                if (response.success) {
                    this.tools = response.tools || [];
                    this.renderToolsList();
                } else {
                    this.showError('加载工具列表失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('加载工具列表失败: ' + error.message);
            });
    }
    
    /**
     * 渲染工具列表
     */
    renderToolsList() {
        // 清空工具列表
        this.toolsList.innerHTML = '';
        
        // 如果没有工具，显示提示信息
        if (this.tools.length === 0) {
            this.toolsList.innerHTML = '<div class="list-group-item text-center text-muted">暂无工具，点击"新建工具"创建</div>';
            return;
        }
        
        // 添加工具到列表
        this.tools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'list-group-item tool-item';
            item.dataset.toolId = tool.id;
            
            // 设置工具项内容
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="tool-name">${tool.name}</div>
                    <span class="tool-category ${tool.category || 'other'}">${this.getCategoryName(tool.category)}</span>
                </div>
                <div class="tool-description">${tool.description || '无描述'}</div>
                <div class="small text-muted mt-1">
                    <span>版本: ${tool.version || '1.0'}</span>
                    <span class="ms-2">作者: ${tool.author || '未知'}</span>
                </div>
            `;
            
            // 点击加载工具
            item.addEventListener('click', () => {
                this.loadTool(tool.id);
            });
            
            this.toolsList.appendChild(item);
        });
    }
    
    /**
     * 根据分类过滤工具列表
     */
    filterToolsByCategory(category) {
        // 显示所有工具项
        const toolItems = this.toolsList.querySelectorAll('.tool-item');
        toolItems.forEach(item => {
            if (category === 'all') {
                item.style.display = 'block';
            } else {
                const toolId = item.dataset.toolId;
                const tool = this.tools.find(t => t.id === toolId);
                if (tool && tool.category === category) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            }
        });
    }
    
    /**
     * 获取分类名称
     */
    getCategoryName(category) {
        const categories = {
            'network': '网络',
            'system': '系统',
            'security': '安全',
            'other': '其他'
        };
        return categories[category] || '其他';
    }
    
    /**
     * 加载工具详情
     */
    loadTool(toolId) {
        // 更新工具项激活状态
        const toolItems = this.toolsList.querySelectorAll('.tool-item');
        toolItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.toolId === toolId) {
                item.classList.add('active');
            }
        });
        
        // 发送API请求获取工具详情
        ApiClient.get(`/api/custom_tools/get/${toolId}`)
            .then(response => {
                if (response.success) {
                    this.currentTool = response.tool;
                    this.displayTool(response.tool);
                } else {
                    this.showError('加载工具详情失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('加载工具详情失败: ' + error.message);
            });
    }
    
    /**
     * 显示工具详情
     */
    displayTool(tool) {
        // 更新工具名称
        this.currentToolName.textContent = tool.name;
        
        // 更新表单字段
        this.toolName.value = tool.name || '';
        this.toolDescription.value = tool.description || '';
        this.toolCategory.value = tool.category || 'other';
        this.toolVersion.value = tool.version || '1.0';
        this.toolAuthor.value = tool.author || '';
        
        // 更新代码编辑器内容
        this.editor.setValue(tool.code || '');
        
        // 启用按钮
        this.saveToolBtn.disabled = true;
        this.deleteToolBtn.disabled = false;
        
        // 解析参数并更新参数表单
        this.updateParametersForm(tool.parameters || []);
        
        // 启用运行按钮
        this.runToolBtn.disabled = false;
    }
    
    /**
     * 更新参数表单
     */
    updateParametersForm(parameters) {
        // 清空参数表单
        this.parametersForm.innerHTML = '';
        
        // 如果没有参数，显示提示信息
        if (parameters.length === 0) {
            this.parametersForm.innerHTML = '<div class="alert alert-info">此工具没有定义参数。</div>';
            return;
        }
        
        // 创建参数表单
        parameters.forEach((param, index) => {
            const paramItem = document.createElement('div');
            paramItem.className = 'parameter-item';
            
            // 参数标签
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = param.label || param.name;
            if (param.required) {
                const requiredMark = document.createElement('span');
                requiredMark.className = 'text-danger ms-1';
                requiredMark.textContent = '*';
                label.appendChild(requiredMark);
            }
            paramItem.appendChild(label);
            
            // 参数描述
            if (param.description) {
                const description = document.createElement('div');
                description.className = 'parameter-description mb-2';
                description.textContent = param.description;
                paramItem.appendChild(description);
            }
            
            // 参数输入控件
            let input;
            switch (param.type) {
                case 'boolean':
                    // 布尔类型使用复选框
                    input = document.createElement('div');
                    input.className = 'form-check';
                    input.innerHTML = `
                        <input class="form-check-input" type="checkbox" id="param-${index}" name="${param.name}" ${param.default ? 'checked' : ''}>
                        <label class="form-check-label" for="param-${index}">
                            启用
                        </label>
                    `;
                    break;
                    
                case 'select':
                    // 选择类型使用下拉框
                    input = document.createElement('select');
                    input.className = 'form-select';
                    input.id = `param-${index}`;
                    input.name = param.name;
                    
                    // 添加选项
                    if (param.options && Array.isArray(param.options)) {
                        param.options.forEach(option => {
                            const optionEl = document.createElement('option');
                            optionEl.value = option.value;
                            optionEl.textContent = option.label || option.value;
                            if (param.default === option.value) {
                                optionEl.selected = true;
                            }
                            input.appendChild(optionEl);
                        });
                    }
                    break;
                    
                case 'textarea':
                    // 文本区域
                    input = document.createElement('textarea');
                    input.className = 'form-control';
                    input.id = `param-${index}`;
                    input.name = param.name;
                    input.rows = 3;
                    input.value = param.default || '';
                    break;
                    
                case 'number':
                    // 数字输入框
                    input = document.createElement('input');
                    input.className = 'form-control';
                    input.type = 'number';
                    input.id = `param-${index}`;
                    input.name = param.name;
                    input.value = param.default || '';
                    if (param.min !== undefined) input.min = param.min;
                    if (param.max !== undefined) input.max = param.max;
                    if (param.step !== undefined) input.step = param.step;
                    break;
                    
                default:
                    // 默认使用文本输入框
                    input = document.createElement('input');
                    input.className = 'form-control';
                    input.type = 'text';
                    input.id = `param-${index}`;
                    input.name = param.name;
                    input.value = param.default || '';
                    if (param.placeholder) input.placeholder = param.placeholder;
            }
            
            // 设置必填属性
            if (param.required && input.tagName !== 'DIV') {
                input.required = true;
            }
            
            paramItem.appendChild(input);
            this.parametersForm.appendChild(paramItem);
        });
    }
    
    /**
     * 处理创建工具
     */
    handleCreateTool() {
        const name = this.newToolName.value.trim();
        const description = this.newToolDescription.value.trim();
        const category = this.newToolCategory.value;
        const templateType = document.querySelector('input[name="templateType"]:checked').value;
        
        if (!name) {
            alert('请输入工具名称');
            return;
        }
        
        // 获取模板代码
        const templateCode = this.getTemplateCode(templateType, name, description, category);
        
        // 发送创建工具请求
        ApiClient.post('/api/custom_tools/create', {
            name: name,
            description: description,
            category: category,
            code: templateCode
        })
            .then(response => {
                if (response.success) {
                    // 隐藏模态框
                    $('#createToolModal').modal('hide');
                    
                    // 重置表单
                    document.getElementById('createToolForm').reset();
                    
                    // 重新加载工具列表
                    this.loadTools();
                    
                    // 加载新创建的工具
                    setTimeout(() => {
                        this.loadTool(response.tool_id);
                    }, 500);
                    
                    // 显示成功消息
                    this.showSuccess(`工具 ${name} 创建成功`);
                } else {
                    this.showError('创建工具失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('创建工具失败: ' + error.message);
            });
    }
    
    /**
     * 获取模板代码
     */
    getTemplateCode(templateType, name, description, category) {
        switch (templateType) {
            case 'basic':
                return `# 工具名称
TOOL_NAME = "${name}"

# 工具描述
TOOL_DESCRIPTION = "${description}"

# 工具作者
TOOL_AUTHOR = ""

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "${category}"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "param1",
        "type": "string",
        "label": "参数1",
        "description": "这是第一个参数",
        "required": True,
        "default": ""
    },
    {
        "name": "param2",
        "type": "number",
        "label": "参数2",
        "description": "这是第二个参数",
        "required": False,
        "default": 42
    }
]

def run(params):
    """工具的主函数，接收参数并返回结果"""
    # 获取参数
    param1 = params.get("param1", "")
    param2 = params.get("param2", 42)
    
    # 执行工具逻辑
    result = f"处理参数: {param1}, {param2}"
    
    # 返回结果（可以是任何可JSON序列化的对象）
    return {
        "message": "工具执行成功",
        "data": result
    }
`;
                
            case 'network':
                return `# 工具名称
TOOL_NAME = "${name}"

# 工具描述
TOOL_DESCRIPTION = "${description}"

# 工具作者
TOOL_AUTHOR = ""

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "${category}"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "ip_address",
        "type": "string",
        "label": "IP地址",
        "description": "目标设备的IP地址",
        "required": True,
        "default": ""
    },
    {
        "name": "port",
        "type": "number",
        "label": "端口",
        "description": "目标端口",
        "required": False,
        "default": 22
    },
    {
        "name": "timeout",
        "type": "number",
        "label": "超时时间(秒)",
        "description": "连接超时时间",
        "required": False,
        "default": 5
    }
]

import socket
import time

def run(params):
    """网络连接测试工具"""
    # 获取参数
    ip_address = params.get("ip_address", "")
    port = int(params.get("port", 22))
    timeout = int(params.get("timeout", 5))
    
    if not ip_address:
        return {
            "success": False,
            "message": "IP地址不能为空"
        }
    
    try:
        # 创建socket对象
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # 记录开始时间
        start_time = time.time()
        
        # 尝试连接
        result = sock.connect_ex((ip_address, port))
        
        # 计算响应时间
        response_time = time.time() - start_time
        
        # 关闭连接
        sock.close()
        
        if result == 0:
            return {
                "success": True,
                "message": f"成功连接到 {ip_address}:{port}",
                "data": {
                    "status": "open",
                    "response_time": round(response_time * 1000, 2)  # 毫秒
                }
            }
        else:
            return {
                "success": False,
                "message": f"无法连接到 {ip_address}:{port}",
                "data": {
                    "status": "closed",
                    "error_code": result
                }
            }
    except socket.timeout:
        return {
            "success": False,
            "message": f"连接 {ip_address}:{port} 超时",
            "data": {
                "status": "timeout",
                "timeout": timeout
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接错误: {str(e)}",
            "data": {
                "status": "error",
                "error": str(e)
            }
        }
`;
                
            case 'empty':
            default:
                return `# 工具名称
TOOL_NAME = "${name}"

# 工具描述
TOOL_DESCRIPTION = "${description}"

# 工具作者
TOOL_AUTHOR = ""

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "${category}"

# 工具参数定义
TOOL_PARAMETERS = [
    # 在这里定义工具参数
    # 例如：
    # {
    #     "name": "param_name",
    #     "type": "string",  # string, number, boolean, select, textarea
    #     "label": "参数显示名称",
    #     "description": "参数描述",
    #     "required": True,  # 是否必填
    #     "default": ""  # 默认值
    # }
]

def run(params):
    """工具的主函数，接收参数并返回结果"""
    # 在这里实现工具逻辑
    
    # 返回结果（可以是任何可JSON序列化的对象）
    return {
        "message": "工具执行成功",
        "data": "Hello, World!"
    }
`;
        }
    }
    
    /**
     * 保存工具
     */
    saveTool() {
        if (!this.currentTool) {
            return;
        }
        
        // 获取编辑器代码
        const code = this.editor.getValue();
        
        // 发送更新工具请求
        ApiClient.post(`/api/custom_tools/update/${this.currentTool.id}`, {
            code: code
        })
            .then(response => {
                if (response.success) {
                    // 禁用保存按钮
                    this.saveToolBtn.disabled = true;
                    
                    // 显示成功消息
                    this.showSuccess(`工具 ${this.currentTool.name} 保存成功`);
                    
                    // 重新加载工具列表
                    this.loadTools();
                } else {
                    this.showError('保存工具失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('保存工具失败: ' + error.message);
            });
    }
    
    /**
     * 删除工具
     */
    deleteTool() {
        if (!this.currentTool) {
            return;
        }
        
        // 确认删除
        if (!confirm(`确定要删除工具 ${this.currentTool.name} 吗？此操作不可恢复。`)) {
            return;
        }
        
        // 发送删除工具请求
        ApiClient.delete(`/api/custom_tools/delete/${this.currentTool.id}`)
            .then(response => {
                if (response.success) {
                    // 重置当前工具
                    this.currentTool = null;
                    this.currentToolName.textContent = '未选择工具';
                    this.editor.setValue('# 在这里编写您的自定义工具代码\n');
                    this.toolName.value = '';
                    this.toolDescription.value = '';
                    this.toolCategory.value = 'other';
                    this.toolVersion.value = '';
                    this.toolAuthor.value = '';
                    
                    // 禁用按钮
                    this.saveToolBtn.disabled = true;
                    this.deleteToolBtn.disabled = true;
                    this.runToolBtn.disabled = true;
                    
                    // 清空参数表单
                    this.parametersForm.innerHTML = '<div class="alert alert-info">请先选择一个工具，或切换到编辑器标签页定义参数。</div>';
                    
                    // 重新加载工具列表
                    this.loadTools();
                    
                    // 显示成功消息
                    this.showSuccess(`工具删除成功`);
                } else {
                    this.showError('删除工具失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('删除工具失败: ' + error.message);
            });
    }
    
    /**
     * 运行工具
     */
    runTool() {
        if (!this.currentTool) {
            return;
        }
        
        // 收集参数
        const params = {};
        const paramElements = this.parametersForm.querySelectorAll('input, select, textarea');
        paramElements.forEach(element => {
            if (element.type === 'checkbox') {
                params[element.name] = element.checked;
            } else {
                params[element.name] = element.value;
            }
        });
        
        // 清空输出区域
        this.toolOutput.textContent = '正在运行工具...';
        
        // 发送运行工具请求
        ApiClient.post(`/api/custom_tools/run/${this.currentTool.id}`, params)
            .then(response => {
                if (response.success) {
                    // 显示结果
                    this.displayToolResult(response.result);
                } else {
                    this.toolOutput.textContent = `运行失败: ${response.message}`;
                }
            })
            .catch(error => {
                this.toolOutput.textContent = `运行错误: ${error.message}`;
            });
    }
    
    /**
     * 显示工具运行结果
     */
    displayToolResult(result) {
        // 将结果转换为格式化的JSON字符串
        const formattedResult = JSON.stringify(result, null, 2);
        
        // 显示结果
        this.toolOutput.textContent = formattedResult;
    }
    
    /**
     * 显示错误消息
     */
    showError(message) {
        console.error(message);
        alert(message);
    }
    
    /**
     * 显示成功消息
     */
    showSuccess(message) {
        console.log(message);
        // 这里可以使用更友好的提示，如Toast通知
        alert(message);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.customToolsManager = new CustomToolsManager();
});