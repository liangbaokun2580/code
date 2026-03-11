/**
 * 命令行页面的JavaScript功能
 */

class CommandLineManager {
    constructor() {
        // DOM元素
        this.terminalOutput = document.getElementById('terminalOutput');
        this.commandInput = document.getElementById('commandInput');
        this.deviceSelect = document.getElementById('deviceSelect');
        this.historyList = document.getElementById('historyList');
        this.favoritesList = document.getElementById('favoritesList');
        this.sessionsList = document.getElementById('sessionsList');
        this.deviceInfo = document.getElementById('deviceInfo');
        this.connectBtn = document.getElementById('connectBtn');
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.saveCommandBtn = document.getElementById('saveCommandBtn');
        this.createSessionBtn = document.getElementById('createSessionBtn');
        
        // 状态变量
        this.currentDevice = null;
        this.isConnected = false;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.sessions = [];
        this.favorites = [];
        this.sessionId = null;
        
        // 初始化
        this.init();
    }
    
    /**
     * 初始化命令行管理器
     */
    init() {
        // 绑定事件
        this.bindEvents();
        
        // 加载设备列表
        this.loadDevices();
        
        // 加载命令历史
        this.loadCommandHistory();
        
        // 加载收藏命令
        this.loadFavoriteCommands();
        
        // 加载会话列表
        this.loadSessions();
        
        // 显示欢迎消息
        this.showWelcomeMessage();
        
        // 处理URL参数
        this.handleUrlParams();
    }
    
    /**
     * 绑定事件处理函数
     */
    bindEvents() {
        // 命令输入框事件
        this.commandInput.addEventListener('keydown', this.handleCommandInputKeydown.bind(this));
        
        // 设备选择事件
        this.deviceSelect.addEventListener('change', this.handleDeviceChange.bind(this));
        
        // 按钮点击事件
        this.connectBtn.addEventListener('click', this.connectDevice.bind(this));
        this.disconnectBtn.addEventListener('click', this.disconnectDevice.bind(this));
        this.clearBtn.addEventListener('click', this.clearTerminal.bind(this));
        this.saveCommandBtn.addEventListener('click', this.showSaveCommandModal.bind(this));
        
        // 如果存在创建会话按钮，绑定事件
        if (this.createSessionBtn) {
            this.createSessionBtn.addEventListener('click', this.showCreateSessionModal.bind(this));
        }
        
        // 保存命令表单提交
        document.getElementById('saveCommandForm').addEventListener('submit', this.saveCommand.bind(this));
        
        // 连接设备表单提交
        document.getElementById('connectDeviceForm').addEventListener('submit', this.handleConnectDeviceForm.bind(this));
        
        // 创建会话表单提交
        const createSessionForm = document.getElementById('createSessionForm');
        if (createSessionForm) {
            createSessionForm.addEventListener('submit', this.handleCreateSessionForm.bind(this));
        }
    }
    
