import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class TopologyService:
    """拓扑服务类，处理网络拓扑数据"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_topology_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取拓扑数据"""
        try:
            # 从数据库获取拓扑数据
            from models import TopologyData
            
            if user_id:
                topology = TopologyData.query.filter_by(user_id=user_id).first()
            else:
                topology = TopologyData.query.first()
            
            if topology and topology.topology_data:
                try:
                    if isinstance(topology.topology_data, str):
                        data = json.loads(topology.topology_data)
                    else:
                        data = topology.topology_data
                    
                    return data
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.error(f"解析拓扑数据失败: {e}")
                    return self._get_default_topology_data()
            else:
                return self._get_default_topology_data()
                
        except Exception as e:
            self.logger.error(f"获取拓扑数据失败: {e}")
            return self._get_default_topology_data()
    
    def _get_default_topology_data(self) -> Dict[str, Any]:
        """获取默认的拓扑数据结构"""
        return {
            'devices': [],
            'connections': [],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0',
                'description': '默认拓扑数据'
            }
        }
    
    def save_topology_data(self, data: Dict[str, Any], user_id: str, name: str = '默认拓扑', description: str = '') -> bool:
        """保存拓扑数据"""
        try:
            from models import TopologyData, db
            
            # 查找现有拓扑数据
            topology = TopologyData.query.filter_by(user_id=user_id).first()
            
            if topology:
                # 更新现有数据
                topology.topology_data = json.dumps(data)
                topology.name = name
                topology.description = description
                topology.updated_at = datetime.now()
            else:
                # 创建新数据
                topology = TopologyData(
                    user_id=user_id,
                    name=name,
                    description=description,
                    topology_data=json.dumps(data),
                    mode='view'
                )
                db.session.add(topology)
            
            db.session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"保存拓扑数据失败: {e}")
            return False
    
    def get_devices(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取设备列表"""
        topology_data = self.get_topology_data(user_id)
        return topology_data.get('devices', [])
    
    def get_connections(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取连接列表"""
        topology_data = self.get_topology_data(user_id)
        return topology_data.get('connections', [])
    
    def get_topology_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取拓扑统计信息"""
        try:
            topology_data = self.get_topology_data(user_id)
            devices = topology_data.get('devices', [])
            connections = topology_data.get('connections', [])
            
            # 统计设备状态
            total_devices = len(devices)
            online_devices = sum(1 for d in devices if d.get('status') == 'online')
            offline_devices = total_devices - online_devices
            
            # 统计连接状态
            total_connections = len(connections)
            active_connections = sum(1 for c in connections if c.get('status') == 'active')
            
            # 统计设备类型
            device_types = {}
            for device in devices:
                device_type = device.get('type', device.get('device_type', 'unknown'))
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            # 统计连接类型
            connection_types = {}
            for conn in connections:
                conn_type = conn.get('type', 'unknown')
                connection_types[conn_type] = connection_types.get(conn_type, 0) + 1
            
            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'total_connections': total_connections,
                'active_connections': active_connections,
                'device_types': device_types,
                'connection_types': connection_types,
                'health_score': (online_devices / total_devices * 100) if total_devices > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"获取拓扑统计失败: {e}")
            return {
                'total_devices': 0,
                'online_devices': 0,
                'offline_devices': 0,
                'total_connections': 0,
                'active_connections': 0,
                'device_types': {},
                'connection_types': {},
                'health_score': 0
            }