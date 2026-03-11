// 开发页面JavaScript文件

class DevelopmentManager {
    constructor() {
        this.editor = null;
        this.isRunning = false;
        this.currentExecution = null;
        this.initializeElements();
        this.initializeCodeEditor();
        this.bindEvents();
        this.loadExampleCode();
    }
    
    initializeElements() {
        this.codeEditor = document.getElementById('codeEditor');
        this.outputArea = document.getElementById('outputArea');
        this.runButton = document.getElementById('runButton');
        this.clearButton = document.getElementById('clearButton');
        this.formatButton = document.getElementById('formatButton');
        this.saveButton = document.getElementById('saveButton');
        this.loadButton = document.getElementById('loadButton');
        this.executionStatus = document.getElementById('executionStatus');
        this.executionTime = document.getElementById('executionTime');
        
        // 设备类型列表
        this.deviceTypesList = document.getElementById('deviceTypesList');
        
        // 示例代码按钮
        this.exampleButtons = document.querySelectorAll('.example-btn');
        
        // API文档链接
        this.apiDocLinks = document.querySelectorAll('.api-doc-link');
    }
    
    initializeCodeEditor() {
        // 使用CodeMirror初始化代码编辑器
        this.editor = CodeMirror.fromTextArea(this.codeEditor, {
            mode: 'python',
            theme: 'monokai',
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            foldGutter: true,
            gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
            lineWrapping: false,
            extraKeys: {
                'Tab': function(cm) {
                    if (cm.somethingSelected()) {
                        cm.indentSelection('add');
                    } else {
                        cm.replaceSelection('    ');
                    }
                },
                'Shift-Tab': function(cm) {
                    cm.indentSelection('subtract');
                },
                'F11': function(cm) {
                    cm.setOption('fullScreen', !cm.getOption('fullScreen'));
                },
                'Esc': function(cm) {
                    if (cm.getOption('fullScreen')) cm.setOption('fullScreen', false);
                },
                'Ctrl-/': 'toggleComment',
                'Ctrl-Enter': () => this.runCode()
            }
        });
        
        // 设置编辑器大小 - 自适应容器高度
        this.editor.setSize('100%', '100%');
        
        // 强制设置行高以确保光标对齐
        const wrapper = this.editor.getWrapperElement();
        wrapper.style.fontSize = '14px';
        wrapper.style.lineHeight = '1.4';
        
        // 确保编辑器正确渲染
        setTimeout(() => {
            this.editor.refresh();
            this.editor.focus();
        }, 50);

        
        // 监听编辑器变化
        this.editor.on('change', () => {
            this.updateStatus();
        });
        
        // 监听窗口大小变化，调整编辑器大小
        window.addEventListener('resize', () => {
            setTimeout(() => {
                this.refreshEditor();
            }, 100);
        });
        
        // 强制刷新编辑器以修复渲染问题
        setTimeout(() => {
            this.refreshEditor();
        }, 500);
    }
    
    refreshEditor() {
        if (!this.editor) return;
        
        // 保存当前光标位置
        const cursor = this.editor.getCursor();
        
        // 强制重新计算编辑器尺寸
        this.editor.setSize('100%', '100%');
        this.editor.refresh();
        
        // 恢复光标位置，避免重复渲染
        setTimeout(() => {
            this.editor.setCursor(cursor);
            this.editor.focus();
        }, 10);
    }
    
    bindEvents() {
        // 工具栏按钮事件
        this.runButton.addEventListener('click', () => this.runCode());
        this.clearButton.addEventListener('click', () => this.clearOutput());
        this.formatButton.addEventListener('click', () => this.formatCode());
        this.saveButton.addEventListener('click', () => this.saveCode());
        this.loadButton.addEventListener('click', () => this.loadCode());
        
        // 页面可见性变化时刷新编辑器
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.editor) {
                setTimeout(() => {
                    this.refreshEditor();
                }, 100);
            }
        });
        
        // 示例代码按钮事件
        this.exampleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const exampleType = e.target.dataset.example;
                this.loadExample(exampleType);
            });
        });
        
        // API文档链接事件
        this.apiDocLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const docType = e.target.dataset.doc;
                this.showApiDocumentation(docType);
            });
        });
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.runCode();
            }
        });
    }
    
    async runCode() {
        if (this.isRunning) {
            Utils.showNotification('代码正在执行中，请稍候', 'warning');
            return;
        }
        
        const code = this.editor.getValue().trim();
        if (!code) {
            Utils.showNotification('请输入代码', 'warning');
            return;
        }
        
        this.isRunning = true;
        this.updateRunButton(true);
        this.clearOutput();
        this.addOutput('开始执行代码...', 'info');
        
        const startTime = Date.now();

        return;
        
        try {
            const response = await ApiClient.post('/api/develop/run', {
                code: code,
                timeout: 30
            });
            
            const result = response.data;
            const executionTime = Date.now() - startTime;
            
            if (result.success) {
                this.addOutput('执行成功', 'success');
                if (result.output) {
                    this.addOutput(result.output, 'output');
                }
                if (result.return_value !== undefined) {
                    this.addOutput(`返回值: ${JSON.stringify(result.return_value, null, 2)}`, 'result');
                }
            } else {
                this.addOutput('执行失败', 'error');
                this.addOutput(result.error, 'error');
                if (result.traceback) {
                    this.addOutput('详细错误信息:', 'error');
                    this.addOutput(result.traceback, 'traceback');
                }
            }
            
            this.updateExecutionStatus(result.success, executionTime);
            
        } catch (error) {
            const executionTime = Date.now() - startTime;
            this.addOutput('网络错误', 'error');
            this.addOutput(error.message, 'error');
            this.updateExecutionStatus(false, executionTime);
            Utils.showNotification('代码执行失败', 'error');
        } finally {
            this.isRunning = false;
            this.updateRunButton(false);
        }
    }
    
    clearOutput() {
        this.outputArea.innerHTML = '';
        this.executionStatus.textContent = '就绪';
        this.executionStatus.className = 'badge bg-secondary';
        this.executionTime.textContent = '0ms';
    }
    
    addOutput(content, type = 'output') {
        const outputDiv = document.createElement('div');
        outputDiv.className = `output-line output-${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        let icon = '';
        switch (type) {
            case 'info':
                icon = '<i class="fas fa-info-circle"></i>';
                break;
            case 'success':
                icon = '<i class="fas fa-check-circle"></i>';
                break;
            case 'error':
                icon = '<i class="fas fa-exclamation-circle"></i>';
                break;
            case 'warning':
                icon = '<i class="fas fa-exclamation-triangle"></i>';
                break;
            case 'result':
                icon = '<i class="fas fa-arrow-right"></i>';
                break;
            default:
                icon = '<i class="fas fa-terminal"></i>';
        }
        
        outputDiv.innerHTML = `
            <span class="output-timestamp">[${timestamp}]</span>
            <span class="output-icon">${icon}</span>
            <span class="output-content">${this.escapeHtml(content)}</span>
        `;
        
        this.outputArea.appendChild(outputDiv);
        this.outputArea.scrollTop = this.outputArea.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/\n/g, '<br>');
    }
    
    updateRunButton(isRunning) {
        if (isRunning) {
            this.runButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>执行中...';
            this.runButton.disabled = true;
        } else {
            this.runButton.innerHTML = '<i class="fas fa-play me-2"></i>运行代码';
            this.runButton.disabled = false;
        }
    }
    
    updateExecutionStatus(success, executionTime) {
        if (success) {
            this.executionStatus.textContent = '执行成功';
            this.executionStatus.className = 'badge bg-success';
        } else {
            this.executionStatus.textContent = '执行失败';
            this.executionStatus.className = 'badge bg-danger';
        }
        
        this.executionTime.textContent = `${executionTime}ms`;
    }
    
    updateStatus() {
        const lineCount = this.editor.lineCount();
        const selection = this.editor.getSelection();
        const cursor = this.editor.getCursor();
        
        // 可以在这里更新状态栏信息
        console.log(`Lines: ${lineCount}, Cursor: ${cursor.line + 1}:${cursor.ch + 1}`);
    }
    
    formatCode() {
        try {
            const code = this.editor.getValue();
            // 简单的Python代码格式化（实际项目中可能需要更复杂的格式化器）
            const formattedCode = this.simpleFormatPython(code);
            this.editor.setValue(formattedCode);
            Utils.showNotification('代码格式化完成', 'success');
        } catch (error) {
            Utils.showNotification('代码格式化失败', 'error');
        }
    }
    
    simpleFormatPython(code) {
        // 简单的Python代码格式化
        const lines = code.split('\n');
        let indentLevel = 0;
        const formattedLines = [];
        
        for (let line of lines) {
            line = line.trim();
            if (!line) {
                formattedLines.push('');
                continue;
            }
            
            // 减少缩进
            if (line.match(/^(except|elif|else|finally)/) || line === 'pass') {
                indentLevel = Math.max(0, indentLevel - 1);
            }
            
            // 添加缩进
            const indentedLine = '    '.repeat(indentLevel) + line;
            formattedLines.push(indentedLine);
            
            // 增加缩进
            if (line.endsWith(':')) {
                indentLevel++;
            }
        }
        
        return formattedLines.join('\n');
    }
    
    saveCode() {
        const code = this.editor.getValue();
        const filename = prompt('请输入文件名:', 'network_script.py');
        
        if (filename) {
            const blob = new Blob([code], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            Utils.showNotification('代码已保存', 'success');
        }
    }
    
    loadCode() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.py,.txt';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.editor.setValue(e.target.result);
                    Utils.showNotification('代码已加载', 'success');
                };
                reader.readAsText(file);
            }
        };
        
        input.click();
    }
    
    loadExample(exampleType) {
        const examples = {
            basic: `# 基础网络设备操作示例
from network_sdk import NetworkManager

# 创建网络管理器
manager = NetworkManager()

# 添加设备
device = manager.add_device(
    device_id='switch01',
    device_type='switch',
    host='192.168.1.10',
    username='admin',
    password='password'
)

# 连接设备
if device.connect():
    print(f"成功连接到设备 {device.device_id}")
    
    # 获取设备状态
    status = device.get_status()
    print(f"设备状态: {status}")
    
    # 获取接口信息
    interfaces = device.get_interfaces()
    for interface in interfaces:
        print(f"接口 {interface['name']}: {interface['status']}")
    
    # 断开连接
    device.disconnect()
else:
    print("连接设备失败")
`,
            
            config: `# 设备配置示例
from network_sdk import NetworkManager

manager = NetworkManager()

# 连接到交换机
switch = manager.get_device('switch01')
if switch and switch.connect():
    
    # 配置VLAN
    vlan_config = {
        'vlan_id': 100,
        'name': 'Production',
        'description': 'Production Network'
    }
    
    result = switch.configure_vlan(vlan_config)
    if result['success']:
        print("VLAN配置成功")
    else:
        print(f"VLAN配置失败: {result['error']}")
    
    # 配置接口
    interface_config = {
        'interface': 'GigabitEthernet0/1',
        'mode': 'access',
        'vlan': 100,
        'description': 'Server Port'
    }
    
    result = switch.configure_interface(interface_config)
    if result['success']:
        print("接口配置成功")
    
    # 保存配置
    switch.save_config()
    switch.disconnect()
`,
            
            monitoring: `# 网络监控示例
from network_sdk import NetworkManager
import time

manager = NetworkManager()

# 监控所有设备
def monitor_network():
    devices = manager.get_all_devices()
    
    for device in devices:
        if device.connect():
            # 检查设备状态
            status = device.get_status()
            print(f"设备 {device.device_id}: {status['status']}")
            
            # 检查CPU和内存使用率
            resources = device.get_resource_usage()
            print(f"  CPU: {resources['cpu']}%")
            print(f"  内存: {resources['memory']}%")
            
            # 检查接口状态
            interfaces = device.get_interfaces()
            down_interfaces = [i for i in interfaces if i['status'] == 'down']
            if down_interfaces:
                print(f"  警告: {len(down_interfaces)} 个接口处于down状态")
            
            device.disconnect()
        else:
            print(f"设备 {device.device_id}: 连接失败")

# 执行监控
monitor_network()
`,
            
            batch: `# 批量操作示例
from network_sdk import NetworkManager

manager = NetworkManager()

# 批量配置多个设备
devices_config = [
    {
        'device_id': 'switch01',
        'host': '192.168.1.10',
        'config': {
            'vlans': [{'id': 100, 'name': 'Production'}],
            'interfaces': [{
                'name': 'GigabitEthernet0/1',
                'vlan': 100,
                'description': 'Server Port'
            }]
        }
    },
    {
        'device_id': 'switch02',
        'host': '192.168.1.11',
        'config': {
            'vlans': [{'id': 200, 'name': 'Development'}],
            'interfaces': [{
                'name': 'GigabitEthernet0/1',
                'vlan': 200,
                'description': 'Dev Port'
            }]
        }
    }
]

# 批量执行配置
results = manager.batch_configure(devices_config)

for device_id, result in results.items():
    if result['success']:
        print(f"设备 {device_id}: 配置成功")
    else:
        print(f"设备 {device_id}: 配置失败 - {result['error']}")

# 批量备份配置
backup_results = manager.batch_backup(['switch01', 'switch02'])
print(f"备份完成，共备份 {len(backup_results)} 个设备")
`
        };
        
        if (examples[exampleType]) {
            this.editor.setValue(examples[exampleType]);
            Utils.showNotification(`已加载${exampleType}示例代码`, 'success');
        }
    }
    
    loadExampleCode() {
        // 默认加载基础示例
        this.loadExample('basic');
    }
    
    showApiDocumentation(docType) {
        const docs = {
            device: `# 设备管理API文档

## NetworkDevice 类

### 方法:
- connect(): 连接到设备
- disconnect(): 断开设备连接
- get_status(): 获取设备状态
- get_interfaces(): 获取接口信息
- configure_vlan(config): 配置VLAN
- configure_interface(config): 配置接口
- execute_command(command): 执行命令
- save_config(): 保存配置
- backup_config(): 备份配置

### 属性:
- device_id: 设备ID
- device_type: 设备类型
- host: 设备IP地址
- status: 连接状态`,
            
            config: `# 配置管理API文档

## 配置格式

### VLAN配置:
{
    'vlan_id': 100,
    'name': 'VLAN名称',
    'description': '描述信息'
}

### 接口配置:
{
    'interface': '接口名称',
    'mode': 'access|trunk',
    'vlan': VLAN_ID,
    'description': '接口描述'
}

### 路由配置:
{
    'network': '目标网络',
    'mask': '子网掩码',
    'gateway': '网关地址'
}`
        };
        
        if (docs[docType]) {
            // 在新窗口中显示文档
            const docWindow = window.open('', '_blank', 'width=800,height=600');
            docWindow.document.write(`
                <html>
                <head>
                    <title>API文档 - ${docType}</title>
                    <style>
                        body { font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
                        pre { background: #2d2d30; padding: 15px; border-radius: 5px; overflow: auto; }
                    </style>
                </head>
                <body>
                    <pre>${docs[docType]}</pre>
                </body>
                </html>
            `);
        }
    }
}

// 全局函数
function runCode() {
    if (window.developmentManager) {
        window.developmentManager.runCode();
    }
}

function clearOutput() {
    if (window.developmentManager) {
        window.developmentManager.clearOutput();
    }
}

function formatCode() {
    if (window.developmentManager) {
        window.developmentManager.formatCode();
    }
}

function saveCode() {
    if (window.developmentManager) {
        window.developmentManager.saveCode();
    }
}

function loadCode() {
    if (window.developmentManager) {
        window.developmentManager.loadCode();
    }
}

function loadExample(type) {
    if (window.developmentManager) {
        window.developmentManager.loadExample(type);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查CodeMirror是否已加载
    if (typeof CodeMirror === 'undefined') {
        console.error('CodeMirror未加载，请检查CDN链接');
        Utils.showNotification('代码编辑器加载失败', 'error');
        return;
    }
    
    // 将实例暴露到全局作用域
    if (typeof window.developmentManager === 'undefined') {
        window.developmentManager = new DevelopmentManager();
    }
    
    // 显示欢迎信息
    setTimeout(() => {
        if (window.developmentManager) {
            window.developmentManager.addOutput('欢迎使用网络设备SDK开发环境！', 'info');
            window.developmentManager.addOutput('按Ctrl+Enter运行代码，或点击运行按钮', 'info');
        }
    }, 500);
});