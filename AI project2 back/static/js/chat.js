// 聊天页面JavaScript文件

class ChatManager {
    constructor() {
        this.currentMode = 'chat';
        this.isTyping = false;
        this.messageHistory = [];
        this.toolExecutionModal = null;
        this.cloudSyncEnabled = true;
        this.lastSyncTime = null;
        this.currentUser = null;
        this.sessionId = null;
        this.currentModel = null;
        
        // 检查用户认证
        this.checkAuthentication();
        
        this.initializeMarkdown();
        this.initializeElements();
        this.bindEvents();
        this.setupTopologyDataListener();
        this.initializeSession();
        this.loadAvailableModels();
    }
    
    initializeMarkdown() {
        // 确保marked和hljs已加载
        if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
            // 配置marked选项
            marked.setOptions({
                renderer: new marked.Renderer(),
                highlight: function(code, lang) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                },
                langPrefix: 'hljs language-',
                pedantic: false,
                gfm: true,
                breaks: true,
                sanitize: false,
                smartypants: false,
                xhtml: false
            });
            
            // 初始化highlight.js
            hljs.configure({
                tabReplace: '    ', // 4个空格替换tab
                classPrefix: 'hljs-'
            });
        }
    }
    
    checkAuthentication() {
        // 检查用户是否已登录
        if (!ApiClient.isAuthenticated()) {
            window.location.href = '/login';
            return;
        }
        
        // 获取用户信息
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            this.currentUser = JSON.parse(userInfo);
        }
    }
    
    getSessionId() {
        // 获取或生成会话ID（基于用户ID）
        if (!this.sessionId) {
            const userId = this.currentUser ? this.currentUser.id : 'anonymous';
            this.sessionId = localStorage.getItem(`chat_session_id_${userId}`) || this.generateSessionId();
            localStorage.setItem(`chat_session_id_${userId}`, this.sessionId);
        }
        return this.sessionId;
    }
    
    generateSessionId() {
        // 生成唯一的会话ID
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    async initializeSession() {
        try {
            // 首先尝试从服务器验证当前会话
            const sessionId = this.getSessionId();
            console.log('初始化会话:', sessionId);
            
            try {
                const response = await ApiClient.get(`/api/chat/sessions/${sessionId}`);
                if (response.success) {
                    console.log('会话验证成功，加载历史记录');
                    this.loadChatHistory();
                } else {
                    console.log('会话验证失败，创建新会话');
                    const created = await this.createNewSession();
                    if (created) {
                        this.loadChatHistory();
                    } else {
                        console.error('无法创建新会话，使用离线模式');
                        this.showWelcomeMessage();
                    }
                }
            } catch (error) {
                if (error.message && error.message.includes('会话不存在')) {
                    console.log('会话不存在，创建新会话');
                    const created = await this.createNewSession();
                    if (created) {
                        this.loadChatHistory();
                    } else {
                        console.error('无法创建新会话，使用离线模式');
                        this.showWelcomeMessage();
                    }
                } else {
                    console.error('会话初始化失败:', error);
                    // 如果网络错误等，仍然尝试加载本地历史
                    this.loadChatHistory();
                }
            }
        } catch (error) {
            console.error('会话初始化过程出错:', error);
            this.loadChatHistory();
        }
    }

    showWelcomeMessage() {
        // 显示欢迎消息，用于离线模式或会话创建失败时
        this.chatMessages.innerHTML = '';
        this.messageHistory = [];
        
        const welcomeMessage = {
            type: 'ai',
            content: '欢迎使用AI助手！当前处于离线模式，部分功能可能受限。请检查网络连接后刷新页面。',
            timestamp: new Date().toISOString()
        };
        
        this.addMessage(welcomeMessage.type, welcomeMessage.content);
        this.messageHistory.push(welcomeMessage);
    }

    getUserPreferences() {
        // 获取用户偏好设置
        return {
            mode: this.currentMode,
            language: 'zh-CN',
            theme: 'default',
            markdown_enabled: typeof marked !== 'undefined',
            model: this.currentModel
        };
    }
    
    async loadAvailableModels() {
        try {
            // 从API获取可用模型列表
            const response = await ApiClient.get('/api/chat/models');
            
            if (response.success && response.data) {
                const models = response.data;
                
                // 清空现有选项
                this.modelSelect.innerHTML = '';
                
                // 添加模型选项
                models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.id;
                    option.textContent = model.name;
                    this.modelSelect.appendChild(option);
                });
                
                // 尝试恢复用户之前选择的模型
                const preferredModel = localStorage.getItem('preferred_model');
                if (preferredModel && this.modelSelect.querySelector(`option[value="${preferredModel}"]`)) {
                    this.modelSelect.value = preferredModel;
                    this.currentModel = preferredModel;
                } else if (models.length > 0) {
                    // 默认选择第一个模型
                    this.currentModel = models[0].id;
                    this.modelSelect.value = this.currentModel;
                }
                
                console.log(`已加载 ${models.length} 个模型，当前选择: ${this.currentModel}`);
            } else {
                console.error('加载模型列表失败:', response.error || '未知错误');
                this.modelSelect.innerHTML = '<option value="" disabled selected>加载失败</option>';
            }
        } catch (error) {
            console.error('获取模型列表出错:', error);
            this.modelSelect.innerHTML = '<option value="" disabled selected>加载失败</option>';
        }
    }
    
    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.charCount = document.getElementById('charCount');
        this.currentModeIcon = document.getElementById('currentModeIcon');
        this.currentModeText = document.getElementById('currentModeText');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        // 模式切换元素
        this.chatModeRadio = document.getElementById('chatMode');
        this.buildModeRadio = document.getElementById('buildMode');
        this.chatModeDesc = document.getElementById('chatModeDesc');
        this.buildModeDesc = document.getElementById('buildModeDesc');
        
        // 侧边栏状态元素
        this.sidebarTotalDevices = document.getElementById('sidebarTotalDevices');
        this.sidebarOnlineDevices = document.getElementById('sidebarOnlineDevices');
        this.sidebarOfflineDevices = document.getElementById('sidebarOfflineDevices');
        this.sidebarDeviceList = document.getElementById('sidebarDeviceList');
        
        // 模型选择元素
        this.modelSelect = document.getElementById('modelSelect');
        
        // 工具执行模态框
        this.toolExecutionModal = new bootstrap.Modal(document.getElementById('toolExecutionModal'));
    }
    
    bindEvents() {
        // 发送按钮点击事件
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // 输入框事件
        this.messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        });
        
        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.autoResize();
        });
        
        // 模式切换事件
        this.chatModeRadio.addEventListener('change', () => {
            if (this.chatModeRadio.checked) {
                this.switchMode('chat');
            }
        });
        
        this.buildModeRadio.addEventListener('change', () => {
            if (this.buildModeRadio.checked) {
                this.switchMode('build');
            }
        });
        
        // 模型选择事件
        if (this.modelSelect) {
            this.modelSelect.addEventListener('change', () => {
                this.currentModel = this.modelSelect.value;
                console.log(`模型已切换为: ${this.currentModel}`);
                // 保存用户选择的模型到本地存储
                localStorage.setItem('preferred_model', this.currentModel);
            });
        }
        
        // 网络状态监听
        networkStatusManager.addListener((status) => {
            this.updateNetworkStatus(status);
        });
    }
    
    switchMode(mode) {
        this.currentMode = mode;
        
        if (mode === 'chat') {
            this.currentModeIcon.className = 'fas fa-comments me-2';
            this.currentModeText.textContent = '聊天模式';
            this.chatModeDesc.classList.add('active');
            this.buildModeDesc.classList.remove('active');
        } else {
            this.currentModeIcon.className = 'fas fa-cogs me-2';
            this.currentModeText.textContent = '构建模式';
            this.chatModeDesc.classList.remove('active');
            this.buildModeDesc.classList.add('active');
        }
    }
    
    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;
        
        if (count > 800) {
            this.charCount.style.color = '#dc3545';
        } else if (count > 600) {
            this.charCount.style.color = '#ffc107';
        } else {
            this.charCount.style.color = '#6c757d';
        }
    }
    
    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        this.addMessage('user', message, null, {}, false);

        // 清空输入框
        this.messageInput.value = '';
        this.updateCharCount();
        this.autoResize();

        
        // 显示打字指示器
        this.showTypingIndicator();
        
        try {
            // 准备聊天历史上下文（转换为标准AI请求格式）
            const chatHistory = this.messageHistory
                .filter(msg => msg.type === 'user' || msg.type === 'assistant' || msg.type === 'tool')
                .map(msg => ({
                    role: msg.type === 'user' ? 'user' : 'assistant',
                    content: msg.content,
                    timestamp: msg.timestamp
                }));
            
            // 发送消息到后端（使用标准AI请求JSON格式）
            let response;
            try {
                response = await ApiClient.post(`/api/chat/sessions/${this.getSessionId()}/messages`, {
                    message: message,
                    mode: this.currentMode,
                    model: this.currentModel, // 添加模型参数
                    chat_history: chatHistory,
                    context: {
                        user_preferences: this.getUserPreferences(),
                        timestamp: new Date().toISOString()
                    }
                });
            } catch (error) {
                // 如果会话不存在，先创建会话再重试
                if (error.message && error.message.includes('会话不存在')) {
                    console.log('会话不存在，创建新会话后重试');
                    const created = await this.createNewSession();
                    if (!created) {
                        throw new Error('无法创建新会话，请检查网络连接');
                    }
                    response = await ApiClient.post(`/api/chat/sessions/${this.getSessionId()}/messages`, {
                        message: message,
                        mode: this.currentMode,
                        chat_history: chatHistory,
                        context: {
                            user_preferences: this.getUserPreferences(),
                            timestamp: new Date().toISOString()
                        }
                    });
                } else {
                    throw error;
                }
            }
            
            // 隐藏打字指示器
            this.hideTypingIndicator();
            this.hideToolExecutionModal();

            const aiMessage = response.data.ai_message;
            
            this.addMessage('assistant', aiMessage.content, aiMessage.tool_calls, aiMessage.choice);
            // 如果有工具调用，执行工具
            if (aiMessage.tool_calls && aiMessage.tool_calls.length > 0) {
                await this.executeToolCalls(aiMessage.tool_calls);
            }

        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('error', `发送消息失败: ${error.message}`);
            Utils.showNotification('发送消息失败', 'error');
        }
    }
    
    addMessage(type, content, toolCalls = null, choice = {}, is_upload = true, toolStatus = {}) {
        if (type === 'tool') return;
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const timestamp = new Date().toISOString();
        
        let avatarIcon = '';
        if (type === 'user') {
            avatarIcon = '<i class="bi bi-user"></i>';
        } else if (type === 'assistant') {
            avatarIcon = '<i class="bi bi-robot"></i>';
        } else if (type === 'error') {
            avatarIcon = '<i class="fas fa-exclamation-triangle"></i>';
        } else if (type === 'system') {
            avatarIcon = '<i class="fas fa-info-circle"></i>';
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatarIcon}
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessageContent(content || '')}</div>
                <div class="message-time">${Utils.formatTime(timestamp)}</div>
                ${toolCalls ? this.renderToolCalls(toolCalls, toolStatus) : ''}
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // 更新会话显示信息
        this.updateSessionDisplay();
        
        // 保存到历史记录 - 确保数据完整性
        const messageData = {
            type,
            content,
            timestamp,
            toolCalls: toolCalls || null,
            choice: choice || {},
            toolStatus: toolStatus || {}
        };
        
        // 防止重复添加相同的消息
        const isDuplicate = this.messageHistory.some(msg => 
            msg.timestamp === timestamp && 
            msg.type === type && 
            msg.content === content
        );
        
        if (!isDuplicate) {
            this.messageHistory.push(messageData);
        }
        
        // 每次添加消息时保存到云端
        if (this.cloudSyncEnabled && this.messageHistory.length > 1 && is_upload) { // 跳过欢迎消息
            this.saveChatToCloud();
        }
    }
    
    addSystemMessage(content) {
        this.addMessage('system', content);
    }
    
    formatMessageContent(content) {
        // 严格的输入验证
        if (content === null || content === undefined) {
            console.warn('formatMessageContent: content is null or undefined');
            return '';
        }
        
        // 确保 content 是字符串类型
        if (typeof content !== 'string') {
            console.warn('formatMessageContent: content is not a string, converting:', typeof content, content);
            content = String(content);
        }
        
        // 如果内容为空字符串
        if (content.trim() === '') {
            return '';
        }
        
        // 检查markdown库是否可用
        if (typeof marked === 'undefined') {
            // 如果marked不可用，使用基本的HTML转换
            content = content.replace(/\n/g, '<br>');
            content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
            content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
            content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
            return content;
        }
        
        try {
            // 使用marked解析markdown
            let htmlContent = marked.parse(content);
            
            // 处理表格样式
            htmlContent = htmlContent.replace(/<table>/g, '<table class="table table-bordered table-striped">');
            
            // 处理图片最大宽度
            htmlContent = htmlContent.replace(/<img/g, '<img style="max-width:100%"');
            
            // 处理链接在新窗口打开
            htmlContent = htmlContent.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a href="$1" target="_blank"');
            
            return htmlContent;
        } catch (error) {
            console.error('Markdown解析错误:', error);
            // 如果解析失败，返回原始内容
            return content.replace(/\n/g, '<br>');
        }
    }
    
    renderToolCalls(toolCalls, toolStatus = {}) {
        if (!toolCalls || toolCalls.length === 0) return '';
        
        const toolCallsHtml = toolCalls.map(toolCall => {
            // 处理不同的工具调用结构
            const toolName = toolCall.name || (toolCall.function && toolCall.function.name) || '未知工具';
            const toolId = toolCall.id || toolCall.tool_id || toolName;
            
            // 根据tool_status渲染调用状态
            let status = 'executing';
            let statusText = '执行中';
            let statusIcon = 'fas fa-spinner fa-spin';
            
            // 检查toolStatus中是否有对应的状态
            if (toolStatus[toolName]) {
                status = toolStatus[toolName];
            } else if (toolStatus[toolId]) {
                status = toolStatus[toolId];
            }
            
            // 根据状态设置显示文本和图标
            switch (status) {
                case 'completed':
                case 'success':
                    statusText = '已完成';
                    statusIcon = 'fas fa-check-circle';
                    break;
                case 'failed':
                case 'error':
                    statusText = '失败';
                    statusIcon = 'fas fa-times-circle';
                    break;
                case 'denied':
                    statusText = '已拒绝';
                    statusIcon = 'fas fa-ban';
                    break;
                case 'pending':
                    statusText = '等待中';
                    statusIcon = 'fas fa-clock';
                    break;
                case 'executing':
                case 'running':
                default:
                    statusText = '执行中';
                    statusIcon = 'fas fa-spinner fa-spin';
                    break;
            }
            
            return `
            <div class="tool-call" data-tool="${toolName}">
                <div class="tool-call-icon">
                    <i class="${statusIcon}"></i>
                </div>
                <div class="tool-call-name">${toolName}</div>
                <div class="tool-call-status ${status}">${statusText}</div>
            </div>
        `;
        }).join('');
        
        return `
            <div class="tool-calls">
                <div class="small text-muted mb-2">
                    <i class="fas fa-tools me-1"></i>AI工具调用:
                </div>
                ${toolCallsHtml}
            </div>
        `;
    }
    
    async executeToolCalls(toolCalls) {
        const toolResults = [];
        
        try {
            for (const toolCall of toolCalls) {
            try {
                // 处理不同的工具调用结构
                const toolName = toolCall.name || (toolCall.function && toolCall.function.name);
                const toolId = toolCall.id || toolCall.tool_id || 'unknown';
                const toolParams = toolCall.parameters || 
                                 (toolCall.function && JSON.parse(toolCall.function.arguments || '{}')) || 
                                 {};
                
                if (!toolName) {
                    console.error('工具名称为空:', toolCall);
                    toolResults.push({
                        tool_name: '未知工具',
                        tool_id: toolId,
                        result: { error: '工具名称为空' },
                        success: false
                    });
                    continue;
                }
                
                // 检查是否需要用户确认
                const requireConfirm = document.getElementById('requireFunctionConfirm').checked;
                
                if (requireConfirm) {
                    // 请求用户确认执行此工具调用
                    const userApproved = await this.requestUserApproval({
                        name: toolName,
                        id: toolId,
                        parameters: toolParams
                    });
                    
                    if (!userApproved) {
                        // 用户拒绝执行，记录拒绝结果
                        toolResults.push({
                            tool_name: toolName,
                            tool_id: toolId,
                            result: { error: '用户拒绝执行此操作' },
                            success: false,
                            user_denied: true,
                            status: '已拒绝'
                        });
                        
                        // 更新工具调用状态为已拒绝
                        this.updateToolCallStatus(toolName, 'denied');
                        continue;
                    }
                    
                    // 如果用户批准了，使用更新后的参数
                    if (this.currentToolCallParams) {
                        Object.assign(toolParams, this.currentToolCallParams);
                        this.currentToolCallParams = null; // 清除临时参数
                    }
                }
                
                // 显示工具执行模态框
                this.showToolExecutionModal(toolName);
                
                // 执行工具
                const result = await ApiClient.post('/api/chat/tools/execute', {
                    tool_name: toolName,
                    tool_params: toolParams,
                    session_id: this.getSessionId()
                });
                
                // 更新工具调用状态
                this.updateToolCallStatus(toolName, 'completed');
                
                // 收集工具执行结果
                toolResults.push({
                    tool_name: toolName,
                    tool_id: toolId,
                    result: result.data,
                    success: true
                });
                
            } catch (error) {
                const toolName = toolCall.name || (toolCall.function && toolCall.function.name) || '未知工具';
                const toolId = toolCall.id || toolCall.tool_id || 'unknown';
                
                // 更新工具调用状态为失败
                this.updateToolCallStatus(toolName, 'failed');
                
                // 收集错误结果
                toolResults.push({
                    tool_name: toolName,
                    tool_id: toolId,
                    result: { error: error.message },
                    success: false
                });
            }
        }
        
        // 隐藏工具执行模态框
        
        // 将工具执行结果发送给AI进行处理
        } finally {
            this.hideToolExecutionModal();
        }
        await this.sendToolResultsToAI(toolResults);
    }
    
    // 请求用户确认执行工具调用
    async requestUserApproval(toolCall) {
        return new Promise((resolve) => {
            // 保存原始工具调用参数
            this.originalToolCallParams = toolCall.parameters || 
                                        (toolCall.function && JSON.parse(toolCall.function.arguments || '{}')) || 
                                        {};
            
            // 填充确认模态框的内容
            this.populateFunctionCallModal(toolCall);
            
            // 显示确认模态框
            const modal = new bootstrap.Modal(document.getElementById('functionCallConfirmModal'));
            modal.show();
            
            // 绑定确认按钮事件
            const approveBtn = document.getElementById('approveFunctionCall');
            const denyBtn = document.getElementById('denyFunctionCall');
            const confirmCheckbox = document.getElementById('confirmUnderstand');
            
            // 重置确认状态
            confirmCheckbox.checked = false;
            approveBtn.disabled = true;
            
            // 监听复选框变化
            const checkboxHandler = () => {
                approveBtn.disabled = !confirmCheckbox.checked;
            };
            confirmCheckbox.addEventListener('change', checkboxHandler);
            
            // 批准按钮点击事件
            const approveHandler = () => {
                // 获取用户选择的参数
                const selectedParams = this.getCurrentSelectedParameters();
                
                // 更新工具调用对象的参数
                if (toolCall.function && toolCall.function.arguments) {
                    toolCall.function.arguments = JSON.stringify(selectedParams);
                } else if (toolCall.parameters) {
                    toolCall.parameters = selectedParams;
                }
                
                // 保存更新后的参数到当前工具调用参数中
                this.currentToolCallParams = selectedParams;
                
                modal.hide();
                cleanup();
                resolve(true);
            };
            
            // 拒绝按钮点击事件
            const denyHandler = () => {
                modal.hide();
                cleanup();
                resolve(false);
            };
            
            // 清理事件监听器
            const cleanup = () => {
                approveBtn.removeEventListener('click', approveHandler);
                denyBtn.removeEventListener('click', denyHandler);
                confirmCheckbox.removeEventListener('change', checkboxHandler);
            };
            
            // 绑定事件
            approveBtn.addEventListener('click', approveHandler);
            denyBtn.addEventListener('click', denyHandler);
        });
    }
    
    // 填充Function Call确认模态框的内容
    populateFunctionCallModal(toolCall) {
        // 处理不同的工具调用结构
        const toolName = toolCall.name || (toolCall.function && toolCall.function.name) || '未知';
        const toolParams = toolCall.parameters || 
                          (toolCall.function && JSON.parse(toolCall.function.arguments || '{}')) || 
                          {};
        
        // 保存原始参数供后续使用
        this.originalToolCallParams = { ...toolParams };
        
        // 设置function名称
        document.getElementById('functionName').textContent = toolName;
        
        // 设置function描述
        const description = this.getFunctionDescription(toolName);
        document.getElementById('functionDescription').textContent = description;
        
        // 处理参数显示和多选功能
        this.renderParametersWithSelection(toolParams);
        
        // 设置风险评估
        this.assessFunctionRisk({
            name: toolName,
            parameters: toolParams
        });
    }
    
    // 渲染参数并处理多选功能
    renderParametersWithSelection(toolParams) {
        const parametersElement = document.getElementById('functionParameters');
        
        // 检查是否有包含'|'的参数值
        const hasMultipleOptions = this.hasParametersWithMultipleOptions(toolParams);
        
        if (hasMultipleOptions) {
            // 创建交互式参数选择界面
            parametersElement.innerHTML = this.createParameterSelectionHTML(toolParams);
            
            // 绑定选择事件
            this.bindParameterSelectionEvents(parametersElement);
        } else {
            // 普通参数显示
            parametersElement.textContent = JSON.stringify(toolParams, null, 2);
        }
    }
    
    // 检查参数是否包含多个选项
    hasParametersWithMultipleOptions(params) {
        for (const [key, value] of Object.entries(params)) {
            if (typeof value === 'string' && value.includes('|')) {
                return true;
            }
        }
        return false;
    }
    
    // 创建参数选择HTML
    createParameterSelectionHTML(params) {
        let html = '<div class="parameter-selection">';
        
        for (const [key, value] of Object.entries(params)) {
            html += `<div class="mb-2">`;
            html += `<label class="form-label fw-bold" style="font-size: 0.85rem; margin-bottom: 0.25rem;">${key}:</label>`;
            
            if (typeof value === 'string' && value.includes('|')) {
                // 多选参数 - 使用下拉选择
                const options = value.split('|').map(opt => opt.trim());
                html += `<div class="parameter-options" data-param="${key}">`;
                html += `<select class="form-select form-select-sm" name="${key}_options" style="max-width: 250px;">`;
                
                options.forEach((option, index) => {
                    html += `<option value="${option}" ${index === 0 ? 'selected' : ''}>${option}</option>`;
                });
                
                html += `</select>`;
                html += `</div>`;
            } else {
                // 普通参数
                html += `<div class="form-control-plaintext bg-light p-2 rounded">${value}</div>`;
            }
            
            html += `</div>`;
        }
        
        html += '</div>';
        return html;
    }
    
    // 绑定参数选择事件
    bindParameterSelectionEvents(container) {
        const selectInputs = container.querySelectorAll('select[name$="_options"]');
        
        selectInputs.forEach(select => {
            select.addEventListener('change', () => {
                // 更新工具调用参数
                this.updateToolCallParameters();
            });
        });
    }
    
    // 更新工具调用参数
    updateToolCallParameters() {
        const container = document.getElementById('functionParameters');
        const parameterOptions = container.querySelectorAll('.parameter-options');
        
        // 构建更新后的参数对象
        const updatedParams = {};
        
        parameterOptions.forEach(optionGroup => {
            const paramName = optionGroup.dataset.param;
            const selectElement = optionGroup.querySelector('select[name$="_options"]');
            
            if (selectElement) {
                updatedParams[paramName] = selectElement.value;
            }
        });
        
        // 保存更新后的参数供后续使用
        this.currentToolCallParams = updatedParams;
    }
    
    // 获取当前选择的参数
    getCurrentSelectedParameters() {
        const container = document.getElementById('functionParameters');
        const parameterOptions = container.querySelectorAll('.parameter-options');
        
        if (parameterOptions.length === 0) {
            // 没有多选参数，返回原始参数
            return this.originalToolCallParams || {};
        }
        
        // 构建选择后的参数对象
        const selectedParams = { ...this.originalToolCallParams };
        
        parameterOptions.forEach(optionGroup => {
            const paramName = optionGroup.dataset.param;
            const selectElement = optionGroup.querySelector('select[name$="_options"]');
            
            if (selectElement) {
                selectedParams[paramName] = selectElement.value;
            }
        });
        
        return selectedParams;
    }
    
    // 获取function描述
    getFunctionDescription(functionName) {
        const descriptions = {
            'get_device_status': '获取网络设备的状态信息，包括在线状态、CPU使用率、内存使用率等',
            'execute_command': '在网络设备上执行配置命令或查看命令',
            'update_device_config': '更新网络设备的配置文件',
            'backup_device_config': '备份网络设备的当前配置',
            'restore_device_config': '恢复网络设备的配置到指定版本',
            'scan_network': '扫描网络以发现新设备或检查网络拓扑',
            'test_connectivity': '测试网络设备之间的连通性',
            'get_interface_status': '获取设备接口的详细状态信息',
            'configure_interface': '配置设备接口参数',
            'add_device': '向网络拓扑中添加新设备',
            'remove_device': '从网络拓扑中移除设备',
            'update_topology': '更新网络拓扑结构'
        };
        
        return descriptions[functionName] || '执行网络管理相关操作';
    }
    
    // 评估function执行风险
    assessFunctionRisk(toolCall) {
        const riskBadge = document.getElementById('riskBadge');
        const riskDescription = document.getElementById('riskDescription');
        const riskAssessment = document.getElementById('riskAssessment');
        
        // 定义高风险操作
        const highRiskFunctions = [
            'execute_command',
            'update_device_config',
            'restore_device_config',
            'configure_interface',
            'remove_device'
        ];
        
        // 定义中风险操作
        const mediumRiskFunctions = [
            'backup_device_config',
            'add_device',
            'update_topology'
        ];
        
        let riskLevel = 'low';
        let riskText = '此操作风险较低，主要进行信息查询';
        let badgeClass = 'bg-success';
        let alertClass = 'alert-success';
        
        const toolName = toolCall.name || (toolCall.function && toolCall.function.name) || '未知';
        
        if (highRiskFunctions.includes(toolName)) {
            riskLevel = 'high';
            riskText = '此操作风险较高，可能会修改设备配置或执行系统命令，请谨慎确认';
            badgeClass = 'bg-danger';
            alertClass = 'alert-danger';
        } else if (mediumRiskFunctions.includes(toolName)) {
            riskLevel = 'medium';
            riskText = '此操作风险中等，会对系统状态产生影响，请仔细检查参数';
            badgeClass = 'bg-warning';
            alertClass = 'alert-warning';
        }
        
        // 更新UI
        riskBadge.textContent = riskLevel === 'high' ? '高风险' : (riskLevel === 'medium' ? '中风险' : '低风险');
        riskBadge.className = `badge ${badgeClass}`;
        riskDescription.textContent = riskText;
        riskAssessment.className = `alert ${alertClass}`;
    }
    
    async sendToolResultsToAI(toolResults) {
        try {
            this.hideToolExecutionModal();
            // 显示AI处理工具结果的指示器
            this.showTypingIndicator();

            const msg = await this.formatToolResultsForAI(toolResults);
            
            // 将工具执行结果发送给AI
            const response = await ApiClient.post('/api/chat/tools/results', {
                tool_results: toolResults,
                mode: this.currentMode,
                session_id: this.getSessionId(),
                model: this.currentModel
            });
            
            // 隐藏打字指示器
            this.hideTypingIndicator();

            // 添加工具执行结果到历史记录
            const toolMessage = {
                'type': 'tool',
                'content': '',
                'timestamp': new Date().toISOString(),
                'toolCalls': [],
                'choice': msg
            };
            
            // 防止重复添加工具消息
            const lastMessage = this.messageHistory[this.messageHistory.length - 1];
            if (!lastMessage || lastMessage.type !== 'tool' || lastMessage.timestamp !== toolMessage.timestamp) {
                this.messageHistory.push(toolMessage);
            }
            
            // 检查是否有用户拒绝的操作
            const deniedOperations = toolResults.filter(result => result.user_denied);
            if (deniedOperations.length > 0) {
                const deniedNames = deniedOperations.map(op => op.tool_name).join(', ');
                this.addMessage('system', `用户拒绝执行以下操作: ${deniedNames}`, null, {}, false);
            }
            
            // 添加AI的响应
            const aiMessage = response.data.ai_message.response;
            this.addMessage('assistant', aiMessage.content || "", aiMessage.tool_calls, aiMessage.choice);
            
            // 如果AI又调用了新的工具，继续执行
            if (aiMessage.tool_calls && aiMessage.tool_calls.length > 0) {
                await this.executeToolCalls(aiMessage.tool_calls);
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('error', `处理工具结果失败: ${error.message}`);
            Utils.showNotification('处理工具结果失败', 'error');
        } finally {
            this.hideToolExecutionModal();
        }
    }

    async formatToolResultsForAI(toolResults) {
        if (!toolResults || toolResults.length === 0) {
            return "没有工具执行结果。";
        }
    
        const messageParts = [];
    
        for (let i = 0; i < toolResults.length; i++) {
            const toolResult = toolResults[i];
            const toolName = toolResult.tool_name || '未知工具';
            const result = toolResult.result || {};
            const toolId = toolResult.tool_id || "";
    
            messageParts.push({
                tool_call_id: toolId,
                role: "tool",
                name: toolName,
                content: JSON.stringify(result)  // 将结果转为 JSON 字符串
            });
        }
    
        return messageParts;
    }
    
    formatToolResult(toolName, result) {
        let content = `**工具执行结果: ${toolName}**\n\n`;
        
        if (result.error) {
            content += `❌ 执行失败: ${result.error}`;
        } else {
            switch (toolName) {
                case 'get_network_status':
                    content += this.formatNetworkStatus(result);
                    break;
                case 'get_device_config':
                    content += this.formatDeviceConfig(result);
                    break;
                case 'ping_device':
                    content += this.formatPingResult(result);
                    break;
                default:
                    content += `✅ 执行成功\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``;
            }
        }
        
        return content;
    }
    
    formatNetworkStatus(status) {
        const summary = status.summary;
        let content = `📊 **网络状态概览**\n\n`;
        content += `• 总设备数: ${summary.total_devices}\n`;
        content += `• 在线设备: ${summary.online_devices}\n`;
        content += `• 离线设备: ${summary.offline_devices}\n`;
        content += `• 异常设备: ${summary.error_devices}\n\n`;
        
        content += `🔗 **设备详情**\n`;
        Object.entries(status.devices).forEach(([deviceId, device]) => {
            const statusIcon = device.status === 'online' ? '🟢' : device.status === 'offline' ? '🔴' : '🟡';
            content += `${statusIcon} ${deviceId}: ${device.status}\n`;
        });
        
        return content;
    }
    
    formatDeviceConfig(config) {
        let content = `⚙️ **设备配置**\n\n`;
        content += `\`\`\`json\n${JSON.stringify(config, null, 2)}\n\`\`\``;
        return content;
    }
    
    formatPingResult(result) {
        let content = `🏓 **连通性测试**\n\n`;
        content += `目标: ${result.target}\n`;
        
        if (result.status === 'success') {
            content += `✅ 连接成功\n`;
            content += `响应时间: ${result.rtt}\n`;
            content += `丢包率: ${result.packet_loss}`;
        } else {
            content += `❌ 连接失败\n`;
            content += `错误: ${result.error}`;
        }
        
        return content;
    }
    
    updateToolCallStatus(toolName, status) {
        const toolCallElement = document.querySelector(`[data-tool="${toolName}"] .tool-call-status.executing`);
        if (toolCallElement) {
            toolCallElement.className = `tool-call-status ${status}`;
            toolCallElement.textContent = status === 'completed' ? '已完成' : status === 'failed' ? '失败' : status === 'denied' ? '已拒绝' : '执行中';
        }
        
        // 保存工具状态到后端
        this.saveToolStatus(toolName, status);
    }
    
    async saveToolStatus(toolName, status) {
        try {
            await ApiClient.post('/api/chat/tools/status', {
                tool_name: toolName,
                status: status,
                session_id: this.getSessionId()
            });
        } catch (error) {
            console.error('保存工具状态失败:', error);
        }
    }
    
    showToolExecutionModal(toolName) {
        document.getElementById('currentToolName').textContent = toolName;
        this.toolExecutionModal.show();
    }
    
    hideToolExecutionModal() {
        this.toolExecutionModal.hide();
    }
    
    showTypingIndicator() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-message';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span class="typing-text">思考中</span>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        const typingMessage = this.chatMessages.querySelector('.typing-message');
        if (typingMessage) {
            typingMessage.remove();
        }
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    updateNetworkStatus(status) {
        if (!status) return;
        
        const summary = status.summary;
        this.sidebarTotalDevices.textContent = summary.total_devices;
        this.sidebarOnlineDevices.textContent = summary.online_devices;
        this.sidebarOfflineDevices.textContent = summary.offline_devices;
        
        // 更新连接状态
        this.connectionStatus.textContent = '已连接';
        this.connectionStatus.className = 'badge bg-success';
        
        // 更新设备列表
        this.loadSidebarDeviceList();
    }
    
    loadSidebarDeviceList() {
        if (!this.sidebarDeviceList) return;
        
        // 完全从本地存储获取设备数据
        console.log('从本地存储加载设备列表...');
        
        // 直接从localStorage读取数据
        try {
            const savedData = localStorage.getItem('topology_backup');
            if (savedData) {
                const parsedData = JSON.parse(savedData);
                if (parsedData.data && parsedData.data.devices) {
                    const devices = parsedData.data.devices.slice(0, 3); // 只显示前3个设备
                    console.log('从本地存储加载到设备:', devices);
                    this.displaySidebarDevices(devices);
                    return;
                }
            }
        } catch (error) {
            console.error('从本地存储读取设备数据失败:', error);
        }
        
        // 如果没有本地数据，显示空状态
        console.log('本地存储中没有设备数据');
        this.showNoSidebarDevices();
    }
    
    displaySidebarDevices(devices) {
        if (!this.sidebarDeviceList) return;
        
        if (devices.length === 0) {
            this.showNoSidebarDevices();
            return;
        }
        
        const totalDevices = devices.length;
        const stats = window.topologyStorage.getNetworkStats();
        
        const deviceHtml = devices.slice(0, 3).map(device => {
            const statusInfo = window.topologyStorage.formatDeviceStatus(device.status);
            const deviceIcon = window.topologyStorage.getDeviceIcon(device.device_type);
            
            return `
                <div class="sidebar-device-item mb-2 p-2 border rounded">
                    <div class="d-flex align-items-center">
                        <span class="device-status ${statusInfo.class}"></span>
                        <i class="${deviceIcon} me-2 text-primary"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold small">${device.hostname || device.ip}</div>
                            <div class="text-muted" style="font-size: 0.75em;">
                                ${device.ip}
                                <span class="badge bg-${statusInfo.class} ms-1" style="font-size: 0.6em;">
                                    ${statusInfo.text}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        if (devices.length > 3) {
            this.sidebarDeviceList.innerHTML = deviceHtml + 
                `<div class="text-center mt-2">
                    <small class="text-muted">共${devices.length}个设备</small>
                </div>`;
        } else {
            this.sidebarDeviceList.innerHTML = deviceHtml;
        }
    }
    
    showNoSidebarDevices() {
        if (!this.sidebarDeviceList) return;
        
        this.sidebarDeviceList.innerHTML = `
            <div class="text-muted text-center py-2">
                <i class="fas fa-network-wired me-1"></i>
                <small>暂无设备</small>
            </div>
        `;
    }
    
    // 监听拓扑数据更新事件
    setupTopologyDataListener() {
        window.topologyStorage.onTopologyDataUpdated(() => {
            console.log('检测到拓扑数据更新，刷新侧边栏设备列表');
            this.loadSidebarDeviceList();
        });
    }
    
    async loadChatHistory() {
        try {
            // 获取当前会话的消息历史
            const response = await ApiClient.get(`/api/chat/sessions/${this.getSessionId()}/messages`);
            
            if (response.success && response.data && response.data.messages) {
                // 清空当前消息
                this.chatMessages.innerHTML = '';
                this.messageHistory = [];
                
                // 添加欢迎消息
                this.addMessage('assistant', '您好！我是ANP智能化运维平台工程助手。我可以帮助您管理和配置网络设备。请选择模式并告诉我您需要什么帮助？', null, {}, false);
                
                // 加载历史消息
                response.data.messages.forEach(msg => {
                    if (msg.role !== 'system') {
                        const type = msg.role;
                        this.addMessage(type, msg.content || '', msg.tool_calls, {}, false, msg.tool_status);
                    }
                });
                
                console.log('已加载聊天历史，消息数量:', response.data.messages.length);
            } else {
                // 没有历史消息，只显示欢迎消息
                this.chatMessages.innerHTML = '';
                this.messageHistory = [];
                this.addMessage('assistant', '您好！我是ANP智能化运维平台工程助手。我可以帮助您管理和配置网络设备。请选择模式并告诉我您需要什么帮助？', null, {}, false);
            }
            
        } catch (error) {
            console.error('加载聊天历史失败:', error);
            
            // 如果是会话不存在的错误，创建新会话
            if (error.message && error.message.includes('会话不存在')) {
                console.log('会话不存在，创建新会话');
                const created = await this.createNewSession();
                if (!created) {
                    // 创建失败，显示默认欢迎消息
                    this.chatMessages.innerHTML = '';
                    this.messageHistory = [];
                    this.addMessage('assistant', '您好！我是ANP智能化运维平台工程助手。我可以帮助您管理和配置网络设备。请选择模式并告诉我您需要什么帮助？', null, {}, false);
                }
                return;
            }
            
            // 其他错误，显示默认欢迎消息
            this.chatMessages.innerHTML = '';
            this.messageHistory = [];
            this.addMessage('assistant', '您好！我是ANP智能化运维平台工程助手。我可以帮助您管理和配置网络设备。请选择模式并告诉我您需要什么帮助？', null, {}, false);
        }
    }
    
    clearChat() {
        this.chatMessages.innerHTML = '';
        this.messageHistory = []; // 确保完全清空数组
        this.addMessage('assistant', '聊天记录已清空。我可以继续为您提供帮助。', null, {}, false);
    }
    
    // 更新模式UI
    updateModeUI() {
        if (this.currentMode === 'chat') {
            this.chatModeRadio.checked = true;
            this.buildModeRadio.checked = false;
            this.switchMode('chat');
        } else {
            this.buildModeRadio.checked = true;
            this.chatModeRadio.checked = false;
            this.switchMode('build');
        }
    }
    
    // 渲染消息列表
    renderMessages() {
        // 清空当前显示的消息
        this.chatMessages.innerHTML = '';
        
        // 重新渲染所有消息，使用addMessage方法避免代码重复
        this.messageHistory.forEach(msg => {
            // 过滤掉role为tool的消息，不进行渲染
            if (msg.role === 'tool') {
                return;
            }
            
            if (msg.type && msg.content !== undefined) {
                // 使用addMessage方法，但不保存到历史记录和云端
                this.addMessage(msg.type, msg.content || '', msg.toolCalls || null, msg.choice || {}, false, msg.tool_status || msg.toolStatus || {});
            }
        });
    }
    
    // 保存对话历史到本地文件
    saveChatHistory() {
        if (this.messageHistory.length === 0) {
            Utils.showNotification('没有对话记录可保存', 'warning');
            return;
        }
        
        const chatData = {
            timestamp: new Date().toISOString(),
            mode: this.currentMode,
            messages: this.messageHistory.filter(msg => msg.type !== 'system'), // 过滤系统消息
            totalMessages: this.messageHistory.length
        };
        
        const dataStr = JSON.stringify(chatData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `chat_history_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        Utils.showNotification('对话历史已保存到本地', 'success');
    }

    // 保存对话历史到云端
    async saveChatToCloud(syncToServer = true) {
        if (this.messageHistory.length === 0) {
            return;
        }

        const chatData = {
            timestamp: new Date().toISOString(),
            mode: this.currentMode,
            messages: this.messageHistory.filter(msg => msg.type !== 'system'),
            totalMessages: this.messageHistory.length,
            title: this.generateChatTitle()
        };

        try {
            // // 保存到浏览器本地存储
            // const savedChats = JSON.parse(localStorage.getItem('cloudChatHistory') || '[]');
            // const chatId = 'chat_' + Date.now();
            
            // savedChats.unshift({
            //     id: chatId,
            //     title: chatData.title,
            //     timestamp: chatData.timestamp,
            //     mode: chatData.mode,
            //     messageCount: chatData.totalMessages,
            //     data: chatData
            // });

            // // 限制保存的对话数量（最多保存20个）
            // if (savedChats.length > 20) {
            //     savedChats.splice(20);
            // }

            // localStorage.setItem('cloudChatHistory', JSON.stringify(savedChats));
            
            // 同步到服务器
            if (syncToServer && this.cloudSyncEnabled) {
                await this.syncChatToServer(chatData);
            }
            
            this.lastSyncTime = new Date().toISOString();
            console.log('聊天历史已保存到本地和云端');
        } catch (error) {
            console.error('保存聊天历史失败:', error);
            // 触发同步失败事件
            window.dispatchEvent(new CustomEvent('chatCloudSyncError', {
                detail: { error: error.message }
            }));
        }
    }

    // 生成对话标题
    generateChatTitle() {
        if (this.messageHistory.length === 0) return '新对话';
        
        // 找到第一条用户消息
        const firstUserMessage = this.messageHistory.find(msg => msg.type === 'user');
        if (firstUserMessage && firstUserMessage.content) {
            // 取前20个字符作为标题
            let title = firstUserMessage.content.substring(0, 20);
            if (firstUserMessage.content.length > 20) {
                title += '...';
            }
            return title;
        }
        
        return `${this.currentMode === 'chat' ? '聊天' : '构建'}对话 - ${new Date().toLocaleDateString()}`;
    }

    // 显示云端对话列表
    showCloudChatList() {
        try {
            const savedChats = JSON.parse(localStorage.getItem('cloudChatHistory') || '[]');
            
            if (savedChats.length === 0) {
                Utils.showNotification('云端暂无保存的对话', 'info');
                return;
            }

            // 创建对话列表模态框
            const modalHtml = `
                <div class="modal fade" id="cloudChatListModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="bi bi-cloud me-2"></i>
                                    云端对话历史
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="list-group" id="cloudChatList">
                                    ${savedChats.map(chat => `
                                        <div class="list-group-item list-group-item-action" data-chat-id="${chat.id}">
                                            <div class="d-flex w-100 justify-content-between">
                                                <h6 class="mb-1">${chat.title}</h6>
                                                <small class="text-muted">${new Date(chat.timestamp).toLocaleString()}</small>
                                            </div>
                                            <p class="mb-1">
                                                <span class="badge bg-${chat.mode === 'chat' ? 'primary' : 'success'} me-2">
                                                    ${chat.mode === 'chat' ? '聊天模式' : '构建模式'}
                                                </span>
                                                ${chat.messageCount} 条消息
                                            </p>
                                            <div class="btn-group btn-group-sm">
                                                <button class="btn btn-outline-primary" onclick="loadCloudChat('${chat.id}')">
                                                    <i class="bi bi-download me-1"></i>加载
                                                </button>
                                                <button class="btn btn-outline-danger" onclick="deleteCloudChat('${chat.id}')">
                                                    <i class="bi bi-trash me-1"></i>删除
                                                </button>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" onclick="clearAllCloudChats()">
                                    <i class="bi bi-trash me-1"></i>清空所有
                                </button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // 移除已存在的模态框
            const existingModal = document.getElementById('cloudChatListModal');
            if (existingModal) {
                existingModal.remove();
            }

            // 添加新的模态框
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('cloudChatListModal'));
            modal.show();

        } catch (error) {
            console.error('加载云端对话列表失败:', error);
            Utils.showNotification('加载云端对话列表失败', 'error');
        }
    }

    // 加载指定的云端对话
    loadCloudChat(chatId) {
        try {
            const savedChats = JSON.parse(localStorage.getItem('cloudChatHistory') || '[]');
            const chat = savedChats.find(c => c.id === chatId);
            
            if (!chat) {
                Utils.showNotification('对话不存在', 'error');
                return;
            }

            // 确认加载
            if (!confirm('加载对话将替换当前的聊天内容，确定要继续吗？')) {
                return;
            }

            // 清空当前对话
            this.clearChat();

            // 加载对话数据
            this.messageHistory = [...(chat.data.messages || [])]; // 使用扩展运算符创建新数组
            this.currentMode = chat.data.mode || 'chat';

            // 更新UI
            this.updateModeUI();
            this.renderMessages();

            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('cloudChatListModal'));
            if (modal) {
                modal.hide();
            }

            Utils.showNotification(`已加载对话: ${chat.title}`, 'success');

        } catch (error) {
            console.error('加载云端对话失败:', error);
            Utils.showNotification('加载云端对话失败', 'error');
        }
    }

    // 删除指定的云端对话
    deleteCloudChat(chatId) {
        try {
            if (!confirm('确定要删除这个对话吗？此操作不可撤销。')) {
                return;
            }

            const savedChats = JSON.parse(localStorage.getItem('cloudChatHistory') || '[]');
            const filteredChats = savedChats.filter(c => c.id !== chatId);
            
            localStorage.setItem('cloudChatHistory', JSON.stringify(filteredChats));
            
            // 刷新对话列表
            this.showCloudChatList();
            
            Utils.showNotification('对话已删除', 'success');

        } catch (error) {
            console.error('删除云端对话失败:', error);
            Utils.showNotification('删除云端对话失败', 'error');
        }
    }

    // 清空所有云端对话
    clearAllCloudChats() {
        try {
            if (!confirm('确定要清空所有云端对话吗？此操作不可撤销。')) {
                return;
            }

            localStorage.removeItem('cloudChatHistory');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('cloudChatListModal'));
            if (modal) {
                modal.hide();
            }
            
            Utils.showNotification('所有云端对话已清空', 'success');

        } catch (error) {
            console.error('清空云端对话失败:', error);
            Utils.showNotification('清空云端对话失败', 'error');
        }
    }
    
    // 从文件加载对话历史
    loadChatHistoryFromFile(file) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                let chatData;
                const content = e.target.result;
                
                if (file.name.endsWith('.json')) {
                    chatData = JSON.parse(content);
                } else if (file.name.endsWith('.txt')) {
                    // 简单的文本格式解析
                    chatData = this.parseTxtChatHistory(content);
                } else {
                    throw new Error('不支持的文件格式');
                }
                
                // 验证数据格式
                if (!chatData.messages || !Array.isArray(chatData.messages)) {
                    throw new Error('无效的对话文件格式');
                }
                
                // 清空当前对话
                this.chatMessages.innerHTML = '';
                this.messageHistory = [];
                
                // 添加欢迎消息
                this.addMessage('assistant', '对话历史已加载。我可以继续为您提供帮助。', null, {}, false);
                
                // 加载历史消息 - 不触发云同步
                chatData.messages.forEach(msg => {
                    if (msg.type && msg.content !== undefined) {
                        this.addMessage(msg.type, msg.content, msg.toolCalls || null, msg.choice || {}, false);
                    }
                });
                
                // 如果有模式信息，切换到对应模式
                if (chatData.mode && chatData.mode !== this.currentMode) {
                    this.switchMode(chatData.mode);
                    if (chatData.mode === 'chat') {
                        this.chatModeRadio.checked = true;
                    } else {
                        this.buildModeRadio.checked = true;
                    }
                }
                
                Utils.showNotification(`成功加载 ${chatData.messages.length} 条对话记录`, 'success');
                
            } catch (error) {
                console.error('加载对话历史失败:', error);
                Utils.showNotification(`加载对话失败: ${error.message}`, 'error');
            }
        };
        
        reader.onerror = () => {
            Utils.showNotification('读取文件失败', 'error');
        };
        
        reader.readAsText(file);
    }
    
    // 解析TXT格式的对话历史
    parseTxtChatHistory(content) {
        const lines = content.split('\n');
        const messages = [];
        let currentMessage = null;
        
        for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;
            
            // 检查是否是新消息的开始
            const userMatch = trimmedLine.match(/^\[用户\]\s*(.*)$/);
            const assistantMatch = trimmedLine.match(/^\[AI\]\s*(.*)$/);
            const systemMatch = trimmedLine.match(/^\[系统\]\s*(.*)$/);
            
            if (userMatch) {
                if (currentMessage) messages.push(currentMessage);
                currentMessage = {
                    type: 'user',
                    content: userMatch[1],
                    timestamp: new Date().toISOString()
                };
            } else if (assistantMatch) {
                if (currentMessage) messages.push(currentMessage);
                currentMessage = {
                    type: 'assistant',
                    content: assistantMatch[1],
                    timestamp: new Date().toISOString()
                };
            } else if (systemMatch) {
                if (currentMessage) messages.push(currentMessage);
                currentMessage = {
                    type: 'system',
                    content: systemMatch[1],
                    timestamp: new Date().toISOString()
                };
            } else if (currentMessage) {
                // 继续当前消息的内容
                currentMessage.content += '\n' + trimmedLine;
            }
        }
        
        if (currentMessage) messages.push(currentMessage);
        
        return {
            timestamp: new Date().toISOString(),
            mode: 'chat',
            messages: messages,
            totalMessages: messages.length
        };
    }
}

