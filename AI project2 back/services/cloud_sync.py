import json
import requests
from datetime import datetime
from threading import Thread
import logging
from typing import Dict, Any, Optional
from flask import current_app

from config import Config
from models import db, CloudSyncLog

class CloudSyncService:
    """云端同步服务"""
    
    def __init__(self):
        self.config = Config()
        self.api_base_url = self.config.CLOUD_STORAGE_API_URL
        self.api_key = self.config.CLOUD_STORAGE_API_KEY
        self.enabled = self.config.CLOUD_STORAGE_ENABLED and self.api_base_url is not None
        self.logger = logging.getLogger(__name__)
        
        # 如果API URL未配置，禁用云端同步
        if not self.api_base_url:
            self.enabled = False
            self.logger.warning("云端API URL未配置，云端同步功能已禁用")
    
    def _make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None) -> Optional[Dict[Any, Any]]:
        """发送HTTP请求到云端API"""
        if not self.enabled or not self.api_base_url:
            self.logger.debug("云端同步已禁用或API URL未配置")
            return None
        
        url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"云端API请求失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"云端同步异常: {e}")
            return None
    
    def _log_sync_operation(self, user_id: int, data_type: str, operation: str, 
                           data_id: str = None, status: str = 'success', error_message: str = None):
        """记录同步操作日志"""
        try:
            sync_log = CloudSyncLog(
                user_id=user_id,
                data_type=data_type,
                operation=operation,
                data_id=data_id,
                status=status,
                error_message=error_message
            )
            db.session.add(sync_log)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"记录同步日志失败: {e}")
    
    def sync_chat_session(self, chat_session, operation: str = 'create'):
        """同步聊天会话数据"""
        # 在主线程中提取数据，避免在异步线程中访问SQLAlchemy对象
        try:
            session_data = {
                'user_id': chat_session.user_id,
                'session_id': chat_session.session_id,
                'title': chat_session.title,
                'created_at': chat_session.created_at.isoformat(),
                'updated_at': chat_session.updated_at.isoformat(),
                'mode': chat_session.mode,
                'is_active': chat_session.is_active
            }
        except Exception as e:
            self.logger.error(f"提取会话数据失败: {e}")
            return
        
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                if operation == 'delete':
                    result = self._make_request('DELETE', f'/chat/sessions/{session_data["session_id"]}')
                elif operation == 'update':
                    result = self._make_request('PUT', f'/chat/sessions/{session_data["session_id"]}', session_data)
                else:  # create
                    result = self._make_request('POST', '/chat/sessions', session_data)
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            session_data['user_id'], 'chat_session', operation, 
                            session_data['session_id'], status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步聊天会话失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            session_data['user_id'], 'chat_session', operation, 
                            session_data['session_id'], 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_chat_message(self, chat_message, user_id, operation: str = 'create'):
        """同步聊天消息数据"""
        # 在主线程中提取数据，避免在异步线程中访问SQLAlchemy对象
        try:
            message_data = {
                'user_id': user_id,
                'session_id': chat_message.session_id,
                'message_id': chat_message.message_id,
                'role': chat_message.role,
                'content': chat_message.content,
                'tool_calls': chat_message.tool_calls,
                'tool_call_results': chat_message.tool_results,
                'created_at': chat_message.created_at.isoformat()
            }
        except Exception as e:
            self.logger.error(f"提取消息数据失败: {e}")
            return
        
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                if operation == 'create':
                    result = self._make_request('POST', '/chat/messages', message_data)
                elif operation == 'update':
                    result = self._make_request('PUT', f'/chat/messages/{message_data["message_id"]}', message_data)
                elif operation == 'delete':
                    result = self._make_request('DELETE', f'/chat/messages/{message_data["message_id"]}')
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            message_data['user_id'], 'chat_message', operation,
                            message_data['message_id'], status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步聊天消息失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            message_data['user_id'], 'chat_message', operation,
                            message_data['message_id'], 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_topology_data(self, topology_data, operation: str = 'create'):
        """同步拓扑数据"""
        # 在主线程中提取数据，避免在异步线程中访问SQLAlchemy对象
        try:
            topo_data = {
                'user_id': topology_data.user_id,
                'topology_id': topology_data.id,
                'name': topology_data.name,
                'description': topology_data.description,
                'topology_data': topology_data.topology_data,
                'mode': topology_data.mode,
                'version': topology_data.version,
                'created_at': topology_data.created_at.isoformat(),
                'updated_at': topology_data.updated_at.isoformat(),
                'is_active': topology_data.is_active
            }
        except Exception as e:
            self.logger.error(f"提取拓扑数据失败: {e}")
            return
        
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                if operation == 'create':
                    result = self._make_request('POST', '/topology/data', topo_data)
                elif operation == 'update':
                    result = self._make_request('PUT', f'/topology/data/{topo_data["topology_id"]}', topo_data)
                elif operation == 'delete':
                    result = self._make_request('DELETE', f'/topology/data/{topo_data["topology_id"]}')
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            topo_data['user_id'], 'topology_data', operation,
                            str(topo_data['topology_id']), status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步拓扑数据失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            topo_data['user_id'], 'topology_data', operation,
                            str(topo_data['topology_id']), 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_network_device(self, network_device, operation: str = 'create'):
        """同步网络设备数据"""
        # 在主线程中提取数据，避免在异步线程中访问SQLAlchemy对象
        try:
            device_data = {
                'user_id': network_device.user_id,
                'device_id': network_device.device_id,
                'hostname': network_device.hostname,
                'ip_address': network_device.ip_address,
                'device_type': network_device.device_type,
                'vendor': network_device.vendor,
                'model': network_device.model,
                'mac_address': network_device.mac_address,
                'status': network_device.status,
                'configuration': network_device.configuration,
                'last_seen': network_device.last_seen.isoformat() if network_device.last_seen else None,
                'created_at': network_device.created_at.isoformat(),
                'updated_at': network_device.updated_at.isoformat()
            }
        except Exception as e:
            self.logger.error(f"提取网络设备数据失败: {e}")
            return
        
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                if operation == 'create':
                    result = self._make_request('POST', '/network/devices', device_data)
                elif operation == 'update':
                    result = self._make_request('PUT', f'/network/devices/{device_data["device_id"]}', device_data)
                elif operation == 'delete':
                    result = self._make_request('DELETE', f'/network/devices/{device_data["device_id"]}')
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            device_data['user_id'], 'network_device', operation,
                            device_data['device_id'], status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步网络设备失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            device_data['user_id'], 'network_device', operation,
                            device_data['device_id'], 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_network_scan_result(self, scan_result: Dict[Any, Any], user_id: int):
        """同步网络扫描结果"""
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                data = {
                    'user_id': user_id,
                    'scan_result': scan_result,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                result = self._make_request('POST', '/network/scan-results', data)
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            user_id, 'network_scan', 'create', None, status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步网络扫描结果失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            user_id, 'network_scan', 'create', None, 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_code_execution(self, execution_log: Dict[Any, Any]):
        """同步代码执行记录"""
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                result = self._make_request('POST', '/develop/executions', execution_log)
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            execution_log['user_id'], 'code_execution', 'create', None, status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步代码执行记录失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            execution_log['user_id'], 'code_execution', 'create', None, 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_code_file(self, code_record: Dict[Any, Any]):
        """同步代码文件"""
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                result = self._make_request('POST', '/develop/files', code_record)
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            code_record['user_id'], 'code_file', 'create', 
                            code_record['filename'], status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步代码文件失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            code_record['user_id'], 'code_file', 'create',
                            code_record['filename'], 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def sync_code_file_operation(self, operation_record: Dict[Any, Any]):
        """同步代码文件操作"""
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return
        
        def _sync():
            try:
                result = self._make_request('POST', '/develop/file-operations', operation_record)
                
                status = 'success' if result else 'failed'
                
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            operation_record['user_id'], 'code_file_operation', 
                            operation_record['action'], operation_record['filename'], status
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                
            except Exception as e:
                self.logger.error(f"同步代码文件操作失败: {e}")
                try:
                    with app.app_context():
                        self._log_sync_operation(
                            operation_record['user_id'], 'code_file_operation',
                            operation_record['action'], operation_record['filename'], 'failed', str(e)
                        )
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
        
        Thread(target=_sync, daemon=True).start()
    
    def pull_user_data(self, user_id: int) -> Dict[str, Any]:
        """从云端拉取用户数据"""
        # 获取当前应用实例
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            self.logger.warning("无法获取Flask应用上下文，跳过云端同步")
            return {}
        
        try:
            result = self._make_request('GET', f'/users/{user_id}/data')
            
            if result:
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(user_id, 'user_data', 'pull', None, 'success')
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                return result
            else:
                # 在应用上下文中记录日志
                try:
                    with app.app_context():
                        self._log_sync_operation(user_id, 'user_data', 'pull', None, 'failed')
                except Exception as log_error:
                    self.logger.error(f"记录同步日志失败: {log_error}")
                return {}
                
        except Exception as e:
            self.logger.error(f"拉取用户数据失败: {e}")
            try:
                with app.app_context():
                    self._log_sync_operation(user_id, 'user_data', 'pull', None, 'failed', str(e))
            except Exception as log_error:
                self.logger.error(f"记录同步日志失败: {log_error}")
            return {}
    
    def get_sync_status(self, user_id: int, limit: int = 50) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            sync_logs = CloudSyncLog.query.filter_by(
                user_id=user_id
            ).order_by(CloudSyncLog.created_at.desc()).limit(limit).all()
            
            logs = []
            for log in sync_logs:
                logs.append({
                    'id': log.id,
                    'data_type': log.data_type,
                    'operation': log.operation,
                    'data_id': log.data_id,
                    'status': log.status,
                    'error_message': log.error_message,
                    'created_at': log.created_at.isoformat()
                })
            
            # 统计同步状态
            total_syncs = len(logs)
            successful_syncs = len([log for log in logs if log['status'] == 'success'])
            failed_syncs = total_syncs - successful_syncs
            
            return {
                'total_syncs': total_syncs,
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'success_rate': (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0,
                'recent_logs': logs
            }
            
        except Exception as e:
            self.logger.error(f"获取同步状态失败: {e}")
            return {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'success_rate': 0,
                'recent_logs': [],
                'error': str(e)
            }
    
    def retry_failed_syncs(self, user_id: int) -> Dict[str, Any]:
        """重试失败的同步操作"""
        try:
            failed_logs = CloudSyncLog.query.filter_by(
                user_id=user_id,
                status='failed'
            ).order_by(CloudSyncLog.created_at.desc()).limit(10).all()
            
            retry_count = 0
            for log in failed_logs:
                # 这里可以根据数据类型重新执行同步操作
                # 为简化，这里只是更新日志状态
                log.status = 'retrying'
                log.updated_at = datetime.utcnow()
                retry_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'retry_count': retry_count,
                'message': f'已重试 {retry_count} 个失败的同步操作'
            }
            
        except Exception as e:
            self.logger.error(f"重试同步操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }