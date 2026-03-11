from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # 关联关系
    chat_sessions = db.relationship('ChatSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    topology_data = db.relationship('TopologyData', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    network_devices = db.relationship('NetworkDevice', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    command_sessions = db.relationship('CommandSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'is_admin': self.is_admin
        }

class ChatSession(db.Model):
    """聊天会话模型"""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='新对话')
    mode = db.Column(db.String(20), default='chat')  # chat, build
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关联关系
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ChatSession {self.session_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'title': self.title,
            'mode': self.mode,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': self.messages.count()
        }

class ChatMessage(db.Model):
    """聊天消息模型"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    message_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, system, tool
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(db.Text)  # JSON格式的元数据
    tool_calls = db.Column(db.Text)  # JSON格式的工具调用信息
    tool_results = db.Column(db.Text)  # JSON格式的工具执行结果
    tool_status = db.Column(db.Text)  # JSON格式的工具状态信息
    tool_call_id = db.Column(db.String(100))  # 工具调用ID，用于关联工具调用和结果
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.message_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'metadata': json.loads(self.message_metadata) if self.message_metadata else {},
            'tool_calls': json.loads(self.tool_calls) if self.tool_calls else [],
            'tool_results': json.loads(self.tool_results) if self.tool_results else [],
            'tool_status': json.loads(self.tool_status) if self.tool_status else {},
            'tool_call_id': self.tool_call_id,
            'created_at': self.created_at.isoformat()
        }

class TopologyData(db.Model):
    """网络拓扑数据模型"""
    __tablename__ = 'topology_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), default='默认拓扑')
    description = db.Column(db.Text)
    topology_data = db.Column(db.Text, nullable=False)  # JSON格式的拓扑数据
    mode = db.Column(db.String(20), default='view')  # view, edit
    version = db.Column(db.String(20), default='1.0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<TopologyData {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'topology_data': json.loads(self.topology_data) if self.topology_data else {},
            'mode': self.mode,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class NetworkDevice(db.Model):
    """网络设备模型"""
    __tablename__ = 'network_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.String(100), nullable=False, index=True)
    hostname = db.Column(db.String(200))
    ip_address = db.Column(db.String(45), nullable=False)  # 支持IPv6
    device_type = db.Column(db.String(50), nullable=False)
    vendor = db.Column(db.String(100))
    model = db.Column(db.String(100))
    os_version = db.Column(db.String(100))
    mac_address = db.Column(db.String(17))
    status = db.Column(db.String(20), default='unknown')  # online, offline, unknown
    last_seen = db.Column(db.DateTime)
    configuration = db.Column(db.Text)  # JSON格式的设备配置
    credentials = db.Column(db.Text)  # 加密的认证信息 (JSON: {"username": "...", "password": "..."})
    is_local = db.Column(db.Boolean, default=False)  # 是否为本机设备
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    interfaces = db.Column(db.Text)  # JSON string of interfaces
    
    # 复合唯一索引
    __table_args__ = (db.UniqueConstraint('user_id', 'device_id', name='_user_device_uc'),)
    
    def __repr__(self):
        return f'<NetworkDevice {self.device_id}>'
    
    def to_dict(self):
        result = {
            'id': self.id,
            'device_id': self.device_id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'vendor': self.vendor,
            'model': self.model,
            'os_version': self.os_version,
            'mac_address': self.mac_address,
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'configuration': json.loads(self.configuration) if self.configuration else {},
            'is_local': self.is_local,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'has_ssh_credentials': bool(self.credentials and json.loads(self.credentials).get('username') and json.loads(self.credentials).get('password'))
        }
        
        # 安全地添加 interfaces 字段，如果该列存在于数据库中
        try:
            result['interfaces'] = json.loads(self.interfaces) if self.interfaces else []
        except AttributeError:
            # 如果数据库中没有 interfaces 列，则返回空列表
            result['interfaces'] = []
            
        return result

class CloudSyncLog(db.Model):
    """云端同步日志模型"""
    __tablename__ = 'cloud_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)  # chat, topology, device
    data_id = db.Column(db.String(100), nullable=False)
    operation = db.Column(db.String(20), nullable=False)  # create, update, delete
    status = db.Column(db.String(20), nullable=False)  # success, failed, pending
    error_message = db.Column(db.Text)
    sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    retry_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<CloudSyncLog {self.data_type}:{self.data_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_type': self.data_type,
            'data_id': self.data_id,
            'operation': self.operation,
            'status': self.status,
            'error_message': self.error_message,
            'sync_time': self.sync_time.isoformat(),
            'retry_count': self.retry_count
        }

class CommandSession(db.Model):
    """命令行会话模型"""
    __tablename__ = 'command_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, closed
    session_data = db.Column(db.Text)  # JSON格式的会话数据
    
    # 关联关系
    device = db.relationship('NetworkDevice', backref='command_sessions')
    history = db.relationship('CommandHistory', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CommandSession {self.session_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'created_at': self.created_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'status': self.status,
            'session_data': json.loads(self.session_data) if self.session_data else {}
        }

class CommandHistory(db.Model):
    """命令历史记录模型"""
    __tablename__ = 'command_history'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), db.ForeignKey('command_sessions.session_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=False)
    command = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')  # success, error
    error_message = db.Column(db.Text)
    
    # 关联关系
    user = db.relationship('User', backref='command_history')
    device = db.relationship('NetworkDevice', backref='command_history')
    
    def __repr__(self):
        return f'<CommandHistory {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'command': self.command,
            'output': self.output,
            'executed_at': self.executed_at.isoformat(),
            'status': self.status,
            'error_message': self.error_message
        }