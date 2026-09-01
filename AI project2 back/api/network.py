from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
import logging

from models import NetworkDevice
from services.network_service import NetworkService

network_bp = Blueprint('network', __name__)
logger = logging.getLogger(__name__)


@network_bp.route('/status', methods=['GET'])
@login_required
def get_network_status():
    """Return network status summary."""
    try:
        network_service = NetworkService()
        status_data = network_service.get_network_status(
            include_recent_activity=True,
            include_device_groups=True,
        )
        return jsonify({
            'success': True,
            'data': {
                'summary': status_data,
            },
        })
    except Exception as exc:
        logger.error("Failed to load network status: %s", exc)
        return jsonify({
            'success': False,
            'error': 'Failed to load network status',
        }), 500


@network_bp.route('/devices', methods=['GET'])
@login_required
def get_network_devices():
    """Return paginated device list."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')

        query = NetworkDevice.query
        if status_filter:
            query = query.filter_by(status=status_filter)

        devices = query.order_by(NetworkDevice.last_seen.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
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
                        'response_time': device.response_time,
                    }
                    for device in devices.items
                ],
                'pagination': {
                    'page': devices.page,
                    'pages': devices.pages,
                    'per_page': devices.per_page,
                    'total': devices.total,
                    'has_next': devices.has_next,
                    'has_prev': devices.has_prev,
                },
            },
        })
    except Exception as exc:
        logger.error("Failed to load device list: %s", exc)
        return jsonify({
            'success': False,
            'error': 'Failed to load device list',
        }), 500


@network_bp.route('/scan', methods=['POST'])
@login_required
def start_network_scan():
    """Start a background network scan for legacy clients."""
    try:
        network_service = NetworkService()
        data = request.get_json() or {}
        target_network = data.get('network') or data.get('scan_range') or '192.168.1.0/24'
        scan_type = data.get('type') or data.get('scan_type') or 'ping'

        scan_id = network_service.start_scan(
            target_network=target_network,
            scan_type=scan_type,
            user_id=current_user.id,
        )

        return jsonify({
            'success': True,
            'data': {
                'scan_id': scan_id,
                'network': target_network,
                'scan_type': scan_type,
                'message': 'Network scan started',
            },
        })
    except Exception as exc:
        logger.error("Failed to start network scan: %s", exc)
        return jsonify({
            'success': False,
            'error': 'Failed to start network scan',
        }), 500


@network_bp.route('/scan/<scan_id>/status', methods=['GET'])
@login_required
def get_scan_status(scan_id):
    """Return background scan status for legacy clients."""
    try:
        network_service = NetworkService()
        status = network_service.get_scan_status(scan_id)
        if not status:
            return jsonify({
                'success': False,
                'error': 'Scan task not found',
            }), 404

        return jsonify({
            'success': True,
            'data': status,
        })
    except Exception as exc:
        logger.error("Failed to load scan status for %s: %s", scan_id, exc)
        return jsonify({
            'success': False,
            'error': 'Failed to load scan status',
        }), 500