// 全局函数
function sendQuickMessage(message) {
    if (window.chatManager) {
        window.chatManager.messageInput.value = message;
        window.chatManager.sendMessage();
    }
}

function switchMode(mode) {
    if (window.chatManager) {
        if (mode === 'chat') {
            window.chatManager.chatModeRadio.checked = true;
        } else {
            window.chatManager.buildModeRadio.checked = true;
        }
        window.chatManager.switchMode(mode);
    }
}

function clearChat() {
    if (window.chatManager) {
        window.chatManager.clearChat();
    }
}

function loadChatHistory() {
    if (window.chatManager) {
        // 显示加载对话模态框
        const loadChatModal = new bootstrap.Modal(document.getElementById('loadChatModal'));
        loadChatModal.show();
    }
}

// 保存对话历史
function saveChatHistory() {
    if (window.chatManager) {
        window.chatManager.saveChatHistory();
    }
}

function saveChatToCloud() {
    if (window.chatManager) {
        window.chatManager.saveChatToCloud();
    }
}

function loadChatFromCloud() {
    if (window.chatManager) {
        window.chatManager.showCloudChatList();
    }
}

function loadCloudChat(chatId) {
    if (window.chatManager) {
        window.chatManager.loadCloudChat(chatId);
    }
}

function deleteCloudChat(chatId) {
    if (window.chatManager) {
        window.chatManager.deleteCloudChat(chatId);
    }
}

