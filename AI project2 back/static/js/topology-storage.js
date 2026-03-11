/**
 * 网络拓扑数据本地存储管理模块
 * 用于在不同页面间共享拓扑数据
 */

class TopologyStorage {
    constructor() {
        this.storageKey = 'network_topology_view';
        this.cacheTimeout = 5 * 60 * 1000; // 5分钟缓存超时
        this.cloudSyncEnabled = true; // 启用云端同步
        this.autoSaveInterval = 30000; // 30秒自动保存间隔
        this.autoSaveTimer = null;
        this.lastSyncTime = null;
        this.manualSaveOnly = true; // 只在手动操作时保存到云端
        this.syncRetryCount = 0;
        this.maxRetryCount = 3;
        this.retryDelay = 5000; // 5秒重试延迟
        
        // 页面加载时尝试从云端加载数据
        this.loadFromCloud();
        
        // 监听网络状态变化
        this.setupNetworkMonitoring();
    }

    /**
     * 保存拓扑数据到本地存储和云端
     * @param {Object} topologyData - 拓扑数据
     * @param {string} mode - 当前模式
     * @param {boolean} syncToCloud - 是否同步到云端
     * @param {boolean} isManualSave - 是否为手动保存操作
     */
    saveTopologyData(topologyData, mode = 'view', syncToCloud = true, isManualSave = false) {
        const topologyView = {
            timestamp: new Date().toISOString(),
            mode: mode,
            data: topologyData,
            stats: this.calculateStats(topologyData),
            version: '1.0'
        };
        
        try {
            // 保存到本地存储
            localStorage.setItem(this.storageKey, JSON.stringify(topologyView));
            console.log('拓扑数据已保存到本地存储');
            
            // 只在手动操作时同步到云端
            if (syncToCloud && this.cloudSyncEnabled && (isManualSave || !this.manualSaveOnly)) {
                this.saveToCloud(topologyView);
            }
            
            this._triggerTopologyDataUpdated();
            
            return true;
        } catch (error) {
            console.error('保存拓扑数据失败:', error);
            return false;
        }
    }

    /**
     * 从本地存储读取拓扑数据
     * @param {boolean} checkTimeout - 是否检查缓存超时
     * @returns {Object|null} 拓扑数据或null
     */
    loadTopologyData(checkTimeout = true) {
        try {
            const savedData = localStorage.getItem(this.storageKey);
            if (!savedData) {
                return null;
            }

            const topologyView = JSON.parse(savedData);
            
            // 检查数据是否过期
            if (checkTimeout && this.isDataExpired(topologyView.timestamp)) {
                console.log('本地拓扑数据已过期');
                return null;
            }

            return topologyView;
        } catch (error) {
            console.error('读取本地拓扑数据失败:', error);
            return null;
        }
    }

    /**
     * 获取设备列表
     * @param {number} limit - 限制返回的设备数量
     * @returns {Array} 设备列表
     */
    getDevices(limit = null) {
        const topologyData = this.loadTopologyData();
        if (!topologyData || !topologyData.data || !topologyData.data.devices) {
            return [];
        }

        const devices = topologyData.data.devices;
        return limit ? devices.slice(0, limit) : devices;
    }

    /**
     * 获取网络统计信息
     * @returns {Object} 统计信息
     */
    getNetworkStats() {
        const topologyData = this.loadTopologyData();
        if (!topologyData || !topologyData.stats) {
            return {
                total_devices: 0,
                online_devices: 0,
                offline_devices: 0,
                unknown_devices: 0
            };
        }

        return topologyData.stats;
    }

    /**
     * 根据IP地址查找设备
     * @param {string} ip - IP地址
     * @returns {Object|null} 设备信息或null
     */
    findDeviceByIP(ip) {
        const devices = this.getDevices();
        return devices.find(device => device.ip === ip) || null;
    }

    /**
     * 根据设备类型过滤设备
     * @param {string} deviceType - 设备类型
     * @returns {Array} 过滤后的设备列表
     */
    getDevicesByType(deviceType) {
        const devices = this.getDevices();
        return devices.filter(device => device.device_type === deviceType);
    }

    /**
     * 获取在线设备列表
     * @returns {Array} 在线设备列表
     */
    getOnlineDevices() {
        const devices = this.getDevices();
        return devices.filter(device => device.status === 'online');
    }

    /**
     * 获取离线设备列表
     * @returns {Array} 离线设备列表
     */
    getOfflineDevices() {
        const devices = this.getDevices();
        return devices.filter(device => device.status === 'offline');
    }

    /**
     * 清除本地存储的拓扑数据
     */
    clearTopologyData() {
        try {
            localStorage.removeItem(this.storageKey);
            console.log('本地拓扑数据已清除');
            
            // 触发数据清除事件
            window.dispatchEvent(new CustomEvent('topologyDataCleared'));
            
            return true;
        } catch (error) {
            console.error('清除拓扑数据失败:', error);
            return false;
        }
    }

    /**
     * 检查数据是否过期
     * @param {string} timestamp - 时间戳
     * @returns {boolean} 是否过期
     */
    isDataExpired(timestamp) {
        const now = new Date().getTime();
        const dataTime = new Date(timestamp).getTime();
        return (now - dataTime) > this.cacheTimeout;
    }

    /**
     * 计算拓扑统计信息
     * @param {Object} topologyData - 拓扑数据
     * @returns {Object} 统计信息
     */
    calculateStats(topologyData) {
        if (!topologyData || !topologyData.devices) {
            return {
                total_devices: 0,
                online_devices: 0,
                offline_devices: 0,
                unknown_devices: 0
            };
        }

        const devices = topologyData.devices;
        const stats = {
            total_devices: devices.length,
            online_devices: devices.filter(d => d.status === 'online').length,
            offline_devices: devices.filter(d => d.status === 'offline').length,
            unknown_devices: devices.filter(d => !d.status || d.status === 'unknown').length
        };

        return stats;
    }

    /**
     * 监听拓扑数据更新事件
     * @param {Function} callback - 回调函数
     */
    onTopologyDataUpdated(callback) {
        window.addEventListener('topologyDataUpdated', callback);
    }

    /**
     * 监听拓扑数据清除事件
     * @param {Function} callback - 回调函数
     */
    onTopologyDataCleared(callback) {
        window.addEventListener('topologyDataCleared', callback);
    }

    /**
     * 获取设备图标类名
     * @param {string} deviceType - 设备类型
     * @returns {string} 图标类名
     */
    getDeviceIcon(deviceType) {
        const iconMap = {
            'router': 'fas fa-server',
            'switch': 'fas fa-network-wired',
            'firewall': 'fas fa-shield-alt',
            'access_point': 'fas fa-wifi',
            'printer': 'fas fa-print',
            'computer': 'fas fa-desktop',
            'server': 'fas fa-server',
            'phone': 'fas fa-phone',
            'camera': 'fas fa-video',
            'unknown': 'fas fa-question-circle'
        };
        return iconMap[deviceType] || iconMap['unknown'];
    }

    /**
     * 根据状态查找设备
     * @param {string} status - 设备状态
     * @returns {Array} 设备列表
     */
    findDevicesByStatus(status) {
        const devices = this.getDevices();
        return devices.filter(device => device.status === status);
    }

    /**
     * 格式化设备状态
     * @param {string} status - 设备状态
     * @returns {Object} 格式化后的状态信息
     */
    formatDeviceStatus(status) {
        const statusMap = {
            'online': { class: 'success', text: '在线' },
            'offline': { class: 'danger', text: '离线' },
            'warning': { class: 'warning', text: '警告' },
            'error': { class: 'danger', text: '错误' },
            'unknown': { class: 'secondary', text: '未知' }
        };
        return statusMap[status] || statusMap['unknown'];
    }

    /**
     * 监听拓扑数据更新事件
     * @param {Function} callback - 回调函数
     */
    onTopologyDataUpdated(callback) {
        if (typeof callback === 'function') {
            window.addEventListener('topologyDataUpdated', callback);
        }
    }

    /**
     * 触发拓扑数据更新事件
     */
    _triggerTopologyDataUpdated() {
        const event = new CustomEvent('topologyDataUpdated', {
            detail: { timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }

    /**
     * 保存数据到云端
     * @param {Object} topologyView - 拓扑视图数据
     * @param {number} retryCount - 重试次数
     */
    async saveToCloud(topologyView, retryCount = 0) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
            
            const response = await fetch('/api/topology/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(topologyView),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            const result = await response.json();
            
            if (result.success) {
                this.lastSyncTime = new Date().toISOString();
                this.syncRetryCount = 0; // 重置重试计数
                console.log('拓扑数据已同步到云端');
            
                // 触发云端同步成功事件
                window.dispatchEvent(new CustomEvent('topologyCloudSyncSuccess', {
                    detail: { timestamp: this.lastSyncTime }
                }));
            } else {
                throw new Error(result.error || '云端同步失败');
            }
        } catch (error) {
            console.error('云端同步请求失败:', error);
            
            // 如果还有重试次数，则进行重试
            if (retryCount < this.maxRetryCount && this.cloudSyncEnabled) {
                console.log(`云端同步失败，${this.retryDelay/1000}秒后进行第${retryCount + 1}次重试`);
                setTimeout(() => {
                    this.saveToCloud(topologyView, retryCount + 1);
                }, this.retryDelay);
                return;
            }
            
            // 重试次数用完，触发同步失败事件
            window.dispatchEvent(new CustomEvent('topologyCloudSyncError', {
                detail: { 
                    error: error.message,
                    retryCount: retryCount,
                    maxRetryReached: retryCount >= this.maxRetryCount
                }
            }));
            
            // 确保数据保存到本地存储作为备份
            this.saveToLocalBackup(topologyView);
        }
    }

    /**
     * 从云端加载数据
     */
    async loadFromCloud() {
        if (!this.cloudSyncEnabled) {
            return;
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000); // 8秒超时
            
            const response = await fetch('/api/topology/load', {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            const result = await response.json();
            
            if (result.success && result.data) {
                // 验证云端数据的完整性
                if (!this.validateCloudData(result.data)) {
                    console.warn('云端数据格式不正确，跳过加载');
                    return;
                }
                
                // 检查云端数据是否比本地数据更新
                const localData = this.loadTopologyData(false);
                const cloudTimestamp = new Date(result.data.timestamp).getTime();
                const localTimestamp = localData ? new Date(localData.timestamp).getTime() : 0;
                
                if (cloudTimestamp > localTimestamp) {
                    // 云端数据更新，使用云端数据
                    localStorage.setItem(this.storageKey, JSON.stringify(result.data));
                    console.log('已从云端加载最新拓扑数据');
                    
                    // 触发数据加载事件
                    window.dispatchEvent(new CustomEvent('topologyCloudDataLoaded', {
                        detail: { data: result.data }
                    }));
                    
                    this._triggerTopologyDataUpdated();
                } else {
                    console.log('本地数据已是最新，无需从云端更新');
                }
                
                this.lastSyncTime = new Date().toISOString();
            } else if (response.status !== 404) {
                console.error('从云端加载数据失败:', result.error);
            }
        } catch (error) {
            console.error('云端加载请求失败:', error);
            // 加载失败时，尝试从本地备份恢复
            this.loadFromLocalBackup();
        }
    }

    /**
     * 手动保存拓扑数据（用于用户主动操作）
     * @param {Object} topologyData - 拓扑数据
     * @param {string} mode - 当前模式
     */
    saveTopologyDataManually(topologyData, mode = 'view') {
        return this.saveTopologyData(topologyData, mode, true, true);
    }

    /**
     * 停止自动保存
     */
    stopAutoSave() {
        if (this.autoSaveTimer) {
            clearInterval(this.autoSaveTimer);
            this.autoSaveTimer = null;
            console.log('拓扑数据自动保存已停止');
        }
    }

    /**
     * 手动同步到云端
     */
    async manualSyncToCloud() {
        const localData = this.loadTopologyData(false);
        if (localData) {
            await this.saveToCloud(localData);
            return true;
        }
        return false;
    }

    /**
     * 获取同步状态
     */
    getSyncStatus() {
        return {
            cloudSyncEnabled: this.cloudSyncEnabled,
            lastSyncTime: this.lastSyncTime,
            autoSaveInterval: this.autoSaveInterval,
            isAutoSaveRunning: this.autoSaveTimer !== null
        };
    }

    /**
     * 设置云端同步状态
     * @param {boolean} enabled - 是否启用云端同步
     */
    setCloudSyncEnabled(enabled) {
        this.cloudSyncEnabled = enabled;
        
        if (enabled) {
            this.loadFromCloud();
        }
        
        console.log(`云端同步已${enabled ? '启用' : '禁用'}`);
    }
    
    /**
     * 验证云端数据的完整性
     * @param {Object} data - 云端数据
     * @returns {boolean} 数据是否有效
     */
    validateCloudData(data) {
        if (!data || typeof data !== 'object') {
            return false;
        }
        
        if (!data.data || typeof data.data !== 'object') {
            return false;
        }
        
        if (!Array.isArray(data.data.devices) || !Array.isArray(data.data.connections)) {
            return false;
        }
        
        return true;
    }
    
    /**
     * 保存到本地备份
     * @param {Object} data - 要备份的数据
     */
    saveToLocalBackup(data) {
        try {
            const backupKey = this.storageKey + '_backup';
            localStorage.setItem(backupKey, JSON.stringify({
                ...data,
                backupTimestamp: new Date().toISOString()
            }));
            console.log('数据已保存到本地备份');
        } catch (error) {
            console.error('保存本地备份失败:', error);
        }
    }
    
    /**
     * 从本地备份加载数据
     */
    loadFromLocalBackup() {
        try {
            const backupKey = this.storageKey + '_backup';
            const backupData = localStorage.getItem(backupKey);
            if (backupData) {
                const parsedData = JSON.parse(backupData);
                console.log('从本地备份恢复数据');
                
                // 触发数据加载事件
                window.dispatchEvent(new CustomEvent('topologyCloudDataLoaded', {
                    detail: { data: parsedData, fromBackup: true }
                }));
                
                return parsedData;
            }
        } catch (error) {
            console.error('从本地备份加载数据失败:', error);
        }
        return null;
    }
    
    /**
     * 设置网络状态监控
     */
    setupNetworkMonitoring() {
        // 监听网络状态变化
        window.addEventListener('online', () => {
            console.log('网络已连接，尝试同步数据');
            if (this.cloudSyncEnabled) {
                this.loadFromCloud();
            }
        });
        
        window.addEventListener('offline', () => {
            console.log('网络已断开，启用离线模式');
        });
    }
}

// 创建全局实例
window.topologyStorage = new TopologyStorage();

// 导出类（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TopologyStorage;
}