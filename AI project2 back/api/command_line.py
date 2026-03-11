from flask import Blueprint, request, jsonify, current_app, session
from flask_login import login_required, current_user
from models import db, NetworkDevice, CommandSession, CommandHistory
from services.device_managers.base_manager import BaseDeviceManager
from services.device_managers.cisco_manager import CiscoDeviceManager
from services.device_managers.huawei_manager import HuaweiDeviceManager
from services.device_managers.h3c_manager import H3CDeviceManager
from datetime import datetime
import uuid
import json
import os
import logging

command_line_bp = Blueprint('command_line', __name__)

# 存储活动会话
active_sessions = {}

# 获取设备管理器实例
def get_device_manager(device_type):
    if device_type.lower() == 'cisco':
        return CiscoDeviceManager()
    elif device_type.lower() == 'huawei':
        return HuaweiDeviceManager()
    elif device_type.lower() == 'h3c':
        return H3CDeviceManager()
    else:
        # 默认使用基础管理器
        return BaseDeviceManager()

@command_line_bp.route('/connect', methods=['POST'])
@login_required
def connect_device():
    data = request.json
    device_id = data.get('device_id')
    username = data.get('username')
    password = data.get('password')
    
    if not device_id or not username or not password:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        })
    
    try:
        # 获取设备信息
        device = db.session.get(NetworkDevice, device_id)
        if not device:
            return jsonify({
                'success': False,
                'message': '设备不存在'
            })
        
        # 获取设备管理器
        device_manager = get_device_manager(device.device_type)
        
        # 连接到设备
        connection = device_manager.connect_ssh(
            device.ip_address,
            username,
            password,
            device.port or 22
        )
        
        if not connection['success']:
            return jsonify({
                'success': False,
                'message': f"连接失败: {connection['error']}"
            })
        
        # 创建交互式shell
        shell = device_manager.create_interactive_shell(connection['connection'])
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 存储会话信息
        active_sessions[session_id] = {
            'device_id': device_id,
            'device_type': device.device_type,
            'connection': connection['connection'],
            'shell': shell,
            'device_manager': device_manager,
            'user_id': current_user.id,
            'created_at': datetime.now()
        }
        
        # 创建会话记录
        command_session = CommandSession(
            session_id=session_id,
            user_id=current_user.id,
            device_id=device_id,
            created_at=datetime.now(),
            status='active'
        )
        db.session.add(command_session)
        db.session.commit()
        
        # 获取欢迎消息
        welcome_message = device_manager.get_welcome_message(shell)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'welcome_message': welcome_message
        })
    
    except Exception as e:
        logging.error(f"连接设备错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"连接设备时发生错误: {str(e)}"
        })

@command_line_bp.route('/create_session', methods=['POST'])
@login_required
def create_session():
    data = request.json
    session_name = data.get('session_name')
    device_id = data.get('device_id')
    username = data.get('username')
    password = data.get('password')
    device_type = data.get('device_type')
    
    if not device_id or not username or not password:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        })
    
    try:
        # 获取设备信息
        device = db.session.get(NetworkDevice, device_id)
        if not device:
            return jsonify({
                'success': False,
                'message': '设备不存在'
            })
        
        # 获取设备管理器
        device_manager = get_device_manager(device_type or device.device_type)
        
        # 连接到设备
        connection = device_manager.connect_ssh(
            device.ip_address,
            username,
            password,
            device.port or 22
        )
        
        if not connection['success']:
            return jsonify({
                'success': False,
                'message': f"连接失败: {connection['error']}"
            })
        
        # 创建交互式shell
        shell = device_manager.create_interactive_shell(connection['connection'])
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 存储会话信息
        active_sessions[session_id] = {
            'device_id': device_id,
            'device_type': device_type or device.device_type,
            'connection': connection['connection'],
            'shell': shell,
            'device_manager': device_manager,
            'user_id': current_user.id,
            'created_at': datetime.now(),
            'session_name': session_name or f"{device.hostname or device.ip_address} 会话"
        }
        
        # 创建会话记录
        session_data = {
            'session_name': session_name,
            'username': username,
            'device_type': device_type
        }
        
        command_session = CommandSession(
            session_id=session_id,
            user_id=current_user.id,
            device_id=device_id,
            created_at=datetime.now(),
            status='active',
            session_data=json.dumps(session_data)
        )
        db.session.add(command_session)
        db.session.commit()
        
        # 获取欢迎消息
        welcome_message = device_manager.get_welcome_message(shell)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'device': {
                'id': device.id,
                'name': device.hostname or device.ip_address,
                'type': device_type or device.device_type,
                'ip': device.ip_address
            },
            'welcome_message': welcome_message
        })
    
    except Exception as e:
        logging.error(f"创建会话错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"创建会话时发生错误: {str(e)}"
        })

