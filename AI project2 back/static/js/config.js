// 配置页面JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const useLocalModelToggle = document.getElementById('use_local_model');
    const localModelConfigs = document.querySelectorAll('.local-model-config');
    const openaiConfigs = document.querySelectorAll('.openai-config');
    const configForm = document.getElementById('configForm');
    
    // 初始化显示状态
    toggleModelConfigs();
    
    // 监听本地模型开关变化
    if (useLocalModelToggle) {
        useLocalModelToggle.addEventListener('change', toggleModelConfigs);
    }
    
    // 切换模型配置显示
    function toggleModelConfigs() {
        const useLocal = useLocalModelToggle && useLocalModelToggle.checked;
        
        localModelConfigs.forEach(config => {
            config.style.display = useLocal ? 'flex' : 'none';
        });
        
        openaiConfigs.forEach(config => {
            config.style.display = useLocal ? 'none' : 'flex';
        });
    }
    
    // 表单提交处理
    if (configForm) {
        configForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 显示加载状态
            const submitBtn = configForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
            submitBtn.disabled = true;
            
            // 验证表单
            if (!validateForm()) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                return;
            }
            
            // 提交表单数据
            const formData = new FormData(configForm);
            
            fetch(configForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('配置保存成功！', 'success');
                    // 可选：重新加载页面以显示更新后的配置
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert(data.message || '保存配置时发生错误', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('网络错误，请稍后重试', 'error');
            })
            .finally(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
    }
    
    // 表单验证
    function validateForm() {
        const useLocal = useLocalModelToggle && useLocalModelToggle.checked;
        let isValid = true;
        
        // 清除之前的错误状态
        document.querySelectorAll('.form-control.error').forEach(el => {
            el.classList.remove('error');
        });
        
        if (useLocal) {
            // 验证本地模型配置
            const localBaseUrl = document.getElementById('local_model_base_url');
            const localModelName = document.getElementById('local_model_name');
            
            if (!localBaseUrl.value.trim()) {
                showFieldError(localBaseUrl, '请输入本地模型API地址');
                isValid = false;
            } else if (!isValidUrl(localBaseUrl.value.trim())) {
                showFieldError(localBaseUrl, '请输入有效的URL地址');
                isValid = false;
            }
            
            if (!localModelName.value.trim()) {
                showFieldError(localModelName, '请输入本地模型名称');
                isValid = false;
            }
        } else {
            // 验证OpenAI配置
            const apiKey = document.getElementById('openai_api_key');
            const apiBase = document.getElementById('openai_api_base');
            const model = document.getElementById('openai_model');
            
            if (!apiKey.value.trim()) {
                showFieldError(apiKey, '请输入OpenAI API Key');
                isValid = false;
            }
            
            if (apiBase.value.trim() && !isValidUrl(apiBase.value.trim())) {
                showFieldError(apiBase, '请输入有效的API Base URL');
                isValid = false;
            }
            
            if (!model.value.trim()) {
                showFieldError(model, '请输入模型名称');
                isValid = false;
            }
        }
        
        // 验证数据库URI
        const databaseUri = document.getElementById('database_uri');
        if (!databaseUri.value.trim()) {
            showFieldError(databaseUri, '请输入数据库连接字符串');
            isValid = false;
        }
        
        // 验证Redis URL
        const redisUrl = document.getElementById('redis_url');
        if (!redisUrl.value.trim()) {
            showFieldError(redisUrl, '请输入Redis连接URL');
            isValid = false;
        }
        
        return isValid;
    }
    
    // 显示字段错误
    function showFieldError(field, message) {
        field.classList.add('error');
        
        // 移除之前的错误消息
        const existingError = field.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // 添加新的错误消息
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = '#dc3545';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.marginTop = '5px';
        field.parentNode.appendChild(errorDiv);
    }
    
    // URL验证
    function isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
    
    // 显示提示消息
    function showAlert(message, type = 'info') {
        // 移除现有的alert
        const existingAlert = document.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        
        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-triangle' : 'info-circle';
        
        alertDiv.innerHTML = `
            <i class="fas fa-${icon}"></i>
            ${message}
        `;
        
        const mainContent = document.querySelector('.main-content');
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
        
        // 自动隐藏成功消息
        if (type === 'success') {
            setTimeout(() => {
                alertDiv.remove();
            }, 3000);
        }
    }
});

// 重置表单
function resetForm() {
    if (confirm('确定要重置所有配置吗？这将恢复到默认值。')) {
        document.getElementById('configForm').reset();
        
        // 重新触发切换逻辑
        const useLocalModelToggle = document.getElementById('use_local_model');
        if (useLocalModelToggle) {
            useLocalModelToggle.dispatchEvent(new Event('change'));
        }
        
        // 清除错误状态
        document.querySelectorAll('.form-control.error').forEach(el => {
            el.classList.remove('error');
        });
        document.querySelectorAll('.error-message').forEach(el => {
            el.remove();
        });
    }
}

// 测试连接
function testConnection() {
    const useLocal = document.getElementById('use_local_model').checked;
    const testBtn = document.querySelector('.btn-info');
    const originalText = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 测试中...';
    testBtn.disabled = true;
    
    const testData = {
        use_local: useLocal
    };
    
    if (useLocal) {
        testData.local_base_url = document.getElementById('local_model_base_url').value;
        testData.local_model_name = document.getElementById('local_model_name').value;
    } else {
        testData.api_key = document.getElementById('openai_api_key').value;
        testData.api_base = document.getElementById('openai_api_base').value;
        testData.model = document.getElementById('openai_model').value;
    }
    
    fetch('/api/test-ai-connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('AI模型连接测试成功！', 'success');
        } else {
            showAlert(data.message || 'AI模型连接测试失败', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('测试连接时发生网络错误', 'error');
    })
    .finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// 显示提示消息的全局函数
function showAlert(message, type = 'info') {
    // 移除现有的alert
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    
    const icon = type === 'success' ? 'check-circle' : 
                type === 'error' ? 'exclamation-triangle' : 'info-circle';
    
    alertDiv.innerHTML = `
        <i class="fas fa-${icon}"></i>
        ${message}
    `;
    
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alertDiv, mainContent.firstChild);
    
    // 自动隐藏成功消息
    if (type === 'success') {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
    
    // 滚动到顶部显示消息
    alertDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 添加错误样式
const style = document.createElement('style');
style.textContent = `
    .form-control.error {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1) !important;
    }
    
    .error-message {
        animation: fadeIn 0.3s ease-out;
    }
`;
document.head.appendChild(style);