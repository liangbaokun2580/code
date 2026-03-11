// 主要JavaScript文件 - 通用功能

// 全局变量
window.AppConfig = {
    apiBaseUrl: '',
    wsUrl: window.location.protocol === 'https:' ? 'wss://' : 'ws://' + window.location.host,
    version: '1.0.0'
};

// 工具函数
class Utils {
    // 显示通知
    static showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // 自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    // 显示加载状态
    static showLoading(element, text = '加载中...') {
        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            ${text}
        `;
        element.disabled = true;
    }
    
    // 隐藏加载状态
    static hideLoading(element) {
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
        element.disabled = false;
    }
    
    // 格式化时间
    static formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // 小于1分钟
            return '刚刚';
        } else if (diff < 3600000) { // 小于1小时
            return `${Math.floor(diff / 60000)}分钟前`;
        } else if (diff < 86400000) { // 小于1天
            return `${Math.floor(diff / 3600000)}小时前`;
        } else {
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }
    
    // 复制到剪贴板
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('已复制到剪贴板', 'success', 2000);
        } catch (err) {
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showNotification('已复制到剪贴板', 'success', 2000);
        }
    }
    
    // 防抖函数
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // 节流函数
    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // 验证IP地址
    static isValidIP(ip) {
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipRegex.test(ip);
    }
    
    // 验证端口号
    static isValidPort(port) {
        const portNum = parseInt(port);
        return portNum >= 1 && portNum <= 65535;
    }
    
    // 格式化文件大小
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 生成随机ID
    static generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }
}

// API客户端
class ApiClient {
    static getAuthToken() {
        return localStorage.getItem('auth_token');
    }
    
    static setAuthToken(token) {
        localStorage.setItem('auth_token', token);
    }
    
    static removeAuthToken() {
        localStorage.removeItem('auth_token');
    }
    
    static isAuthenticated() {
        return !!this.getAuthToken();
    }
    
    static async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        // 添加认证头
        const token = this.getAuthToken();
        if (token) {
            defaultOptions.headers['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };
        
        try {
            // Normalize URL to avoid relative-path 404s when running under /chat
            let requestUrl = url;
            if (!/^https?:\/\//i.test(requestUrl)) {
                const normalizedUrl = requestUrl.startsWith('/') ? requestUrl : `/${requestUrl}`;
                const base = AppConfig.apiBaseUrl ? AppConfig.apiBaseUrl.replace(/\/$/, '') : '';
                requestUrl = base ? base + normalizedUrl : normalizedUrl;
            }
            const response = await fetch(requestUrl, config);
            
            // 处理401未授权错误
            if (response.status === 401) {
                this.removeAuthToken();
                window.location.href = '/login';
                throw new Error('认证失败，请重新登录');
            }
            
            let data = null;
            try {
                data = await response.json();
            } catch (e) {
                // Non-JSON response
            }

            if (!response.ok) {
                const msg = (data && (data.error || data.message))
                    ? (data.error || data.message)
                    : `HTTP error! status: ${response.status}`;
                const err = new Error(msg);
                err.status = response.status;
                err.response = data;
                throw err;
            }
            
            if (data && data.success === false) {
                const err = new Error(data.error || '请求失败');
                err.status = response.status;
                err.response = data;
                throw err;
            }
            
            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }
    
    static async get(url) {
        return this.request(url, { method: 'GET' });
    }
    
    static async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }
    
    static async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }
    
    static async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
}

// 网络状态管理
class NetworkStatusManager {
    constructor() {
        this.status = null;
        this.listeners = [];
        this.updateInterval = null;
    }
    
    // 添加状态监听器
    addListener(callback) {
        this.listeners.push(callback);
    }
    
    // 移除状态监听器
    removeListener(callback) {
        const index = this.listeners.indexOf(callback);
        if (index > -1) {
            this.listeners.splice(index, 1);
        }
    }
    
    // 通知所有监听器
    notifyListeners() {
        this.listeners.forEach(callback => {
            try {
                callback(this.status);
            } catch (error) {
                console.error('状态监听器错误:', error);
            }
        });
    }
    
    // 获取网络状态
    async getStatus() {
        try {
            const response = await ApiClient.get('/api/network/status');
            this.status = response.data;
            this.notifyListeners();
            return this.status;
        } catch (error) {
            console.error('获取网络状态失败:', error);
            throw error;
        }
    }
    
    // 开始自动更新
    startAutoUpdate(interval = 30000) {
        this.stopAutoUpdate();
        this.updateInterval = setInterval(() => {
            this.getStatus().catch(error => {
                console.error('自动更新网络状态失败:', error);
            });
        }, interval);
    }
    
    // 停止自动更新
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// 全局实例
window.networkStatusManager = new NetworkStatusManager();

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 添加全局错误处理
    window.addEventListener('error', function(event) {
        console.error('全局错误:', event.error);
        // 可以在这里添加错误报告逻辑
    });
    
    // 添加未处理的Promise拒绝处理
    window.addEventListener('unhandledrejection', function(event) {
        console.error('未处理的Promise拒绝:', event.reason);
        // 可以在这里添加错误报告逻辑
    });
    
    // 检查浏览器兼容性
    if (!window.fetch) {
        Utils.showNotification('您的浏览器版本过低，可能无法正常使用所有功能', 'warning', 5000);
    }
    
    // 添加键盘快捷键
    document.addEventListener('keydown', function(event) {
        // Ctrl+/ 显示帮助
        if (event.ctrlKey && event.key === '/') {
            event.preventDefault();
            showHelp();
        }
        
        // ESC 关闭模态框
        if (event.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
});

// 显示帮助信息
function showHelp() {
    const helpContent = `
        <div class="help-content">
            <h5><i class="fas fa-keyboard me-2"></i>键盘快捷键</h5>
            <ul class="list-unstyled">
                <li><kbd>Ctrl</kbd> + <kbd>/</kbd> - 显示帮助</li>
                <li><kbd>Esc</kbd> - 关闭模态框</li>
                <li><kbd>Enter</kbd> - 发送消息（聊天页面）</li>
                <li><kbd>Shift</kbd> + <kbd>Enter</kbd> - 换行（聊天页面）</li>
                <li><kbd>Ctrl</kbd> + <kbd>Enter</kbd> - 运行代码（开发页面）</li>
            </ul>
            
            <h5><i class="fas fa-info-circle me-2"></i>功能说明</h5>
            <ul class="list-unstyled">
                <li><strong>聊天模式：</strong>查看网络状态，获取配置信息</li>
                <li><strong>构建模式：</strong>修改网络配置，管理设备</li>
                <li><strong>SDK开发：</strong>使用Python编写网络管理脚本</li>
            </ul>
        </div>
    `;
    
    // 创建模态框
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-question-circle me-2"></i>
                        帮助信息
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    ${helpContent}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // 模态框关闭后移除元素
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
}

// 导出工具类供其他模块使用
window.Utils = Utils;
window.ApiClient = ApiClient;
window.NetworkStatusManager = NetworkStatusManager;

// 添加一些全局样式类的动态应用
function addDynamicStyles() {
    // 为所有按钮添加点击效果
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('btn')) {
            event.target.style.transform = 'scale(0.98)';
            setTimeout(() => {
                event.target.style.transform = '';
            }, 100);
        }
    });
    
    // 为输入框添加焦点效果
    document.addEventListener('focusin', function(event) {
        if (event.target.classList.contains('form-control')) {
            event.target.parentElement.classList.add('focused');
        }
    });
    
    document.addEventListener('focusout', function(event) {
        if (event.target.classList.contains('form-control')) {
            event.target.parentElement.classList.remove('focused');
        }
    });
}

// 页面加载完成后添加动态样式
document.addEventListener('DOMContentLoaded', addDynamicStyles);