    /**
     * 加载设备列表
     */
    loadDevices() {
        // 清空设备选择框
        this.deviceSelect.innerHTML = '<option value="">选择设备...</option>';
        
        // 发送API请求获取设备列表
        ApiClient.get('/api/command_line/devices')
            .then(response => {
                if (response.success) {
                    // 添加设备到选择框
                    response.devices.forEach(device => {
                        const option = document.createElement('option');
                        option.value = device.id;
                        option.textContent = `${device.name} (${device.ip_address})`;
                        option.dataset.type = device.device_type;
                        option.dataset.ip = device.ip_address;
                        this.deviceSelect.appendChild(option);
                    });
                } else {
                    this.showError('加载设备列表失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('加载设备列表失败: ' + error.message);
            });
    }
    
    /**
     * 处理设备选择变化
     */
    handleDeviceChange(event) {
        const selectedOption = this.deviceSelect.options[this.deviceSelect.selectedIndex];
        if (selectedOption.value) {
            this.currentDevice = {
                id: selectedOption.value,
                name: selectedOption.textContent,
                type: selectedOption.dataset.type,
                ip: selectedOption.dataset.ip
            };
            
            // 更新设备信息显示
            this.deviceInfo.textContent = `设备: ${this.currentDevice.name} | 类型: ${this.currentDevice.type} | IP: ${this.currentDevice.ip}`;
            this.connectBtn.disabled = false;
        } else {
            this.currentDevice = null;
            this.deviceInfo.textContent = '未选择设备';
            this.connectBtn.disabled = true;
        }
    }
    
    /**
     * 连接到设备
     */
    connectDevice() {
        if (!this.currentDevice) {
            this.showError('请先选择一个设备');
            return;
        }
        
        // 显示连接模态框
        $('#deviceConnectModal').modal('show');
    }
    
    /**
     * 处理连接设备表单提交
     */
    handleConnectDeviceForm(event) {
        event.preventDefault();
        
        const username = document.getElementById('deviceUsername').value;
        const password = document.getElementById('devicePassword').value;
        const deviceType = document.getElementById('deviceType').value;
        
        // 隐藏模态框
        $('#deviceConnectModal').modal('hide');
        
        // 显示连接中消息
        this.appendToTerminal('正在连接到设备 ' + this.currentDevice.name + '...', 'info');
        
        // 发送连接请求
        ApiClient.post('/api/command_line/connect', {
            device_id: this.currentDevice.id,
            username: username,
            password: password,
            device_type: deviceType
        })
            .then(response => {
                if (response.success) {
                    this.isConnected = true;
                    this.sessionId = response.session_id;
                    this.appendToTerminal('成功连接到设备 ' + this.currentDevice.name, 'success');
                    this.appendToTerminal(response.welcome_message || '', 'output-text');
                    
                    // 更新UI状态
                    this.updateConnectionState(true);
                    
                    // 聚焦到命令输入框
                    this.commandInput.focus();
                } else {
                    this.showError('连接失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('连接失败: ' + error.message);
            });
    }
    
    /**
     * 断开设备连接
     */
    disconnectDevice() {
        if (!this.isConnected) {
            return;
        }
        
        // 发送断开连接请求
        ApiClient.post('/api/command_line/disconnect', {
            session_id: this.sessionId
        })
            .then(response => {
                if (response.success) {
                    this.isConnected = false;
                    this.sessionId = null;
                    this.appendToTerminal('已断开与设备 ' + this.currentDevice.name + ' 的连接', 'info');
                    
                    // 更新UI状态
                    this.updateConnectionState(false);
                } else {
                    this.showError('断开连接失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('断开连接失败: ' + error.message);
            });
    }
    
    /**
     * 更新连接状态UI
     */
    updateConnectionState(isConnected) {
        this.connectBtn.disabled = isConnected;
        this.disconnectBtn.disabled = !isConnected;
        this.deviceSelect.disabled = isConnected;
        this.commandInput.disabled = !isConnected;
        
        if (isConnected) {
            this.commandInput.placeholder = '输入命令...';
        } else {
            this.commandInput.placeholder = '请先连接设备...';
        }
    }
    
    /**
     * 处理命令输入框按键事件
     */
    handleCommandInputKeydown(event) {
        // 如果未连接，不处理
        if (!this.isConnected) {
            return;
        }
        
        // 处理上下键浏览历史命令
        if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.navigateHistory(-1);
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.navigateHistory(1);
        }
        // 处理Tab键自动完成
        else if (event.key === 'Tab') {
            event.preventDefault();
            this.autocompleteCommand();
        }
        // 处理Enter键执行命令
        else if (event.key === 'Enter') {
            event.preventDefault();
            this.executeCommand();
        }
    }
    
    /**
     * 浏览命令历史
     */
    navigateHistory(direction) {
        if (this.commandHistory.length === 0) {
            return;
        }
        
        this.historyIndex += direction;
        
        // 确保索引在有效范围内
        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex >= this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length - 1;
        }
        
        // 设置输入框值为历史命令
        this.commandInput.value = this.commandHistory[this.historyIndex];
        
        // 将光标移到末尾
        setTimeout(() => {
            this.commandInput.selectionStart = this.commandInput.selectionEnd = this.commandInput.value.length;
        }, 0);
    }
    
    /**
     * 命令自动完成
     */
    autocompleteCommand() {
        const command = this.commandInput.value.trim();
        if (!command) return;
        
        // 发送自动完成请求
        ApiClient.post('/api/command_line/autocomplete', {
            session_id: this.sessionId,
            command: command
        })
            .then(response => {
                if (response.success && response.suggestions && response.suggestions.length > 0) {
                    // 如果只有一个建议，直接填充
                    if (response.suggestions.length === 1) {
                        this.commandInput.value = response.suggestions[0];
                        // 将光标移到末尾
                        setTimeout(() => {
                            this.commandInput.selectionStart = this.commandInput.selectionEnd = this.commandInput.value.length;
                        }, 0);
                    }
                    // 否则显示建议列表
                    else {
                        this.showAutocompleteSuggestions(response.suggestions);
                    }
                }
            })
            .catch(error => {
                console.error('自动完成失败:', error);
            });
    }
    
    /**
     * 显示自动完成建议
     */
    showAutocompleteSuggestions(suggestions) {
        // 移除现有的建议列表
        const existingSuggestions = document.querySelector('.autocomplete-suggestions');
        if (existingSuggestions) {
            existingSuggestions.remove();
        }
        
        // 创建建议列表容器
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'autocomplete-suggestions';
        
        // 添加建议项
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'autocomplete-suggestion';
            item.textContent = suggestion;
            item.addEventListener('click', () => {
                this.commandInput.value = suggestion;
                suggestionsContainer.remove();
                this.commandInput.focus();
            });
            suggestionsContainer.appendChild(item);
        });
        
        // 定位并添加到页面
        const inputRect = this.commandInput.getBoundingClientRect();
        suggestionsContainer.style.top = (inputRect.bottom + window.scrollY) + 'px';
        suggestionsContainer.style.left = (inputRect.left + window.scrollX) + 'px';
        suggestionsContainer.style.width = inputRect.width + 'px';
        
        document.body.appendChild(suggestionsContainer);
        
        // 点击其他地方关闭建议列表
        document.addEventListener('click', function closeAutocomplete(e) {
            if (!suggestionsContainer.contains(e.target) && e.target !== this.commandInput) {
                suggestionsContainer.remove();
                document.removeEventListener('click', closeAutocomplete);
            }
        }.bind(this));
    }
    
    /**
     * 执行命令
     */
    executeCommand() {
        const command = this.commandInput.value.trim();
        if (!command) return;
        
        // 添加命令到终端显示
        this.appendToTerminal(command, 'command', true);
        
        // 添加到历史记录
        this.addToHistory(command);
        
        // 清空输入框
        this.commandInput.value = '';
        
        // 发送命令执行请求
        ApiClient.post('/api/command_line/execute', {
            session_id: this.sessionId,
            command: command
        })
            .then(response => {
                if (response.success) {
                    // 显示命令输出
                    if (response.output) {
                        this.appendToTerminal(response.output, 'output-text');
                    }
                } else {
                    this.showError('命令执行失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('命令执行失败: ' + error.message);
            });
    }
    
    /**
     * 添加命令到历史记录
     */
    addToHistory(command) {
        // 避免重复添加相同的命令
        if (this.commandHistory.length > 0 && this.commandHistory[this.commandHistory.length - 1] === command) {
            return;
        }
        
        // 添加到历史数组
        this.commandHistory.push(command);
        
        // 重置历史索引
        this.historyIndex = this.commandHistory.length;
        
        // 更新历史列表UI
        this.updateHistoryList();
        
        // 保存到本地存储
        this.saveCommandHistory();
    }
    
    /**
     * 更新历史列表UI
     */
    updateHistoryList() {
        // 清空列表
        this.historyList.innerHTML = '';
        
        // 添加历史命令（最新的在最上面）
        for (let i = this.commandHistory.length - 1; i >= 0; i--) {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.textContent = this.commandHistory[i];
            item.addEventListener('click', () => {
                this.commandInput.value = this.commandHistory[i];
                this.commandInput.focus();
            });
            this.historyList.appendChild(item);
        }
    }
    
    /**
     * 保存命令历史到本地存储
     */
    saveCommandHistory() {
        // 只保存最近的50条命令
        const historyToSave = this.commandHistory.slice(-50);
        localStorage.setItem('commandHistory', JSON.stringify(historyToSave));
    }
    
    /**
     * 加载命令历史从本地存储
     */
    loadCommandHistory() {
        const savedHistory = localStorage.getItem('commandHistory');
        if (savedHistory) {
            try {
                this.commandHistory = JSON.parse(savedHistory);
                this.historyIndex = this.commandHistory.length;
                this.updateHistoryList();
            } catch (error) {
                console.error('加载命令历史失败:', error);
            }
        }
    }
    
    /**
     * 显示保存命令模态框
     */
    showSaveCommandModal() {
        const command = this.commandInput.value.trim();
        if (command) {
            document.getElementById('commandText').value = command;
        }
        $('#saveCommandModal').modal('show');
    }
    
    /**
     * 保存命令到收藏
     */
    saveCommand(event) {
        event.preventDefault();
        
        const command = document.getElementById('commandText').value.trim();
        const name = document.getElementById('commandName').value.trim();
        const description = document.getElementById('commandDescription').value.trim();
        
        if (!command || !name) {
            alert('命令和名称不能为空');
            return;
        }
        
        // 添加到收藏
        const favorite = {
            id: Date.now().toString(),
            name: name,
            command: command,
            description: description
        };
        
        this.favorites.push(favorite);
        
        // 更新收藏列表UI
        this.updateFavoritesList();
        
        // 保存到本地存储
        this.saveFavoriteCommands();
        
        // 隐藏模态框
        $('#saveCommandModal').modal('hide');
        
        // 重置表单
        document.getElementById('saveCommandForm').reset();
    }
    
    /**
     * 更新收藏列表UI
     */
    updateFavoritesList() {
        // 清空列表
        this.favoritesList.innerHTML = '';
        
        // 添加收藏命令
        this.favorites.forEach(favorite => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.title = favorite.description || favorite.command;
            item.textContent = favorite.name;
            
            // 点击填充命令
            item.addEventListener('click', () => {
                this.commandInput.value = favorite.command;
                this.commandInput.focus();
            });
            
            this.favoritesList.appendChild(item);
        });
    }
    
    /**
     * 保存收藏命令到本地存储
     */
    saveFavoriteCommands() {
        localStorage.setItem('favoriteCommands', JSON.stringify(this.favorites));
    }
    
    /**
     * 加载收藏命令从本地存储
     */
    loadFavoriteCommands() {
        const savedFavorites = localStorage.getItem('favoriteCommands');
        if (savedFavorites) {
            try {
                this.favorites = JSON.parse(savedFavorites);
                this.updateFavoritesList();
            } catch (error) {
                console.error('加载收藏命令失败:', error);
            }
        }
    }
    
    /**
     * 加载会话列表
     */
    loadSessions() {
        // 发送API请求获取会话列表
        ApiClient.get('/api/command_line/sessions')
            .then(response => {
                if (response.success) {
                    this.sessions = response.sessions || [];
                    this.updateSessionsList();
                }
            })
            .catch(error => {
                console.error('加载会话列表失败:', error);
            });
    }
    
    /**
     * 更新会话列表UI
     */
    updateSessionsList() {
        // 清空列表
        this.sessionsList.innerHTML = '';
        
        // 添加会话
        this.sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.textContent = `${session.device_name} (${new Date(session.created_at).toLocaleString()})`;
            
            // 点击恢复会话
            item.addEventListener('click', () => {
                this.restoreSession(session.id);
            });
            
            this.sessionsList.appendChild(item);
        });
        
        // 添加创建会话按钮
        const createButton = document.createElement('button');
        createButton.className = 'btn btn-sm btn-success w-100 mt-2';
        createButton.innerHTML = '<i class="bi bi-plus-circle me-1"></i>创建新会话';
        createButton.addEventListener('click', this.showCreateSessionModal.bind(this));
        this.sessionsList.appendChild(createButton);
    }
    
    /**
     * 恢复会话
     */
    restoreSession(sessionId) {
        // 发送恢复会话请求
        ApiClient.post('/api/command_line/restore_session', {
            session_id: sessionId
        })
            .then(response => {
                if (response.success) {
                    this.isConnected = true;
                    this.sessionId = sessionId;
                    this.currentDevice = response.device;
                    
                    // 更新设备选择
                    for (let i = 0; i < this.deviceSelect.options.length; i++) {
                        if (this.deviceSelect.options[i].value === this.currentDevice.id) {
                            this.deviceSelect.selectedIndex = i;
                            break;
                        }
                    }
                    
                    // 更新设备信息显示
                    this.deviceInfo.textContent = `设备: ${this.currentDevice.name} | 类型: ${this.currentDevice.type} | IP: ${this.currentDevice.ip}`;
                    
                    // 更新UI状态
                    this.updateConnectionState(true);
                    
                    // 显示会话历史
                    this.clearTerminal();
                    this.appendToTerminal('已恢复会话', 'success');
                    if (response.history) {
                        response.history.forEach(entry => {
                            this.appendToTerminal(entry.command, 'command', true);
                            if (entry.output) {
                                this.appendToTerminal(entry.output, 'output-text');
                            }
                        });
                    }
                    
                    // 聚焦到命令输入框
                    this.commandInput.focus();
                } else {
                    this.showError('恢复会话失败: ' + response.message);
                }
            })
            .catch(error => {
                this.showError('恢复会话失败: ' + error.message);
            });
    }
    
    /**
     * 清空终端
     */
    clearTerminal() {
        this.terminalOutput.innerHTML = '';
    }
    
    /**
     * 添加内容到终端显示
     */
    appendToTerminal(text, className = '', withPrompt = false) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        if (withPrompt) {
            const prompt = document.createElement('span');
            prompt.className = 'terminal-prompt';
            prompt.textContent = '> ';
            line.appendChild(prompt);
        }
        
        const content = document.createElement('span');
        content.className = className ? `terminal-${className}` : '';
        
        // 处理多行文本
        if (text.includes('\n')) {
            const lines = text.split('\n');
            content.textContent = lines[0];
            line.appendChild(content);
            this.terminalOutput.appendChild(line);
            
            // 添加后续行
            for (let i = 1; i < lines.length; i++) {
                const nextLine = document.createElement('div');
                nextLine.className = 'terminal-line';
                const nextContent = document.createElement('span');
                nextContent.className = className ? `terminal-${className}` : '';
                nextContent.textContent = lines[i];
                nextLine.appendChild(nextContent);
                this.terminalOutput.appendChild(nextLine);
            }
        } else {
            content.textContent = text;
            line.appendChild(content);
            this.terminalOutput.appendChild(line);
        }
        
        // 滚动到底部
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }
    
    /**
     * 显示错误消息
     */
    showError(message) {
        this.appendToTerminal(message, 'error');
    }
    
    /**
     * 显示欢迎消息
     */
    showWelcomeMessage() {
        const welcomeMessage = [
            '欢迎使用网络设备命令行工具',
            '-----------------------------',
            '请从左侧选择一个设备并连接，然后开始输入命令。',
            '使用上下箭头键浏览命令历史，Tab键自动完成命令。',
            '您可以保存常用命令以便快速访问。',
            '-----------------------------'
        ].join('\n');
        
        this.appendToTerminal(welcomeMessage, 'info');
    }
    
    /**
     * 处理URL参数
     */
    handleUrlParams() {
        // 获取URL参数
        const urlParams = new URLSearchParams(window.location.search);
        const deviceIP = urlParams.get('device');
        const deviceName = urlParams.get('name');
        
        // 如果URL中包含设备IP参数
        if (deviceIP) {
            // 在设备列表中查找匹配的设备
            let deviceFound = false;
            
            // 等待设备列表加载完成
            setTimeout(() => {
                for (let i = 0; i < this.deviceSelect.options.length; i++) {
                    const option = this.deviceSelect.options[i];
                    if (option.dataset.ip === deviceIP) {
                        // 选中匹配的设备
                        this.deviceSelect.selectedIndex = i;
                        this.handleDeviceChange();
                        deviceFound = true;
                        
                        // 自动打开连接对话框
                        this.connectDevice();
                        
                        // 如果有设备名称参数，填充到设备连接对话框
                        if (deviceName) {
                            this.appendToTerminal(`准备连接到设备: ${deviceName} (${deviceIP})`, 'info');
                        }
                        
                        break;
                    }
                }
                
                // 如果在设备列表中未找到匹配的设备，但有设备IP和名称
                if (!deviceFound && deviceIP) {
                    // 填充设备连接对话框
                    document.getElementById('deviceIp').value = deviceIP;
                    
                    // 显示连接对话框
                    $('#connectDeviceModal').modal('show');
                    
                    // 显示信息
                    if (deviceName) {
                        this.appendToTerminal(`准备连接到设备: ${deviceName} (${deviceIP})`, 'info');
                    } else {
                        this.appendToTerminal(`准备连接到设备IP: ${deviceIP}`, 'info');
                    }
                }
            }, 500); // 给设备列表加载一些时间
        }
    }
}