@command_line_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect_device():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({
            'success': False,
            'message': '无效的会话ID'
        })
    
    try:
        # 获取会话信息
        session_info = active_sessions[session_id]
        
        # 关闭连接
        if 'connection' in session_info and session_info['connection']:
            session_info['connection'].close()
        
        # 更新会话状态
        command_session = CommandSession.query.filter_by(session_id=session_id).first()
        if command_session:
            command_session.status = 'closed'
            command_session.closed_at = datetime.now()
            db.session.commit()
        
        # 移除会话
        del active_sessions[session_id]
        
        return jsonify({
            'success': True,
            'message': '已断开连接'
        })
    
    except Exception as e:
        logging.error(f"断开连接错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"断开连接时发生错误: {str(e)}"
        })

@command_line_bp.route('/execute', methods=['POST'])
@login_required
def execute_command():
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    if not session_id or not command or session_id not in active_sessions:
        return jsonify({
            'success': False,
            'message': '无效的会话ID或命令为空'
        })
    
    try:
        # 获取会话信息
        session_info = active_sessions[session_id]
        device_manager = session_info['device_manager']
        shell = session_info['shell']
        
        # 执行命令
        result = device_manager.execute_interactive_command(shell, command)
        
        # 记录命令历史
        command_history = CommandHistory(
            session_id=session_id,
            user_id=current_user.id,
            device_id=session_info['device_id'],
            command=command,
            output=result,
            executed_at=datetime.now()
        )
        db.session.add(command_history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'output': result
        })
    
    except Exception as e:
        logging.error(f"执行命令错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"执行命令时发生错误: {str(e)}"
        })

@command_line_bp.route('/autocomplete', methods=['POST'])
@login_required
def autocomplete_command():
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    if not session_id or not command or session_id not in active_sessions:
        return jsonify({
            'success': False,
            'message': '无效的会话ID或命令为空'
        })
    
    try:
        # 获取会话信息
        session_info = active_sessions[session_id]
        device_manager = session_info['device_manager']
        shell = session_info['shell']
        
        # 获取自动完成建议
        suggestions = device_manager.get_command_suggestions(shell, command)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
    
    except Exception as e:
        logging.error(f"命令自动完成错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取命令建议时发生错误: {str(e)}"
        })

@command_line_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    try:
        # 获取用户的会话列表
        sessions = CommandSession.query.filter_by(
            user_id=current_user.id
        ).order_by(CommandSession.created_at.desc()).limit(10).all()
        
        sessions_list = []
        for session in sessions:
            device = db.session.get(NetworkDevice, session.device_id)
            sessions_list.append({
                'id': session.session_id,
                'device_id': session.device_id,
                'device_name': device.name if device else 'Unknown',
                'created_at': session.created_at.isoformat(),
                'status': session.status
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_list
        })
    
    except Exception as e:
        logging.error(f"获取会话列表错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取会话列表时发生错误: {str(e)}"
        })

@command_line_bp.route('/restore_session', methods=['POST'])
@login_required
def restore_session():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({
            'success': False,
            'message': '会话ID不能为空'
        })
    
    try:
        # 检查会话是否存在
        command_session = CommandSession.query.filter_by(session_id=session_id).first()
        if not command_session:
            return jsonify({
                'success': False,
                'message': '会话不存在'
            })
        
        # 检查会话是否属于当前用户
        if command_session.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权访问此会话'
            })
        
        # 如果会话已经在活动列表中，直接返回
        if session_id in active_sessions:
            device = db.session.get(NetworkDevice, command_session.device_id)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'device': {
                    'id': device.id,
                    'name': device.name,
                    'type': device.device_type,
                    'ip': device.ip_address
                }
            })
        
        # 如果会话不在活动列表中，需要重新连接
        # 这里需要用户重新提供凭据，所以返回需要重新连接的信息
        return jsonify({
            'success': False,
            'message': '会话已过期，请重新连接',
            'need_reconnect': True
        })
    
    except Exception as e:
        logging.error(f"恢复会话错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"恢复会话时发生错误: {str(e)}"
        })

@command_line_bp.route('/history', methods=['GET'])
@login_required
def get_command_history():
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({
            'success': False,
            'message': '会话ID不能为空'
        })
    
    try:
        # 获取命令历史
        history = CommandHistory.query.filter_by(
            session_id=session_id
        ).order_by(CommandHistory.executed_at.desc()).limit(50).all()
        
        history_list = []
        for entry in history:
            history_list.append({
                'id': entry.id,
                'command': entry.command,
                'output': entry.output,
                'executed_at': entry.executed_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
    
    except Exception as e:
        logging.error(f"获取命令历史错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取命令历史时发生错误: {str(e)}"
        })


@command_line_bp.route('/devices', methods=['GET'])
@login_required
def get_devices():
    """获取可用的网络设备列表"""
    try:
        # 查询所有设备
        devices = NetworkDevice.query.all()
        
        # 构建设备列表
        device_list = []
        for device in devices:
            device_list.append({
                'id': device.id,
                'name': device.hostname or device.device_id,
                'ip_address': device.ip_address,
                'device_type': device.device_type,
                'description': device.model or device.vendor
            })
        
        return jsonify({
            'success': True,
            'devices': device_list
        })
    except Exception as e:
        current_app.logger.error(f"Error getting devices: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取设备列表失败: {str(e)}"
        }), 500