function clearAllCloudChats() {
    if (window.chatManager) {
        window.chatManager.clearAllCloudChats();
    }
}

// 从文件加载对话
function loadChatFromFile() {
    const fileInput = document.getElementById('chatFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        Utils.showNotification('请选择一个文件', 'warning');
        return;
    }
    
    if (window.chatManager) {
        window.chatManager.loadChatHistoryFromFile(file);
        
        // 关闭模态框
        const loadChatModal = bootstrap.Modal.getInstance(document.getElementById('loadChatModal'));
        if (loadChatModal) {
            loadChatModal.hide();
        }
        
        // 清空文件输入
        fileInput.value = '';
    }
}

// 扩展ChatManager类的云端同步方法
// 加载聊天历史


// 保存聊天到云端
ChatManager.prototype.saveChatToCloud = async function() {
    try {
        const chatData = {
            session_id: this.getSessionId(),
            messages: this.messageHistory,
            mode: this.currentMode,
            timestamp: new Date().toISOString()
        };
        
        try {
            await ApiClient.put(`/api/chat/sessions/${this.getSessionId()}`, chatData);
        } catch (error) {
            // 如果会话不存在，先创建会话再重试
             if (error.message && error.message.includes('会话不存在')) {
                 console.log('会话不存在，创建新会话后重试保存');
                 const created = await this.createNewSession();
                 if (!created) {
                     throw new Error('无法创建新会话，保存失败');
                 }
                 await ApiClient.put(`/api/chat/sessions/${this.getSessionId()}`, chatData);
             } else {
                 throw error;
             }
        }
        this.lastSyncTime = new Date();
    } catch (error) {
        console.error('保存聊天历史失败:', error);
    }
};

ChatManager.prototype.syncChatToServer = async function(chatData) {
    try {
        let response;
        try {
            response = await ApiClient.put(`/api/chat/sessions/${this.getSessionId()}`, {
                messages: chatData.messages,
                mode: chatData.mode,
                timestamp: chatData.timestamp
            });
        } catch (error) {
            // 如果会话不存在，先创建会话再重试
             if (error.message && error.message.includes('会话不存在')) {
                 console.log('会话不存在，创建新会话后重试同步');
                 const created = await this.createNewSession();
                 if (!created) {
                     throw new Error('无法创建新会话，同步失败');
                 }
                 response = await ApiClient.put(`/api/chat/sessions/${this.getSessionId()}`, {
                     messages: chatData.messages,
                     mode: chatData.mode,
                     timestamp: chatData.timestamp
                 });
             } else {
                 throw error;
             }
        }
        
        // 触发同步成功事件
        window.dispatchEvent(new CustomEvent('chatCloudSyncSuccess', {
            detail: { timestamp: chatData.timestamp }
        }));
        
        return response;
    } catch (error) {
        console.error('同步聊天历史到服务器失败:', error);
        throw error;
    }
};

ChatManager.prototype.loadChatFromServer = async function() {
    try {
        const response = await ApiClient.get(`/api/chat/sessions/${this.getSessionId()}`);
        
        if (response.success && response.data && response.data.messages) {
            // 触发云端数据加载事件
            window.dispatchEvent(new CustomEvent('chatCloudDataLoaded', {
                detail: { data: response.data }
            }));
            
            return response.data;
        }
        
        return null;
    } catch (error) {
        // 如果会话不存在，尝试创建新会话
        if (error.message && error.message.includes('会话不存在')) {
            console.log('会话不存在，创建新会话');
            const created = await this.createNewSession();
            if (!created) {
                console.error('无法创建新会话');
            }
            return null;
        }
        console.error('从服务器加载聊天历史失败:', error);
        return null;
    }
};

