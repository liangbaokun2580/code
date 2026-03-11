/**
 * API客户端工具
 * 用于处理前端与后端的通信
 */

class ApiClient {
    /**
     * 发送GET请求
     * @param {string} url - 请求URL
     * @param {Object} params - 查询参数
     * @returns {Promise} - 返回Promise对象
     */
    static async get(url, params = {}) {
        try {
            // 构建查询字符串
            const queryString = Object.keys(params).length > 0
                ? '?' + new URLSearchParams(params).toString()
                : '';
            
            // 发送请求
            const response = await fetch(url + queryString, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 解析响应数据
            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }
    
    /**
     * 发送POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @returns {Promise} - 返回Promise对象
     */
    static async post(url, data = {}) {
        try {
            // 发送请求
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(data)
            });
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 解析响应数据
            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }
    
    /**
     * 发送PUT请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @returns {Promise} - 返回Promise对象
     */
    static async put(url, data = {}) {
        try {
            // 发送请求
            const response = await fetch(url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(data)
            });
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 解析响应数据
            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }
    
    /**
     * 发送DELETE请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @returns {Promise} - 返回Promise对象
     */
    static async delete(url, data = {}) {
        try {
            // 发送请求
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: Object.keys(data).length > 0 ? JSON.stringify(data) : undefined
            });
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 解析响应数据
            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }
    
    /**
     * 上传文件
     * @param {string} url - 请求URL
     * @param {FormData} formData - 表单数据
     * @returns {Promise} - 返回Promise对象
     */
    static async upload(url, formData) {
        try {
            // 发送请求
            const response = await fetch(url, {
                method: 'POST',
                credentials: 'same-origin',
                body: formData
            });
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 解析响应数据
            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }
}