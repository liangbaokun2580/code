class DevelopmentManager {
    constructor() {
        this.editor = null;
        this.isRunning = false;
        this.defaultOutputPlaceholder = `
            <div class="output-placeholder">
            </div>
        `;

        this.initializeElements();
        this.initializeCodeEditor();
        this.bindEvents();
        this.loadExampleCode();
        this.loadDeviceTypes();
    }

    initializeElements() {
        this.codeEditor = document.getElementById('codeEditor');
        this.outputArea = document.getElementById('outputContent');
        this.runButton = document.getElementById('runButton');
        this.clearButton = document.getElementById('clearButton');
        this.formatButton = document.getElementById('formatButton');
        this.saveButton = document.getElementById('saveButton');
        this.loadButton = document.getElementById('loadButton');
        this.executionStatus = document.getElementById('codeStatus');
        this.executionTime = document.getElementById('executionTime');
        this.deviceTypesList = document.getElementById('deviceTypes');
    }

    initializeCodeEditor() {
        if (!this.codeEditor || typeof CodeMirror === 'undefined') {
            return;
        }

        this.editor = CodeMirror.fromTextArea(this.codeEditor, {
            mode: 'python',
            theme: 'monokai',
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            lineWrapping: false,
            extraKeys: {
                Tab: (cm) => {
                    if (cm.somethingSelected()) {
                        cm.indentSelection('add');
                    } else {
                        cm.replaceSelection('    ');
                    }
                },
                'Shift-Tab': (cm) => cm.indentSelection('subtract'),
                'Ctrl-/': 'toggleComment',
                'Ctrl-Enter': () => this.runCode()
            }
        });

        this.editor.setSize('100%', '100%');

        const wrapper = this.editor.getWrapperElement();
        wrapper.style.fontSize = '14px';
        wrapper.style.lineHeight = '1.4';

        this.editor.on('change', () => this.updateStatus());

        setTimeout(() => {
            this.refreshEditor();
            this.editor.focus();
        }, 50);

        window.addEventListener('resize', () => {
            setTimeout(() => this.refreshEditor(), 100);
        });
    }

    refreshEditor() {
        if (!this.editor) {
            return;
        }

        const cursor = this.editor.getCursor();
        this.editor.setSize('100%', '100%');
        this.editor.refresh();
        this.editor.setCursor(cursor);
    }

    bindEvents() {
        if (this.runButton) {
            this.runButton.addEventListener('click', () => this.runCode());
        }
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => this.clearEditor());
        }
        if (this.formatButton) {
            this.formatButton.addEventListener('click', () => this.formatCode());
        }
        if (this.saveButton) {
            this.saveButton.addEventListener('click', () => this.saveCode());
        }
        if (this.loadButton) {
            this.loadButton.addEventListener('click', () => this.loadCode());
        }

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                setTimeout(() => this.refreshEditor(), 100);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.runCode();
            }
        });
    }

    async runCode() {
        if (!this.editor) {
            Utils.showNotification('编辑器尚未初始化', 'warning');
            return;
        }

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

        try {
            const result = await ApiClient.post('/api/develop/run', {
                code,
                timeout: 30
            });

            const executionTime = Date.now() - startTime;
            const isSuccess = result.success && (result.return_code === undefined || result.return_code === 0);

            if (isSuccess) {
                this.addOutput('执行成功', 'success');
                if (result.output) {
                    this.addOutput(result.output, 'output');
                }
                if (result.error) {
                    this.addOutput(result.error, 'warning');
                }
            } else {
                this.addOutput('执行失败', 'error');
                this.addOutput(result.error || '执行返回非零状态码', 'error');
                if (result.traceback) {
                    this.addOutput(result.traceback, 'traceback');
                }
            }

            this.updateExecutionStatus(isSuccess, executionTime);
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

    clearEditor() {
        if (!this.editor) {
            return;
        }

        this.editor.setValue('');
        this.clearOutput();
        Utils.showNotification('编辑器已清空', 'success');
    }

    clearOutput() {
        if (!this.outputArea) {
            return;
        }

        this.outputArea.innerHTML = this.defaultOutputPlaceholder;

        if (this.executionStatus) {
            this.executionStatus.textContent = '就绪';
            this.executionStatus.className = 'badge bg-secondary';
        }

        if (this.executionTime) {
            this.executionTime.textContent = '0ms';
        }
    }

    clearOutputContent() {
        if (this.outputArea) {
            this.outputArea.innerHTML = '';
        }
    }

    addOutput(content, type = 'output') {
        if (!this.outputArea) {
            return;
        }

        if (this.outputArea.querySelector('.output-placeholder')) {
            this.clearOutputContent();
        }

        const outputDiv = document.createElement('div');
        outputDiv.className = `output-line output-${type}`;

        const timestamp = new Date().toLocaleTimeString();
        const iconMap = {
            info: 'bi bi-info-circle',
            success: 'bi bi-check-circle',
            error: 'bi bi-exclamation-circle',
            warning: 'bi bi-exclamation-triangle',
            result: 'bi bi-arrow-right-circle',
            output: 'bi bi-terminal',
            traceback: 'bi bi-bug'
        };
        const iconClass = iconMap[type] || iconMap.output;

        outputDiv.innerHTML = `
            <span class="output-timestamp">[${timestamp}]</span>
            <span class="output-icon"><i class="${iconClass}"></i></span>
            <span class="output-content">${this.escapeHtml(String(content))}</span>
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
        if (!this.runButton) {
            return;
        }

        if (isRunning) {
            this.runButton.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>执行中...';
            this.runButton.disabled = true;
        } else {
            this.runButton.innerHTML = '<i class="bi bi-play me-1"></i>运行代码';
            this.runButton.disabled = false;
        }
    }

    updateExecutionStatus(success, executionTime) {
        if (this.executionStatus) {
            this.executionStatus.textContent = success ? '执行成功' : '执行失败';
            this.executionStatus.className = success ? 'badge bg-success' : 'badge bg-danger';
        }

        if (this.executionTime) {
            this.executionTime.textContent = `${executionTime}ms`;
        }
    }

    updateStatus() {
        if (!this.editor) {
            return;
        }

        const cursor = this.editor.getCursor();
        console.debug(`Cursor: ${cursor.line + 1}:${cursor.ch + 1}`);
    }

    formatCode() {
        if (!this.editor) {
            return;
        }

        try {
            const formattedCode = this.simpleFormatPython(this.editor.getValue());
            this.editor.setValue(formattedCode);
            Utils.showNotification('代码格式化完成', 'success');
        } catch (error) {
            Utils.showNotification('代码格式化失败', 'error');
        }
    }

    simpleFormatPython(code) {
        const lines = code.split('\n');
        let indentLevel = 0;
        const formattedLines = [];

        for (let line of lines) {
            line = line.trim();
            if (!line) {
                formattedLines.push('');
                continue;
            }

            if (/^(except|elif|else|finally)\b/.test(line)) {
                indentLevel = Math.max(0, indentLevel - 1);
            }

            formattedLines.push('    '.repeat(indentLevel) + line);

            if (line.endsWith(':')) {
                indentLevel += 1;
            }
        }

        return formattedLines.join('\n');
    }

    saveCode() {
        if (!this.editor) {
            return;
        }

        const code = this.editor.getValue();
        const filename = prompt('请输入文件名:', 'network_script.py');

        if (!filename) {
            return;
        }

        const blob = new Blob([code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        Utils.showNotification('代码已保存', 'success');
    }

    loadCode() {
        if (!this.editor) {
            return;
        }

        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.py,.txt';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) {
                return;
            }

            const reader = new FileReader();
            reader.onload = (event) => {
                this.editor.setValue(event.target.result);
                Utils.showNotification('代码已加载', 'success');
            };
            reader.readAsText(file);
        };
        input.click();
    }

    loadExample(exampleType) {
        if (!this.editor) {
            return;
        }

        const examples = {
            basic: `print("Hello, world!")\nfor i in range(3):\n    print(f"step {i + 1}")`,
            config: `device = {\n    "hostname": "switch01",\n    "ip": "192.168.1.10",\n    "role": "access"\n}\n\nprint("准备配置设备:", device["hostname"])`,
            monitor: `devices = [\n    {"name": "router01", "status": "online"},\n    {"name": "switch02", "status": "offline"}\n]\n\nfor device in devices:\n    print(f"{device['name']}: {device['status']}")`,
            batch: `hosts = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]\nresults = []\n\nfor host in hosts:\n    results.append({"host": host, "result": "ok"})\n\nprint(results)`
        };

        if (examples[exampleType]) {
            this.editor.setValue(examples[exampleType]);
            Utils.showNotification(`已加载 ${exampleType} 示例代码`, 'success');
        }
    }

    loadExampleCode() {
        this.loadExample('basic');
    }

    loadDeviceTypes() {
        if (!this.deviceTypesList) {
            return;
        }

        const deviceTypes = [
            { name: 'Cisco IOS', description: '路由器 / 交换机' },
            { name: 'Huawei VRP', description: '企业网络设备' },
            { name: 'H3C Comware', description: '园区与数据中心' },
            { name: 'Juniper JunOS', description: '路由与安全设备' }
        ];

        this.deviceTypesList.innerHTML = deviceTypes.map((device) => `
            <div class="device-item mb-2 p-2 border rounded">
                <div class="fw-semibold">${device.name}</div>
                <small class="text-muted">${device.description}</small>
            </div>
        `).join('');
    }
}

function runCode() {
    window.developmentManager?.runCode();
}

function clearCode() {
    window.developmentManager?.clearEditor();
}

function clearOutput() {
    window.developmentManager?.clearOutput();
}

function formatCode() {
    window.developmentManager?.formatCode();
}

function saveCode() {
    window.developmentManager?.saveCode();
}

function loadCode() {
    window.developmentManager?.loadCode();
}

function loadExample(type) {
    window.developmentManager?.loadExample(type);
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof CodeMirror === 'undefined') {
        console.error('CodeMirror 未加载');
        Utils.showNotification('代码编辑器加载失败', 'error');
        return;
    }

    if (!window.developmentManager) {
        window.developmentManager = new DevelopmentManager();
    }

    setTimeout(() => {
        window.developmentManager?.addOutput('欢迎使用 SDK 开发环境', 'info');
        window.developmentManager?.addOutput('按 Ctrl+Enter 可直接运行代码', 'info');
    }, 200);
});