/**
 * 插入命令到输入框
 */
CommandLineManager.prototype.insertCommand = function(command) {
    if (this.commandInput) {
        this.commandInput.value = command;
        this.commandInput.focus();
    }
};

/**
 * 清空命令历史
 */
CommandLineManager.prototype.clearHistory = function() {
    this.commandHistory = [];
    this.historyIndex = -1;
    this.updateHistoryList();
    this.saveCommandHistory();
};

/**
 * 复制终端输出
 */
CommandLineManager.prototype.copyOutput = function() {
    if (!this.terminalOutput) return;
    
    // 获取终端输出文本
    const outputText = Array.from(this.terminalOutput.querySelectorAll('.terminal-line'))
        .map(line => line.textContent.trim())
        .join('\n');
    
    // 复制到剪贴板
    navigator.clipboard.writeText(outputText)
        .then(() => {
            this.appendToTerminal('已复制终端输出到剪贴板', 'success');
        })
        .catch(err => {
            this.showError('复制失败: ' + err.message);
        });
};

/**
 * 下载终端输出
 */
CommandLineManager.prototype.downloadOutput = function() {
    if (!this.terminalOutput) return;
    
    // 获取终端输出文本
    const outputText = Array.from(this.terminalOutput.querySelectorAll('.terminal-line'))
        .map(line => line.textContent.trim())
        .join('\n');
    
    // 创建下载链接
    const blob = new Blob([outputText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'terminal_output_' + new Date().toISOString().replace(/[:.]/g, '-') + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    this.appendToTerminal('已下载终端输出', 'success');
};

/**
 * 显示创建会话模态框
 */
CommandLineManager.prototype.showCreateSessionModal = function() {
    // 获取模态框元素
    const modal = document.getElementById('createSessionModal');
    
    // 加载设备列表到下拉框
    const sessionDeviceSelect = document.getElementById('sessionDevice');
    sessionDeviceSelect.innerHTML = '<option value="">选择设备...</option>';
    
    // 复制设备选择框的选项
    Array.from(this.deviceSelect.options).forEach(option => {
        if (option.value) { // 跳过空选项
            const newOption = document.createElement('option');
            newOption.value = option.value;
            newOption.textContent = option.textContent;
            newOption.dataset.type = option.dataset.type;
            newOption.dataset.ip = option.dataset.ip;
            sessionDeviceSelect.appendChild(newOption);
        }
    });
    
    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
};

/**
 * 处理创建会话表单提交
 */
CommandLineManager.prototype.handleCreateSessionForm = function(event) {
    event.preventDefault();
    
    const sessionName = document.getElementById('sessionName').value;
    const deviceId = document.getElementById('sessionDevice').value;
    const username = document.getElementById('sessionUsername').value;
    const password = document.getElementById('sessionPassword').value;
    const deviceType = document.getElementById('sessionType').value;
    
    if (!deviceId || !username || !password) {
        alert('请填写完整的会话信息');
        return;
    }
    
    // 隐藏模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('createSessionModal'));
    modal.hide();
    
    // 显示连接中消息
    this.appendToTerminal(`正在创建会话 ${sessionName}...`, 'info');
    
    // 发送创建会话请求
    ApiClient.post('/api/command_line/create_session', {
        session_name: sessionName,
        device_id: deviceId,
        username: username,
        password: password,
        device_type: deviceType
    })
        .then(response => {
            if (response.success) {
                this.isConnected = true;
                this.sessionId = response.session_id;
                this.currentDevice = response.device;
                
                // 更新设备选择
                for (let i = 0; i < this.deviceSelect.options.length; i++) {
                    if (this.deviceSelect.options[i].value === this.currentDevice.id) {
                        this.deviceSelect.selectedIndex = i;
                        break;
                    }
                }
                
                // 更新设备信息显示
                this.deviceInfo.textContent = `设备: ${this.currentDevice.name} | 类型: ${this.currentDevice.type} | IP: ${this.currentDevice.ip}`;
                
                // 更新UI状态
                this.updateConnectionState(true);
                
                this.appendToTerminal(`成功创建会话 ${sessionName}`, 'success');
                this.appendToTerminal(response.welcome_message || '', 'output-text');
                
                // 重新加载会话列表
                this.loadSessions();
                
                // 聚焦到命令输入框
                this.commandInput.focus();
            } else {
                this.showError('创建会话失败: ' + response.message);
            }
        })
        .catch(error => {
            this.showError('创建会话失败: ' + error.message);
        });
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.commandLineManager = new CommandLineManager();
});