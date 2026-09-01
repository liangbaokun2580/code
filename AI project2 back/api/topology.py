from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import json
import uuid
import ipaddress

from models import db, TopologyData, NetworkDevice
from services.cloud_sync import CloudSyncService
from services.network_service import NetworkService
from utils.database_utils import safe_create_or_update
import socket
import platform
import psutil
import netifaces

topology_bp = Blueprint('topology', __name__)
cloud_sync = CloudSyncService()
network_service = NetworkService()

LOCAL_GATEWAY_SESSION_KEY = 'topology_gateway_override'

@topology_bp.route('/ping', methods=['POST'])
@login_required
def ping_device():
    """Ping设备测试连通性"""
    try:
        data = request.get_json()
        if not data or 'ip' not in data:
            return jsonify({'success': False, 'error': '缺少IP地址参数'}), 400
        
        ip = data['ip']
        timeout = data.get('timeout', 3)
        
        # 验证IP地址格式
        import ipaddress
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return jsonify({'success': False, 'error': '无效的IP地址格式'}), 400
        
        # 执行ping测试并获取延迟信息
        ping_result = network_service.ping_host_with_latency(ip, timeout)
        
        # 如果ping通了，更新数据库中设备的在线状态
        if ping_result['reachable']:
            device = NetworkDevice.query.filter_by(
                user_id=current_user.id,
                ip_address=ip
            ).first()
            
            if device:
                device.status = 'online'
                device.last_seen = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception as db_error:
                    db.session.rollback()
                    # 记录数据库错误但不影响ping结果返回
                    print(f"更新设备状态失败: {db_error}")
        
        return jsonify({
            'success': True,
            'reachable': ping_result['reachable'],
            'latency': ping_result['latency'],
            'response_time': ping_result['latency'],  # 兼容前端现有代码
            'ip': ip,
            'timeout': timeout,
            'output': ping_result.get('output', '')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/data', methods=['GET'])
@login_required
def get_topology_data():
    """获取用户的拓扑数据"""
    try:
        # 获取最新的拓扑数据
        topology = TopologyData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(TopologyData.updated_at.desc()).first()
        
        if not topology:
            # 如果没有拓扑数据，返回空的默认结构
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'mode': 'view',
                    'data': {
                        'devices': [],
                        'connections': []
                    },
                    'stats': {'deviceCount': 0, 'connectionCount': 0},
                    'version': '1.0'
                }
            })
        
        # 获取拓扑数据并转换为前端期望的格式
        topology_data = topology.to_dict()['topology_data']
        
        # 构建符合前端验证要求的数据结构
        formatted_data = {
            'timestamp': topology.updated_at.isoformat(),
            'mode': topology.mode or 'view',
            'data': {
                'devices': topology_data.get('devices', topology_data.get('nodes', [])),
                'connections': topology_data.get('connections', topology_data.get('edges', []))
            },
            'stats': {
                'deviceCount': len(topology_data.get('devices', topology_data.get('nodes', []))),
                'connectionCount': len(topology_data.get('connections', topology_data.get('edges', [])))
            },
            'version': topology.version or '1.0'
        }
        
        return jsonify({
            'success': True,
            'data': formatted_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/save', methods=['POST'])
@login_required
def save_topology_data():
    """保存拓扑数据"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '数据不能为空'}), 400
        
        # 验证数据格式
        if 'data' not in data:
            return jsonify({'success': False, 'error': '缺少拓扑数据'}), 400
        
        topology_data = data['data']
        mode = data.get('mode', 'view')
        name = data.get('name', '默认拓扑')
        description = data.get('description', '')
        
        # 查找现有的拓扑数据
        existing_topology = TopologyData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if existing_topology:
            # 更新现有数据
            existing_topology.topology_data = json.dumps(topology_data)
            existing_topology.mode = mode
            existing_topology.name = name
            existing_topology.description = description
            existing_topology.updated_at = datetime.utcnow()
            topology = existing_topology
        else:
            # 创建新的拓扑数据
            topology = TopologyData(
                user_id=current_user.id,
                name=name,
                description=description,
                topology_data=json.dumps(topology_data),
                mode=mode
            )
            db.session.add(topology)
        
        # 处理设备信息保存到NetworkDevice表
        devices_saved = 0
        devices_updated = 0
        
        if 'devices' in topology_data:
            for device_info in topology_data['devices']:
                # 跳过没有IP地址的设备
                device_ip = device_info.get('ip') or device_info.get('ip_address')
                if not device_ip:
                    continue
                
                # 查找现有设备
                device = NetworkDevice.query.filter_by(
                    user_id=current_user.id,
                    ip_address=device_ip
                ).first()
                
                if device:
                    # 更新现有设备信息
                    device.hostname = device_info.get('name') or device_info.get('hostname') or device.hostname
                    device.device_type = device_info.get('type') or device_info.get('device_type') or device.device_type
                    device.vendor = device_info.get('vendor') or device.vendor
                    device.model = device_info.get('model') or device.model
                    device.mac_address = device_info.get('mac_address') or device.mac_address
                    device.status = device_info.get('status', 'unknown')
                    
                    # 更新SSH凭据
                    if 'credentials' in device_info:
                        device.credentials = device_info.get('credentials')
                        
                    device.last_seen = datetime.utcnow()
                    device.updated_at = datetime.utcnow()
                    devices_updated += 1
                else:
                    # 创建新设备
                    device = NetworkDevice(
                        user_id=current_user.id,
                        device_id=device_info.get('id') or str(uuid.uuid4()),
                        hostname=device_info.get('name') or device_info.get('hostname') or '',
                        ip_address=device_ip,
                        device_type=device_info.get('type') or device_info.get('device_type') or 'unknown',
                        vendor=device_info.get('vendor') or '',
                        model=device_info.get('model') or '',
                        mac_address=device_info.get('mac_address') or '',
                        status=device_info.get('status', 'unknown'),
                        credentials=device_info.get('credentials'),
                        last_seen=datetime.utcnow()
                    )
                    db.session.add(device)
                    devices_saved += 1
        
        db.session.commit()
        
        # 异步同步到云端
        operation = 'update' if existing_topology else 'create'
        cloud_sync.sync_topology_data(topology, operation)
        
        return jsonify({
            'success': True,
            'message': f'拓扑数据保存成功，新增设备 {devices_saved} 个，更新设备 {devices_updated} 个',
            'data': {
                'topology': topology.to_dict(),
                'devices_saved': devices_saved,
                'devices_updated': devices_updated
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/load', methods=['GET'])
@login_required
def load_topology_data():
    """加载拓扑数据（与get_topology_data相同，为兼容性保留）"""
    return get_topology_data()

@topology_bp.route('/clear', methods=['POST'])
@login_required
def clear_topology_data():
    """清空当前用户的拓扑图数据"""
    try:
        empty_topology = {
            'devices': [],
            'connections': []
        }

        topology = TopologyData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()

        if topology:
            topology.topology_data = json.dumps(empty_topology)
            topology.mode = 'view'
            topology.updated_at = datetime.utcnow()
        else:
            topology = TopologyData(
                user_id=current_user.id,
                name='默认拓扑',
                description='',
                topology_data=json.dumps(empty_topology),
                mode='view'
            )
            db.session.add(topology)

        db.session.commit()
        cloud_sync.sync_topology_data(topology, 'update')

        return jsonify({
            'success': True,
            'message': '拓扑图已清空',
            'data': {
                'topology': topology.to_dict()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/versions', methods=['GET'])
@login_required
def get_topology_versions():
    """获取拓扑数据的历史版本"""
    try:
        topologies = TopologyData.query.filter_by(
            user_id=current_user.id
        ).order_by(TopologyData.updated_at.desc()).limit(10).all()
        
        versions = []
        for topology in topologies:
            versions.append({
                'id': topology.id,
                'name': topology.name,
                'description': topology.description,
                'version': topology.version,
                'created_at': topology.created_at.isoformat(),
                'updated_at': topology.updated_at.isoformat(),
                'is_active': topology.is_active
            })
        
        return jsonify({
            'success': True,
            'data': versions
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/versions/<int:version_id>', methods=['GET'])
@login_required
def get_topology_version(version_id):
    """获取指定版本的拓扑数据"""
    try:
        topology = TopologyData.query.filter_by(
            id=version_id,
            user_id=current_user.id
        ).first()
        
        if not topology:
            return jsonify({'success': False, 'error': '版本不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': topology.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/scan', methods=['POST'])
@login_required
def scan_network():
    """扫描网络设备"""
    try:
        data = request.get_json() or {}
        scan_range = data.get('scan_range', '192.168.1.0/24')
        scan_type = data.get('scan_type', 'ping')  # ping, snmp, full
        
        # 执行网络扫描
        scan_result = network_service.scan_network(
            scan_range=scan_range,
            scan_type=scan_type,
            user_id=current_user.id
        )

        if scan_result.get('error'):
            return jsonify({
                'success': False,
                'error': scan_result.get('error'),
                'data': {
                    'scan_result': scan_result,
                    'devices_saved': 0
                }
            }), 500
        
        # 保存扫描到的设备
        devices_saved = 0
        persistence_error = None
        try:
            for device_info in scan_result.get('devices', []):
                ip_address = device_info.get('ip_address') or device_info.get('ip')
                if not ip_address:
                    continue

                device = NetworkDevice.query.filter_by(
                    user_id=current_user.id,
                    ip_address=ip_address
                ).first()
                
                if device:
                    # 更新现有设备
                    device.hostname = device_info.get('hostname', device.hostname)
                    device.device_type = device_info.get('device_type', device.device_type)
                    device.vendor = device_info.get('vendor', device.vendor)
                    device.model = device_info.get('model', device.model)
                    device.mac_address = device_info.get('mac_address', device.mac_address)
                    device.status = device_info.get('status', 'unknown')
                    device.last_seen = datetime.utcnow()
                    device.updated_at = datetime.utcnow()
                else:
                    # 创建新设备
                    device = NetworkDevice(
                        user_id=current_user.id,
                        device_id=device_info.get('device_id', str(uuid.uuid4())),
                        hostname=device_info.get('hostname', ''),
                        ip_address=ip_address,
                        device_type=device_info.get('device_type', 'unknown'),
                        vendor=device_info.get('vendor', ''),
                        model=device_info.get('model', ''),
                        mac_address=device_info.get('mac_address', ''),
                        status=device_info.get('status', 'unknown'),
                        last_seen=datetime.utcnow()
                    )
                    db.session.add(device)
                
                devices_saved += 1
            
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            persistence_error = f'保存扫描结果失败: {str(db_error)}'

        # 异步同步到云端
        try:
            cloud_sync.sync_network_scan_result(scan_result, current_user.id)
        except Exception as sync_error:
            if persistence_error:
                persistence_error = f'{persistence_error}; 云同步失败: {str(sync_error)}'
            else:
                persistence_error = f'云同步失败: {str(sync_error)}'
        
        return jsonify({
            'success': True,
            'message': f'网络扫描完成，发现 {len(scan_result.get("devices", []))} 个设备',
            'data': {
                'scan_result': scan_result,
                'devices_saved': devices_saved
            },
            'warning': persistence_error
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/devices', methods=['GET'])
@login_required
def get_devices():
    """获取用户的网络设备列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status_filter = request.args.get('status')
        device_type_filter = request.args.get('device_type')
        
        query = NetworkDevice.query.filter_by(user_id=current_user.id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if device_type_filter:
            query = query.filter_by(device_type=device_type_filter)
        
        devices = query.order_by(NetworkDevice.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'devices': [device.to_dict() for device in devices.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': devices.total,
                    'pages': devices.pages
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/devices/<device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    """获取指定设备的详细信息"""
    try:
        device = NetworkDevice.query.filter_by(
            device_id=device_id,
            user_id=current_user.id
        ).first()
        
        if not device:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': device.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/devices/<device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    """更新设备信息"""
    try:
        device = NetworkDevice.query.filter_by(
            device_id=device_id,
            user_id=current_user.id
        ).first()
        
        if not device:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        
        data = request.get_json()
        
        # 更新允许的字段
        updatable_fields = ['hostname', 'device_type', 'vendor', 'model', 'configuration']
        for field in updatable_fields:
            if field in data:
                if field == 'configuration':
                    setattr(device, field, json.dumps(data[field]))
                else:
                    setattr(device, field, data[field])
        
        device.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 异步同步到云端
        cloud_sync.sync_network_device(device, 'update')
        
        return jsonify({
            'success': True,
            'message': '设备信息更新成功',
            'data': device.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/devices/<device_id>', methods=['DELETE'])
@login_required
def delete_device(device_id):
    """删除设备"""
    try:
        device = NetworkDevice.query.filter_by(
            device_id=device_id,
            user_id=current_user.id
        ).first()
        
        if not device:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        
        db.session.delete(device)
        db.session.commit()
        
        # 异步同步到云端
        cloud_sync.sync_network_device(device, 'delete')
        
        return jsonify({
            'success': True,
            'message': '设备删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/export', methods=['GET'])
@login_required
def export_topology():
    """导出拓扑数据"""
    try:
        # 获取拓扑数据
        topology = TopologyData.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(TopologyData.updated_at.desc()).first()
        
        # 获取设备数据
        devices = NetworkDevice.query.filter_by(
            user_id=current_user.id
        ).all()
        
        export_data = {
            'topology': topology.to_dict() if topology else None,
            'devices': [device.to_dict() for device in devices],
            'export_time': datetime.utcnow().isoformat(),
            'user_id': current_user.id
        }
        
        return jsonify({
            'success': True,
            'data': export_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/import', methods=['POST'])
@login_required
def import_topology():
    """导入拓扑数据"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '导入数据不能为空'}), 400
        
        imported_count = 0
        
        # 导入拓扑数据
        if 'topology' in data and data['topology']:
            topology_data = data['topology']
            
            # 创建新的拓扑数据
            topology = TopologyData(
                user_id=current_user.id,
                name=topology_data.get('name', '导入的拓扑'),
                description=topology_data.get('description', ''),
                topology_data=json.dumps(topology_data.get('topology_data', {})),
                mode=topology_data.get('mode', 'view')
            )
            db.session.add(topology)
            imported_count += 1
        
        # 导入设备数据
        if 'devices' in data:
            for device_data in data['devices']:
                # 检查设备是否已存在
                existing_device = NetworkDevice.query.filter_by(
                    user_id=current_user.id,
                    ip_address=device_data['ip_address']
                ).first()
                
                if not existing_device:
                    device = NetworkDevice(
                        user_id=current_user.id,
                        device_id=device_data.get('device_id', str(uuid.uuid4())),
                        hostname=device_data.get('hostname', ''),
                        ip_address=device_data['ip_address'],
                        device_type=device_data.get('device_type', 'unknown'),
                        vendor=device_data.get('vendor', ''),
                        model=device_data.get('model', ''),
                        mac_address=device_data.get('mac_address', ''),
                        status=device_data.get('status', 'unknown')
                    )
                    db.session.add(device)
                    imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功导入 {imported_count} 项数据'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@topology_bp.route('/local-info', methods=['GET'])
@login_required
def get_local_device_info():
    """获取本机设备信息"""
    try:
        # 获取主机名
        hostname = socket.gethostname()
        
        # 获取本机IP地址
        local_ip = None
        try:
            # 连接到外部地址来获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = '127.0.0.1'
        
        # 获取默认网关
        gateway = None
        try:
            gateways = netifaces.gateways()
            default_gateway = gateways.get('default', {})
            if netifaces.AF_INET in default_gateway:
                gateway = default_gateway[netifaces.AF_INET][0]
        except:
            gateway = None

        gateway_override = session.get(LOCAL_GATEWAY_SESSION_KEY)
        if gateway_override:
            gateway = gateway_override
        
        # 获取MAC地址
        mac_address = None
        try:
            # 获取默认网络接口的MAC地址
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface.startswith('lo') or interface.startswith('Loopback'):
                    continue
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        if addr['addr'] == local_ip:
                            if netifaces.AF_LINK in addrs:
                                mac_address = addrs[netifaces.AF_LINK][0]['addr']
                                break
                if mac_address:
                    break
        except:
            pass
        
        # 获取系统信息
        system_info = f"{platform.system()} {platform.release()}"
        
        # 获取网络接口信息
        interfaces = []
        try:
            for interface_name in netifaces.interfaces():
                if interface_name.startswith('lo') or interface_name.startswith('Loopback'):
                    continue
                    
                interface_info = {
                    'name': interface_name,
                    'addresses': [],
                    'mac': None
                }
                
                addrs = netifaces.ifaddresses(interface_name)
                
                # IPv4地址
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        interface_info['addresses'].append({
                            'type': 'IPv4',
                            'address': addr['addr'],
                            'netmask': addr.get('netmask', '')
                        })
                
                # IPv6地址
                if netifaces.AF_INET6 in addrs:
                    for addr in addrs[netifaces.AF_INET6]:
                        interface_info['addresses'].append({
                            'type': 'IPv6',
                            'address': addr['addr'],
                            'netmask': addr.get('netmask', '')
                        })
                
                # MAC地址
                if netifaces.AF_LINK in addrs:
                    interface_info['mac'] = addrs[netifaces.AF_LINK][0]['addr']
                
                if interface_info['addresses']:  # 只添加有地址的接口
                    interfaces.append(interface_info)
        except Exception as e:
            print(f"获取网络接口信息失败: {e}")
        
        # 检查并初始化本机设备到数据库
        try:
            filter_kwargs = {
                'user_id': current_user.id,
                'device_id': 'local_device'
            }
            
            create_kwargs = {
                'user_id': current_user.id,
                'device_id': 'local_device',
                'hostname': hostname,
                'ip_address': local_ip,
                'device_type': 'pc',
                'vendor': 'Local',
                'model': 'Unknown',
                'mac_address': mac_address or '',
                'status': 'online',
                'is_local': True
            }
            
            update_kwargs = {
                'hostname': hostname,
                'ip_address': local_ip,
                'mac_address': mac_address or '',
                'status': 'online',
                'last_seen': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            local_device, created = safe_create_or_update(
                db, NetworkDevice, filter_kwargs, update_kwargs, create_kwargs
            )
            
            if created:
                print(f"本机设备已初始化到数据库: {hostname} ({local_ip})")
            else:
                print(f"本机设备信息已更新: {hostname} ({local_ip})")
                
        except Exception as e:
            print(f"处理本机设备失败: {e}")
            return jsonify({'error': '初始化本机设备失败'}), 500
        
        return jsonify({
            'success': True,
            'hostname': hostname,
            'ip': local_ip,
            'mac': mac_address,
            'gateway': gateway,
            'gateway_overridden': bool(gateway_override),
            'system': system_info,
            'interfaces': interfaces
        })
        
    except Exception as e:
        print(f"获取本机信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'hostname': 'localhost',
            'ip': '127.0.0.1',
            'mac': None,
            'gateway': None,
            'gateway_overridden': False,
            'system': 'Unknown',
            'interfaces': []
        }), 500

@topology_bp.route('/local-info/gateway', methods=['PUT'])
@login_required
def update_local_gateway():
    """Update the application-level gateway override for the current session."""
    try:
        data = request.get_json() or {}
        gateway = (data.get('gateway') or '').strip()

        if not gateway:
            session.pop(LOCAL_GATEWAY_SESSION_KEY, None)
            session.modified = True
            return jsonify({
                'success': True,
                'gateway': None,
                'message': 'Gateway override cleared'
            })

        try:
            ipaddress.ip_address(gateway)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid gateway address'
            }), 400

        session[LOCAL_GATEWAY_SESSION_KEY] = gateway
        session.modified = True
        return jsonify({
            'success': True,
            'gateway': gateway,
            'message': 'Gateway updated'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
