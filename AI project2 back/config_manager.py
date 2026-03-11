import os
import json
from typing import Any, Optional
from threading import Lock

class ConfigManager:
    """配置管理器 - 支持JSON文件存储和点分割路径访问"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = os.path.abspath(config_file)
        self._config = {}
        self._lock = Lock()
        self.load_config()
    
    def load_config(self):
        """从JSON文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._config = {}
                self.save_config()  # 创建默认配置文件
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self._config = {}
    
    def save_config(self):
        """保存配置到JSON文件"""
        try:
            # 创建备份
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                with open(self.config_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            # 保存新配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            path: 配置路径，使用点分割，如 'openai.api_key'
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        with self._lock:
            try:
                keys = path.split('.')
                value = self._config
                
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return default
                
                return value
            except Exception:
                return default
    
    def set(self, path: str, value: Any, save: bool = True) -> bool:
        """设置配置值
        
        Args:
            path: 配置路径，使用点分割，如 'openai.api_key'
            value: 要设置的值
            save: 是否立即保存到文件
            
        Returns:
            是否设置成功
        """
        with self._lock:
            try:
                keys = path.split('.')
                config = self._config
                
                # 创建嵌套字典结构
                for key in keys[:-1]:
                    if key not in config:
                        config[key] = {}
                    elif not isinstance(config[key], dict):
                        config[key] = {}
                    config = config[key]
                
                # 设置最终值
                config[keys[-1]] = value
                
                if save:
                    self.save_config()
                
                return True
            except Exception as e:
                print(f"设置配置失败: {e}")
                return False
    
    def delete(self, path: str, save: bool = True) -> bool:
        """删除配置项
        
        Args:
            path: 配置路径
            save: 是否立即保存到文件
            
        Returns:
            是否删除成功
        """
        with self._lock:
            try:
                keys = path.split('.')
                config = self._config
                
                # 导航到父级
                for key in keys[:-1]:
                    if isinstance(config, dict) and key in config:
                        config = config[key]
                    else:
                        return False  # 路径不存在
                
                # 删除最终键
                if isinstance(config, dict) and keys[-1] in config:
                    del config[keys[-1]]
                    
                    if save:
                        self.save_config()
                    
                    return True
                
                return False
            except Exception as e:
                print(f"删除配置失败: {e}")
                return False
    
    def exists(self, path: str) -> bool:
        """检查配置路径是否存在"""
        with self._lock:
            try:
                keys = path.split('.')
                value = self._config
                
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return False
                
                return True
            except Exception:
                return False
    
    def get_section(self, path: str) -> dict:
        """获取配置段
        
        Args:
            path: 配置段路径，如 'openai'
            
        Returns:
            配置段字典
        """
        value = self.get(path, {})
        return value if isinstance(value, dict) else {}
    
    def update_section(self, path: str, values: dict, save: bool = True) -> bool:
        """批量更新配置段
        
        Args:
            path: 配置段路径
            values: 要更新的键值对
            save: 是否立即保存
            
        Returns:
            是否更新成功
        """
        try:
            for key, value in values.items():
                full_path = f"{path}.{key}" if path else key
                if not self.set(full_path, value, save=False):
                    return False
            
            if save:
                self.save_config()
            
            return True
        except Exception as e:
            print(f"批量更新配置失败: {e}")
            return False
    
    def get_all(self) -> dict:
        """获取所有配置"""
        with self._lock:
            return self._config.copy()
    
    def reload(self):
        """重新加载配置文件"""
        self.load_config()

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config(path: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(path, default)

def set_config(path: str, value: Any, save: bool = True) -> bool:
    """设置配置值的便捷函数"""
    return config_manager.set(path, value, save)

def config_exists(path: str) -> bool:
    """检查配置是否存在的便捷函数"""
    return config_manager.exists(path)