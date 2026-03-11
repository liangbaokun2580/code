// 设置页面JavaScript

class SettingsManager {
    constructor() {
        this.currentUser = null;
        this.currentSection = 'profile';
        this.init();
    }

    async init() {
        await this.loadUserInfo();
        this.setupEventListeners();
        this.showSection('profile');
        // 模型配置初始化已移除
    }

    // 加载用户信息
    async loadUserInfo() {
        try {
            const response = await fetch('/api/user/info');
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.currentUser = result.data;
                    this.updateUserDisplay();
                    this.checkAdminAccess();
                } else {
                    console.error('Failed to load user info:', result.error || 'Unknown error');
                    window.location.href = '/login';
                }
            } else {
                console.error('Failed to load user info');
                window.location.href = '/login';
            }
        } catch (error) {
            console.error('Error loading user info:', error);
            this.showMessage('加载用户信息失败', 'error');
        }
    }

    // 更新用户显示信息
    updateUserDisplay() {
        if (!this.currentUser) return;

        // 更新导航栏用户名
        const usernameElement = document.getElementById('currentUsername');
        if (usernameElement) {
            usernameElement.textContent = this.currentUser.username;
        }

        // 显示用户区域
        const userSection = document.getElementById('userSection');
        const authSection = document.getElementById('authSection');
        if (userSection && authSection) {
            userSection.style.display = 'block';
            authSection.style.display = 'none';
        }

        // 填充个人资料表单
        this.fillProfileForm();
    }

    // 检查管理员权限
    checkAdminAccess() {
        const systemConfigNav = document.getElementById('systemConfigNav');
        if (systemConfigNav) {
            if (this.currentUser && this.currentUser.is_admin === true) {
                systemConfigNav.style.display = 'block';
                console.log('Admin access granted - showing system config');
            } else {
                systemConfigNav.style.display = 'none';
                console.log('Admin access denied - hiding system config', {
                    user: this.currentUser,
                    is_admin: this.currentUser ? this.currentUser.is_admin : 'no user'
                });
            }
        }
    }

    // 填充个人资料表单
    fillProfileForm() {
        if (!this.currentUser) return;

        document.getElementById('username').value = this.currentUser.username || '';
        document.getElementById('email').value = this.currentUser.email || '';
        
        // 格式化日期
        if (this.currentUser.created_at) {
            const createdDate = new Date(this.currentUser.created_at);
            document.getElementById('createdAt').value = createdDate.toLocaleString('zh-CN');
        }
        
        if (this.currentUser.last_login) {
            const lastLoginDate = new Date(this.currentUser.last_login);
            document.getElementById('lastLogin').value = lastLoginDate.toLocaleString('zh-CN');
        } else {
            document.getElementById('lastLogin').value = '从未登录';
        }
    }

    // 设置事件监听器
    setupEventListeners() {
        // 导航菜单点击事件
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.showSection(section);
            });
        });
        
        // 个人资料表单提交
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveProfile();
            });
        }
        
        // 安全设置表单提交
        const securityForm = document.getElementById('securityForm');
        if (securityForm) {
            securityForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.changePassword();
            });
        }
        
        // 偏好设置表单提交
        const preferencesForm = document.getElementById('preferencesForm');
        if (preferencesForm) {
            preferencesForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.savePreferences();
            });
        }
        
        // 模型配置相关事件已移除
    }

    // 显示指定设置区域
    showSection(sectionName) {
        // 隐藏所有区域
        document.querySelectorAll('.settings-section').forEach(section => {
            section.style.display = 'none';
        });

        // 移除所有导航链接的active类
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // 显示指定区域
        const targetSection = document.getElementById(sectionName + 'Section');
        if (targetSection) {
            targetSection.style.display = 'block';
        }

        // 激活对应导航链接
        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // 更新页面标题
        this.updatePageTitle(sectionName);

        // 如果是系统配置，加载配置内容
        if (sectionName === 'system') {
            this.loadSystemConfig();
            // 模型配置功能已移除
        }

        this.currentSection = sectionName;
    }

    // 更新页面标题
    updatePageTitle(sectionName) {
        const titles = {
            'profile': '个人资料',
            'account': '账户安全',
            'preferences': '偏好设置',
            'system': '系统配置'
        };
        
        const titleElement = document.getElementById('pageTitle');
        if (titleElement) {
            titleElement.textContent = titles[sectionName] || '设置';
        }
    }

    // 更新个人资料
    async updateProfile() {
        const email = document.getElementById('email').value;
        
        if (!this.validateEmail(email)) {
            this.showMessage('请输入有效的邮箱地址', 'error');
            return;
        }

        try {
            const response = await fetch('/api/user/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });

            if (response.ok) {
                this.showMessage('个人资料更新成功', 'success');
                await this.loadUserInfo(); // 重新加载用户信息
            } else {
                const error = await response.json();
                this.showMessage(error.message || '更新失败', 'error');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            this.showMessage('更新个人资料失败', 'error');
        }
    }

    // 修改密码
    async changePassword() {
        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // 验证密码
        if (!this.validatePassword(newPassword)) {
            this.showMessage('密码长度至少8位，包含字母和数字', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            this.showMessage('两次输入的密码不一致', 'error');
            return;
        }

        try {
            const response = await fetch('/api/user/password', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (response.ok) {
                this.showMessage('密码修改成功', 'success');
                document.getElementById('passwordForm').reset();
            } else {
                const error = await response.json();
                this.showMessage(error.message || '密码修改失败', 'error');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showMessage('密码修改失败', 'error');
        }
    }

    // 保存偏好设置
    async savePreferences() {
        const theme = document.querySelector('input[name="theme"]:checked').value;
        const language = document.getElementById('language').value;
        const notifications = document.getElementById('notifications').checked;

        const preferences = {
            theme,
            language,
            notifications
        };

        try {
            const response = await fetch('/api/user/preferences', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(preferences)
            });

            if (response.ok) {
                this.showMessage('偏好设置保存成功', 'success');
                this.applyTheme(theme);
                localStorage.setItem('userPreferences', JSON.stringify(preferences));
            } else {
                const error = await response.json();
                this.showMessage(error.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('Error saving preferences:', error);
            this.showMessage('保存偏好设置失败', 'error');
        }
    }

    // 加载系统配置
    async loadSystemConfig() {
        if (!this.currentUser || !this.currentUser.is_admin) {
            document.getElementById('systemConfigContainer').innerHTML = 
                '<div class="alert alert-warning">您没有权限访问系统配置</div>';
            return;
        }

        try {
            const response = await fetch('/api/settings/config-form');
            if (response.ok) {
                const html = await response.text();
                document.getElementById('systemConfigContainer').innerHTML = html;
                // 重新绑定配置表单事件
                this.setupConfigFormEvents();
            } else {
                document.getElementById('systemConfigContainer').innerHTML = 
                    '<div class="alert alert-danger">无法加载系统配置</div>';
            }
        } catch (error) {
            console.error('Error loading system config:', error);
            document.getElementById('systemConfigContainer').innerHTML = 
                '<div class="alert alert-danger">加载系统配置时发生错误</div>';
        }
    }

    // 设置配置表单事件
    setupConfigFormEvents() {
        const configForm = document.getElementById('configForm');
        if (configForm) {
            // 加载原有的config.js逻辑
            const script = document.createElement('script');
            script.src = '/static/js/config.js';
            document.head.appendChild(script);
        }
    }

    // 应用主题
    applyTheme(theme) {
        const body = document.body;
        body.classList.remove('theme-light', 'theme-dark', 'theme-auto');
        
        if (theme === 'dark') {
            body.classList.add('theme-dark');
        } else if (theme === 'light') {
            body.classList.add('theme-light');
        } else {
            body.classList.add('theme-auto');
        }
    }
    
    // 初始化模型配置
    initializeModelConfig() {
        // 模型配置功能已移除
        console.log('模型配置功能已移除');
    }
    
    // 模型配置相关方法已移除

    // 验证邮箱
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // 验证密码
    validatePassword(password) {
        // 至少8位，包含字母和数字
        const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/;
        return passwordRegex.test(password);
    }

    // 显示消息
    showMessage(message, type = 'info') {
        const toast = document.getElementById('messageToast');
        const toastMessage = document.getElementById('toastMessage');
        const toastHeader = toast.querySelector('.toast-header');
        
        if (toastMessage && toastHeader) {
            toastMessage.textContent = message;
            
            // 更新图标和颜色
            const icon = toastHeader.querySelector('i');
            icon.className = 'me-2 ';
            
            switch (type) {
                case 'success':
                    icon.className += 'fas fa-check-circle text-success';
                    break;
                case 'error':
                    icon.className += 'fas fa-exclamation-circle text-danger';
                    break;
                case 'warning':
                    icon.className += 'fas fa-exclamation-triangle text-warning';
                    break;
                default:
                    icon.className += 'fas fa-info-circle text-info';
            }
            
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        }
    }
}

// 登出函数
async function logout() {
    try {
        // 调用后端登出API
        await fetch('/auth/logout', {
            method: 'GET',
            credentials: 'include'
        });
    } catch (error) {
        console.error('登出请求失败:', error);
    } finally {
        // 无论API调用是否成功，都清除本地存储并跳转
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new SettingsManager();
});