ChatManager.prototype.createNewSession = async function() {
    try {
        const response = await ApiClient.post('/api/chat/sessions', {
            title: '新对话',
            mode: this.currentMode || 'chat'
        });
        
        if (response.success && response.data) {
            // 更新会话ID
            this.sessionId = response.data.session_id;
            const userId = this.currentUser ? this.currentUser.id : 'anonymous';
            localStorage.setItem(`chat_session_id_${userId}`, this.sessionId);
            console.log('新会话创建成功:', this.sessionId);
            
            // 更新UI显示
            this.updateSessionDisplay();
            
            // 清空当前聊天
            this.clearChat();
            
            return true;
        } else {
            console.error('创建会话失败: 服务器返回错误');
            return false;
        }
    } catch (error) {
        console.error('创建新会话失败:', error);
        return false;
    }
}

// 更新会话显示信息
ChatManager.prototype.updateSessionDisplay = function() {
    const sessionDisplay = document.getElementById('currentSessionDisplay');
    const messageCount = document.getElementById('messageCount');
    
    if (sessionDisplay && this.sessionId) {
        sessionDisplay.textContent = this.sessionId.substring(0, 8) + '...';
    }
    
    if (messageCount) {
        messageCount.textContent = this.messageHistory.length;
    }
}

// 显示会话列表
ChatManager.prototype.showSessionList = async function() {
    const modal = new bootstrap.Modal(document.getElementById('sessionListModal'));
    modal.show();
    
    // 加载会话列表
    await this.loadSessionList();
}

// 加载会话列表
ChatManager.prototype.loadSessionList = async function() {
    const container = document.getElementById('sessionListContainer');
    
    try {
        const response = await ApiClient.get('/api/chat/sessions');
        
        if (response.success && response.data) {
            const sessions = Array.isArray(response.data) ? response.data : (response.data.sessions || []);
            
            if (sessions.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-chat-square-text text-muted" style="font-size: 3rem;"></i>
                        <p class="mt-2 text-muted">暂无会话记录</p>
                        <button class="btn btn-primary" onclick="chatManager.createNewSessionFromModal()">
                            <i class="bi bi-plus-circle me-1"></i>创建第一个会话
                        </button>
                    </div>
                `;
                return;
            }
            
            let html = '';
            sessions.forEach(session => {
                const isActive = session.session_id === this.sessionId;
                const createdAt = new Date(session.created_at).toLocaleString('zh-CN');
                const messageCount = session.message_count || 0;
                
                html += `
                    <div class="card mb-2 ${isActive ? 'border-primary' : ''}">
                        <div class="card-body p-3">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    <h6 class="card-title mb-1">
                                        ${session.title || '未命名会话'}
                                        ${isActive ? '<span class="badge bg-primary ms-2">当前</span>' : ''}
                                    </h6>
                                    <p class="card-text small text-muted mb-1">
                                        会话ID: ${session.session_id.substring(0, 8)}...
                                    </p>
                                    <p class="card-text small text-muted mb-0">
                                        创建时间: ${createdAt} | 消息数: ${messageCount}
                                    </p>
                                </div>
                                <div class="btn-group-vertical btn-group-sm">
                                    ${!isActive ? `<button class="btn btn-outline-primary" onclick="chatManager.switchToSession('${session.session_id}')" title="切换到此会话">
                                        <i class="bi bi-arrow-right-circle"></i>
                                    </button>` : ''}
                                    <button class="btn btn-outline-danger" onclick="chatManager.deleteSession('${session.session_id}')" title="删除会话">
                                        <i class="bi bi-trash3"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } else {
            throw new Error('获取会话列表失败');
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                加载会话列表失败: ${error.message}
            </div>
        `;
    }
}

// 切换到指定会话
ChatManager.prototype.switchToSession = async function(sessionId) {
    try {
        // 更新会话ID
        this.sessionId = sessionId;
        const userId = this.currentUser ? this.currentUser.id : 'anonymous';
        localStorage.setItem(`chat_session_id_${userId}`, sessionId);
        
        // 更新UI显示
        this.updateSessionDisplay();
        
        // 加载会话历史
        await this.loadChatHistory();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('sessionListModal'));
        if (modal) {
            modal.hide();
        }
        
        console.log('已切换到会话:', sessionId);
    } catch (error) {
        console.error('切换会话失败:', error);
        alert('切换会话失败: ' + error.message);
    }
}

// 删除指定会话
ChatManager.prototype.deleteSession = async function(sessionId) {
    if (!confirm('确定要删除这个会话吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        const response = await ApiClient.delete(`/api/chat/sessions/${sessionId}`);
        
        if (response.success) {
            // 如果删除的是当前会话，创建新会话
            if (sessionId === this.sessionId) {
                await this.createNewSession();
            }
            
            // 重新加载会话列表
            await this.loadSessionList();
            
            console.log('会话删除成功:', sessionId);
        } else {
            throw new Error('删除会话失败');
        }
    } catch (error) {
        console.error('删除会话失败:', error);
        alert('删除会话失败: ' + error.message);
    }
}

// 删除当前会话
ChatManager.prototype.deleteCurrentSession = async function() {
    if (!this.sessionId) {
        alert('当前没有活动会话');
        return;
    }
    
    await this.deleteSession(this.sessionId);
}

// 清空所有会话
ChatManager.prototype.clearAllSessions = async function() {
    if (!confirm('确定要清空所有会话吗？此操作不可撤销，将删除所有聊天记录。')) {
        return;
    }
    
    try {
        const response = await ApiClient.delete('/api/chat/sessions');
        
        if (response.success) {
            // 创建新会话
            await this.createNewSession();
            
            // 重新加载会话列表
            await this.loadSessionList();
            
            console.log('所有会话已清空');
        } else {
            throw new Error('清空会话失败');
        }
    } catch (error) {
        console.error('清空所有会话失败:', error);
        alert('清空会话失败: ' + error.message);
    }
}

// 从模态框创建新会话
ChatManager.prototype.createNewSessionFromModal = async function() {
    const success = await this.createNewSession();
    if (success) {
        // 重新加载会话列表
        await this.loadSessionList();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('sessionListModal'));
        if (modal) {
            modal.hide();
        }
    }
}


ChatManager.prototype.initializeChatFromCloud = async function() {
    // 尝试从服务器加载聊天历史
    const cloudData = await this.loadChatFromServer();
    
    if (cloudData && cloudData.messages && cloudData.messages.length > 0) {
        // 清空当前消息
        this.chatMessages.innerHTML = '';
        this.messageHistory = [];
        
        // 添加欢迎消息
        this.addMessage('assistant', '您好！我是ANP智能化运维平台工程助手。我可以帮助您管理和配置网络设备。请选择模式并告诉我您需要什么帮助？');
        
        // 加载最近的消息（最多10条）
        const recentMessages = cloudData.messages.slice(-10);
        recentMessages.forEach(msg => {
            if (msg.type !== 'system') {
                this.addMessage(msg.type, msg.content || '', msg.tool_calls, {}, false, msg.tool_status);
            }
        });
        
        // 更新模式
        if (cloudData.mode) {
            this.switchMode(cloudData.mode);
            document.getElementById(cloudData.mode + 'Mode').checked = true;
        }
        
        console.log('已从云端加载聊天历史');
        return true;
    }
    
    return false;
};

function loadNetworkStatus() {
    networkStatusManager.getStatus().catch(error => {
        console.error('加载网络状态失败:', error);
    });
}

// 全局函数，供HTML调用
function createNewSession() {
    if (window.chatManager) {
        return window.chatManager.createNewSession();
    }
}

function showSessionList() {
    if (window.chatManager) {
        return window.chatManager.showSessionList();
    }
}

function deleteCurrentSession() {
    if (window.chatManager) {
        return window.chatManager.deleteCurrentSession();
    }
}

function clearAllSessions() {
    if (window.chatManager) {
        return window.chatManager.clearAllSessions();
    }
}

function createNewSessionFromModal() {
    if (window.chatManager) {
        return window.chatManager.createNewSessionFromModal();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    window.chatManager = new ChatManager();
    
    // 开始自动更新网络状态 (每2分钟更新一次)
    networkStatusManager.startAutoUpdate(120000);
    
    // 初始加载网络状态
    loadNetworkStatus();
    
    // 延迟更新会话显示，确保DOM已完全加载
    setTimeout(() => {
        if (window.chatManager) {
            window.chatManager.updateSessionDisplay();
        }
    }, 100);
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (networkStatusManager) {
        networkStatusManager.stopAutoUpdate();
    }
});
