from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json
import uuid

db = SQLAlchemy()


# ============================================================
# 核心业务表
# ============================================================

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
    tool_executions = db.relationship('ToolExecution', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    code_executions = db.relationship('CodeExecution', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    login_history = db.relationship('LoginHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    user_settings = db.relationship('UserSetting', backref='user', uselist=False, cascade='all, delete-orphan')
    workflows = db.relationship('Workflow', backref='user', lazy='dynamic', cascade='all, delete-orphan')

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
    mode = db.Column(db.String(20), default='chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

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
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(db.Text)
    tool_calls = db.Column(db.Text)
    tool_results = db.Column(db.Text)
    tool_status = db.Column(db.Text)
    tool_call_id = db.Column(db.String(100))
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
    topology_data = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(20), default='view')
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
    ip_address = db.Column(db.String(45), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    vendor = db.Column(db.String(100))
    model = db.Column(db.String(100))
    os_version = db.Column(db.String(100))
    mac_address = db.Column(db.String(17))
    status = db.Column(db.String(20), default='unknown')
    last_seen = db.Column(db.DateTime)
    configuration = db.Column(db.Text)
    credentials = db.Column(db.Text)
    is_local = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    interfaces = db.Column(db.Text)

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
        try:
            result['interfaces'] = json.loads(self.interfaces) if self.interfaces else []
        except AttributeError:
            result['interfaces'] = []
        return result


class CloudSyncLog(db.Model):
    """云端同步日志模型"""
    __tablename__ = 'cloud_sync_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)
    data_id = db.Column(db.String(100), nullable=False)
    operation = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
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
    status = db.Column(db.String(20), default='active')
    session_data = db.Column(db.Text)

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
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text)

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


# ============================================================
# 高优先级扩展表
# ============================================================

class ToolExecution(db.Model):
    """自定义工具执行记录模型"""
    __tablename__ = 'tool_executions'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    params = db.Column(db.Text)
    result = db.Column(db.Text)
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text)
    execution_time_ms = db.Column(db.Integer)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ToolExecution {self.tool_id} #{self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'tool_id': self.tool_id,
            'user_id': self.user_id,
            'params': json.loads(self.params) if self.params else {},
            'result': json.loads(self.result) if self.result else {},
            'status': self.status,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'executed_at': self.executed_at.isoformat()
        }


class AuditLog(db.Model):
    """操作审计日志模型"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(100))
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    status = db.Column(db.String(20), default='success')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog {self.action}:{self.resource_type} #{self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'detail': json.loads(self.detail) if self.detail else {},
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class LoginHistory(db.Model):
    """登录历史模型"""
    __tablename__ = 'login_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    status = db.Column(db.String(20), default='success')
    fail_reason = db.Column(db.String(200))
    login_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<LoginHistory user={self.user_id} #{self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'fail_reason': self.fail_reason,
            'login_at': self.login_at.isoformat()
        }


class UserSetting(db.Model):
    """用户偏好设置模型"""
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='zh-CN')
    notifications_enabled = db.Column(db.Boolean, default=True)
    auto_save = db.Column(db.Boolean, default=True)
    code_font_size = db.Column(db.Integer, default=14)
    terminal_font_size = db.Column(db.Integer, default=14)
    max_history = db.Column(db.Integer, default=100)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserSetting user={self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'theme': self.theme,
            'language': self.language,
            'notifications_enabled': self.notifications_enabled,
            'auto_save': self.auto_save,
            'code_font_size': self.code_font_size,
            'terminal_font_size': self.terminal_font_size,
            'max_history': self.max_history,
            'updated_at': self.updated_at.isoformat()
        }


# ============================================================
# 中优先级扩展表
# ============================================================

class CodeExecution(db.Model):
    """代码执行历史模型 (SDK开发环境)"""
    __tablename__ = 'code_executions'

    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255))
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default='python')
    output = db.Column(db.Text)
    error = db.Column(db.Text)
    return_code = db.Column(db.Integer)
    status = db.Column(db.String(20), default='success')
    execution_time_ms = db.Column(db.Integer)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<CodeExecution {self.execution_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'code': self.code,
            'language': self.language,
            'output': self.output,
            'error': self.error,
            'return_code': self.return_code,
            'status': self.status,
            'execution_time_ms': self.execution_time_ms,
            'executed_at': self.executed_at.isoformat()
        }


class ConfigBackup(db.Model):
    """设备配置备份模型"""
    __tablename__ = 'config_backups'

    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    config_text = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(50), default='running')
    version = db.Column(db.String(50))
    description = db.Column(db.Text)
    file_size_bytes = db.Column(db.Integer)
    checksum = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    device = db.relationship('NetworkDevice', backref='config_backups')

    def __repr__(self):
        return f'<ConfigBackup {self.backup_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'config_type': self.config_type,
            'version': self.version,
            'description': self.description,
            'file_size_bytes': self.file_size_bytes,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat()
        }


# ============================================================
# 低优先级扩展表（未实现功能的预留表）
# ============================================================

class Workflow(db.Model):
    """工作流定义模型"""
    __tablename__ = 'workflows'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    is_active = db.Column(db.Boolean, default=True)
    version = db.Column(db.String(20), default='1.0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = db.relationship('WorkflowStep', backref='workflow', lazy='dynamic', cascade='all, delete-orphan')
    executions = db.relationship('WorkflowExecution', backref='workflow', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Workflow {self.workflow_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'is_active': self.is_active,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'step_count': self.steps.count()
        }


class WorkflowStep(db.Model):
    """工作流步骤模型"""
    __tablename__ = 'workflow_steps'

    id = db.Column(db.Integer, primary_key=True)
    step_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False, default=0)
    timeout_seconds = db.Column(db.Integer, default=300)
    retry_count = db.Column(db.Integer, default=0)
    on_failure = db.Column(db.String(20), default='stop')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WorkflowStep {self.step_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'step_id': self.step_id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'action_type': self.action_type,
            'config': json.loads(self.config) if self.config else {},
            'order': self.order,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'on_failure': self.on_failure,
            'created_at': self.created_at.isoformat()
        }


class WorkflowExecution(db.Model):
    """工作流执行历史模型"""
    __tablename__ = 'workflow_executions'

    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=0)
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    step_results = db.relationship('WorkflowStepResult', backref='execution', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<WorkflowExecution {self.execution_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'workflow_id': self.workflow_id,
            'user_id': self.user_id,
            'status': self.status,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'result': json.loads(self.result) if self.result else {},
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat()
        }


class WorkflowStepResult(db.Model):
    """工作流步骤执行结果模型"""
    __tablename__ = 'workflow_step_results'

    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.Integer, db.ForeignKey('workflow_executions.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('workflow_steps.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    output = db.Column(db.Text)
    error = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration_ms = db.Column(db.Integer)

    def __repr__(self):
        return f'<WorkflowStepResult step={self.step_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'step_id': self.step_id,
            'status': self.status,
            'output': self.output,
            'error': self.error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_ms': self.duration_ms
        }


class AiModelConfig(db.Model):
    """AI模型配置模型（多模型驱动 MLD）"""
    __tablename__ = 'ai_model_configs'

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    api_base = db.Column(db.String(500))
    api_key = db.Column(db.Text)
    model_id = db.Column(db.String(100))
    is_local = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    max_tokens = db.Column(db.Integer, default=4096)
    temperature = db.Column(db.Float, default=0.7)
    top_p = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usage_logs = db.relationship('ModelUsageLog', backref='model_config', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AiModelConfig {self.config_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'config_id': self.config_id,
            'user_id': self.user_id,
            'name': self.name,
            'provider': self.provider,
            'api_base': self.api_base,
            'model_id': self.model_id,
            'is_local': self.is_local,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class ModelUsageLog(db.Model):
    """模型使用统计日志模型"""
    __tablename__ = 'model_usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    model_config_id = db.Column(db.Integer, db.ForeignKey('ai_model_configs.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    latency_ms = db.Column(db.Integer)
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text)
    request_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ModelUsageLog #{self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'model_config_id': self.model_config_id,
            'user_id': self.user_id,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'latency_ms': self.latency_ms,
            'status': self.status,
            'error_message': self.error_message,
            'request_type': self.request_type,
            'created_at': self.created_at.isoformat()
        }


class MonitoringRule(db.Model):
    """监控规则模型"""
    __tablename__ = 'monitoring_rules'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    metric = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    comparison = db.Column(db.String(10), default='gt')
    check_interval_seconds = db.Column(db.Integer, default=300)
    severity = db.Column(db.String(20), default='warning')
    is_enabled = db.Column(db.Boolean, default=True)
    notification_channels = db.Column(db.Text)
    last_checked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    device = db.relationship('NetworkDevice', backref='monitoring_rules')

    def __repr__(self):
        return f'<MonitoringRule {self.rule_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'name': self.name,
            'metric': self.metric,
            'threshold': self.threshold,
            'comparison': self.comparison,
            'check_interval_seconds': self.check_interval_seconds,
            'severity': self.severity,
            'is_enabled': self.is_enabled,
            'notification_channels': json.loads(self.notification_channels) if self.notification_channels else [],
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Alert(db.Model):
    """告警记录模型"""
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('monitoring_rules.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='warning')
    status = db.Column(db.String(20), default='open')
    current_value = db.Column(db.Float)
    threshold_value = db.Column(db.Float)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    resolution_note = db.Column(db.Text)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    device = db.relationship('NetworkDevice', backref='alerts')

    def __repr__(self):
        return f'<Alert {self.alert_id} [{self.severity}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'status': self.status,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_note': self.resolution_note,
            'triggered_at': self.triggered_at.isoformat()
        }


class TopologyConfigGeneration(db.Model):
    """拓扑配置生成历史模型"""
    __tablename__ = 'topology_config_generations'

    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    topology_id = db.Column(db.Integer, db.ForeignKey('topology_data.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('network_devices.id'), nullable=True)
    generated_config = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(50))
    device_vendor = db.Column(db.String(50))
    prompt_used = db.Column(db.Text)
    model_used = db.Column(db.String(100))
    status = db.Column(db.String(20), default='generated')
    is_applied = db.Column(db.Boolean, default=False)
    applied_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    topology = db.relationship('TopologyData', backref='config_generations')
    device = db.relationship('NetworkDevice', backref='config_generations')

    def __repr__(self):
        return f'<TopologyConfigGeneration {self.generation_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'generation_id': self.generation_id,
            'topology_id': self.topology_id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'config_type': self.config_type,
            'device_vendor': self.device_vendor,
            'model_used': self.model_used,
            'status': self.status,
            'is_applied': self.is_applied,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }
