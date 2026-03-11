from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, NetworkDevice
from services.network_service import NetworkService
import logging

network_bp = Blueprint('network', __name__)
logger = logging.getLogger(__name__)

@network_bp.route('/status', methods=['GET'])
@login_required
def get_network_status():
    """获取网络状态概览"""
    try:
        # 使用NetworkService获取网络状态
        network_service = NetworkService()
        status_data = network_service.get_network_status(
            include_recent_activity=True,
            include_device_groups=True
        )
        
        return jsonify({
            'success': True,
            'data': {
                'summary': status_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取网络状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取网络状态失败'
        }), 500

@network_bp.route('/devices', methods=['GET'])
@login_required
def get_network_devices():
    """获取网络设备列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        
        query = NetworkDevice.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        devices = query.order_by(
            NetworkDevice.last_seen.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'devices': [
                    {
                        'id': device.id,
                        'hostname': device.hostname,
                        'ip_address': device.ip_address,
                        'mac_address': device.mac_address,
                        'device_type': device.device_type,
                        'vendor': device.vendor,
                        'status': device.status,
                        'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                        'response_time': device.response_time
                    }
                    for device in devices.items
                ],
                'pagination': {
                    'page': devices.page,
                    'pages': devices.pages,
                    'per_page': devices.per_page,
                    'total': devices.total,
                    'has_next': devices.has_next,
                    'has_prev': devices.has_prev
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取设备列表失败'
        }), 500

@network_bp.route('/scan', methods=['POST'])
@login_required
def start_network_scan():
    """启动网络扫描"""
    try:
        network_service = NetworkService()
        
        # 获取扫描参数
        data = request.get_json() or {}
        target_network = data.get('network', '192.168.1.0/24')
        scan_type = data.get('type', 'ping')
        
        # 启动异步扫描
        scan_id = network_service.start_scan(
            target_network=target_network,
            scan_type=scan_type,
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'data': {
                'scan_id': scan_id,
                'message': '网络扫描已启动'
            }
        })
        
    except Exception as e:
        logger.error(f"启动网络扫描失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '启动网络扫描失败'
        }), 500

@network_bp.route('/scan/<scan_id>/status', methods=['GET'])
@login_required
def get_scan_status(scan_id):
    """获取扫描状态"""
    try:
        network_service = NetworkService()
        status = network_service.get_scan_status(scan_id)
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取扫描状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取扫描状态失败'
        }), 500