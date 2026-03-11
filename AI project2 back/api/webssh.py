from flask import Blueprint, request, jsonify, current_app, session
from flask_socketio import emit, join_room, leave_room
import paramiko
import threading
import socket
import select
import time
import json
import os
import uuid
from models import NetworkDevice, db
from flask_login import current_user, login_required

webssh_bp = Blueprint('webssh', __name__)

# 存储活动的SSH会话
active_ssh_sessions = {}

# 获取设备凭据
def get_device_credentials(device_id):
    device = NetworkDevice.query.filter_by(device_id=device_id).first()
    if not device:
        return None, None
    
    credentials = device.credentials
    if not credentials:
        return None, None
    
    try:
        creds = json.loads(credentials)
        return creds.get('username'), creds.get('password')
    except:
        return None, None

# 初始化SSH客户端
def create_ssh_client(hostname, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, port=port, username=username, password=password)
        return client
    except Exception as e:
        current_app.logger.error(f"SSH连接错误: {str(e)}")
        return None

# 处理SSH数据传输的线程
class SSHThread(threading.Thread):
    def __init__(self, ssh_session_id, client, socketio):
        super(SSHThread, self).__init__()
        self.ssh_session_id = ssh_session_id
        self.client = client
        self.socketio = socketio
        self.channel = client.invoke_shell()
        self.channel.settimeout(0.1)
        self.running = True
        
    def run(self):
        while self.running and not self.channel.closed:
            try:
                # 检查通道是否可读
                r, w, e = select.select([self.channel], [], [], 0.1)
                if self.channel in r:
                    data = self.channel.recv(1024)
                    if len(data) == 0:
                        self.running = False
                        break
                    
                    # 发送数据到WebSocket
                    self.socketio.emit('ssh_output', {
                        'data': data.decode('utf-8', errors='replace'),
                        'session_id': self.ssh_session_id
                    }, room=self.ssh_session_id)
            except socket.timeout:
                pass
            except Exception as e:
                current_app.logger.error(f"SSH线程错误: {str(e)}")
                self.running = False
                break
                
        # 关闭连接
        self.channel.close()
        self.client.close()
        
    def stop(self):
        self.running = False
        
    def send_command(self, command):
        if self.channel and not self.channel.closed:
            self.channel.send(command)

# 注册WebSocket事件处理程序
def register_webssh_events(socketio):
    @socketio.on('connect_ssh')
    @login_required
    def handle_connect_ssh(data):
        device_id = data.get('device_id')
        if not device_id:
            emit('ssh_error', {'message': '设备ID不能为空'})
            return
            
        # 获取设备信息
        device = NetworkDevice.query.filter_by(device_id=device_id).first()
        if not device:
            emit('ssh_error', {'message': '设备不存在'})
            return
            
        # 获取凭据
        username, password = get_device_credentials(device_id)
        if not username or not password:
            emit('ssh_error', {'message': '设备凭据不可用'})
            return
            
        # 创建SSH客户端
        client = create_ssh_client(device.ip_address, 22, username, password)
        if not client:
            emit('ssh_error', {'message': 'SSH连接失败'})
            return
            
        # 创建会话ID并加入房间
        ssh_session_id = str(uuid.uuid4())
        join_room(ssh_session_id)
        
        # 创建并启动SSH线程
        ssh_thread = SSHThread(ssh_session_id, client, socketio)
        ssh_thread.daemon = True
        ssh_thread.start()
        
        # 存储会话信息
        active_ssh_sessions[ssh_session_id] = {
            'thread': ssh_thread,
            'device_id': device_id,
            'user_id': current_user.id,
            'start_time': time.time()
        }
        
        emit('ssh_connected', {
            'session_id': ssh_session_id,
            'device_name': device.hostname or device.ip_address
        })
    
    @socketio.on('disconnect_ssh')
    def handle_disconnect_ssh(data):
        session_id = data.get('session_id')
        if session_id and session_id in active_ssh_sessions:
            ssh_session = active_ssh_sessions[session_id]
            ssh_session['thread'].stop()
            leave_room(session_id)
            del active_ssh_sessions[session_id]
            emit('ssh_disconnected', {'session_id': session_id})
    
    @socketio.on('ssh_input')
    def handle_ssh_input(data):
        session_id = data.get('session_id')
        command = data.get('command')
        
        if not session_id or not command:
            return
            
        if session_id in active_ssh_sessions:
            ssh_session = active_ssh_sessions[session_id]
            ssh_session['thread'].send_command(command)

# API路由
@webssh_bp.route('/devices', methods=['GET'])
@login_required
def get_ssh_devices():
    devices = NetworkDevice.query.all()
    result = []
    
    for device in devices:
        username, password = get_device_credentials(device.device_id)
        can_ssh = username is not None and password is not None
        
        result.append({
            'device_id': device.device_id,
            'hostname': device.hostname or '',
            'ip_address': device.ip_address,
            'device_type': device.device_type,
            'can_ssh': can_ssh
        })
    
    return jsonify(result)

@webssh_bp.route('/sessions', methods=['GET'])
@login_required
def get_active_sessions():
    user_sessions = []
    
    for session_id, session_data in active_ssh_sessions.items():
        if session_data['user_id'] == current_user.id:
            device = NetworkDevice.query.filter_by(device_id=session_data['device_id']).first()
            if device:
                user_sessions.append({
                    'session_id': session_id,
                    'device_name': device.hostname or device.ip_address,
                    'start_time': session_data['start_time']
                })
    
    return jsonify(user_sessions)