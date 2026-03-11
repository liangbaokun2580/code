from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional, URL, NumberRange
from models import db, User
import json
import os
import re
from datetime import datetime

settings_bp = Blueprint('settings', __name__)

class ConfigForm(FlaskForm):
    """配置表单"""
    # AI模型配置
    
    openai_api_key = StringField('OpenAI API Key', validators=[Optional()])
    openai_api_base = StringField('OpenAI API Base URL', validators=[Optional(), URL()])
    openai_model = StringField('OpenAI 模型', validators=[Optional()])
    openai_max_tokens = IntegerField('最大Token数', validators=[Optional(), NumberRange(min=1, max=32000)])
    openai_temperature = FloatField('温度参数', validators=[Optional(), NumberRange(min=0, max=2)])
    openai_top_p = FloatField('核采样', validators=[Optional(), NumberRange(min=0, max=1)])
    openai_presence_penalty = FloatField('话题新鲜度', validators=[Optional(), NumberRange(min=-2, max=2)])
    openai_frequency_penalty = FloatField('频率惩罚度', validators=[Optional(), NumberRange(min=-2, max=2)])
    
    # 数据库配置
    database_uri = StringField('数据库连接字符串', validators=[DataRequired()])
    database_pool_size = IntegerField('数据库连接池大小', validators=[Optional(), NumberRange(min=1, max=100)])
    
    # 网络扫描配置
    network_scan_timeout = IntegerField('扫描超时时间(秒)', validators=[Optional(), NumberRange(min=1, max=300)])
    network_scan_threads = IntegerField('扫描线程数', validators=[Optional(), NumberRange(min=1, max=200)])
    default_scan_range = StringField('默认扫描范围', validators=[Optional()])
    
    # Redis配置
    redis_url = StringField('Redis连接URL', validators=[DataRequired()])
    redis_host = StringField('Redis主机', validators=[Optional()])
    redis_port = IntegerField('Redis端口', validators=[Optional(), NumberRange(min=1, max=65535)])
    redis_password = StringField('Redis密码', validators=[Optional()])
    
    # 应用配置
    app_name = StringField('应用名称', validators=[Optional()])
    app_version = StringField('应用版本', validators=[Optional()])
    debug_mode = BooleanField('调试模式', validators=[Optional()])
    
    # 日志配置
    log_level = SelectField('日志级别', choices=[
        ('DEBUG', 'DEBUG'),
        ('INFO', 'INFO'),
        ('WARNING', 'WARNING'),
        ('ERROR', 'ERROR'),
        ('CRITICAL', 'CRITICAL')
    ], validators=[DataRequired()])

@settings_bp.route('/')
@login_required
def settings_page():
    """设置页面"""
    form = ConfigForm()
    # 加载当前配置到表单
    load_current_config(form)
    return render_template('settings.html', form=form)

@settings_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config_page():
    """配置页面"""
    form = ConfigForm()
    
    if request.method == 'GET':
        # 加载当前配置
        load_current_config(form)
    
    if form.validate_on_submit():
        try:
            # 保存配置
            save_config(form)

            print(form.openai_api_key.data)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '配置保存成功'})
            else:
                flash('配置保存成功！', 'success')
                return redirect(url_for('settings.config_page'))
                
        except Exception as e:
            error_msg = f'保存配置时发生错误: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
    
    elif request.method == 'POST':
        # 表单验证失败
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(f'{form[field].label.text}: {error}')
            return jsonify({'success': False, 'message': '; '.join(errors)})
    
    return render_template('settings.html', form=form)

@settings_bp.route('/config-form')
def config_form():
    """返回配置表单片段（用于嵌入到设置页面）"""
    form = ConfigForm()
    load_current_config(form)
    return render_template('config_form.html', form=form)

@settings_bp.route('/api/test-ai-connection', methods=['POST'])
@login_required
def test_ai_connection():
    """测试AI模型连接"""
    try:
        data = request.get_json()
        use_local = data.get('use_local', False)
        
        if use_local:
            # 测试本地模型连接
            base_url = data.get('local_base_url')
            model_name = data.get('local_model_name')
            
            if not base_url or not model_name:
                return jsonify({'success': False, 'message': '请填写完整的本地模型配置'})
            
            # 这里可以添加实际的连接测试逻辑
            # 例如：向本地模型API发送测试请求
            import requests
            test_url = f"{base_url.rstrip('/')}/api/tags"
            
            try:
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [model.get('name', '') for model in models]
                    if model_name in model_names:
                        return jsonify({'success': True, 'message': f'本地模型 {model_name} 连接成功'})
                    else:
                        return jsonify({'success': False, 'message': f'模型 {model_name} 不存在，可用模型: {", ".join(model_names)}'})
                else:
                    return jsonify({'success': False, 'message': f'连接失败，状态码: {response.status_code}'})
            except requests.RequestException as e:
                return jsonify({'success': False, 'message': f'连接本地模型失败: {str(e)}'})
        
        else:
            # 测试OpenAI连接
            api_key = data.get('api_key')
            api_base = data.get('api_base')
            model = data.get('model')
            
            if not api_key or not model:
                return jsonify({'success': False, 'message': '请填写完整的OpenAI配置'})
            
            # 这里可以添加实际的OpenAI连接测试逻辑
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=api_key,
                    base_url=api_base if api_base else None
                )
                
                # 发送测试请求
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                
                return jsonify({'success': True, 'message': f'OpenAI模型 {model} 连接成功'})
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'连接OpenAI失败: {str(e)}'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'测试连接时发生错误: {str(e)}'})

@settings_bp.route('/api/user/info')
@login_required
def get_user_info():
    """获取当前用户信息"""
    try:
        user_data = current_user.to_dict()
        return jsonify({
            'success': True,
            'data': user_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@settings_bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户资料"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': '邮箱地址不能为空'}), 400
        
        # 检查邮箱是否已被其他用户使用
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            return jsonify({'error': '该邮箱地址已被使用'}), 400
        
        # 更新用户信息
        current_user.email = email
        db.session.commit()
        
        return jsonify({'message': '个人资料更新成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/user/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': '密码不能为空'}), 400
        
        # 验证当前密码
        if not check_password_hash(current_user.password_hash, current_password):
            return jsonify({'error': '当前密码错误'}), 400
        
        # 验证新密码强度
        if len(new_password) < 8:
            return jsonify({'error': '密码长度至少8位'}), 400
        
        # 更新密码
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({'message': '密码修改成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/user/preferences', methods=['GET', 'PUT'])
@login_required
def user_preferences():
    """用户偏好设置"""
    if request.method == 'GET':
        # 获取用户偏好设置
        preferences = session.get('user_preferences', {
            'theme': 'light',
            'language': 'zh-CN',
            'notifications': True
        })
        return jsonify(preferences)
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # 验证数据
            valid_themes = ['light', 'dark', 'auto']
            valid_languages = ['zh-CN', 'en-US']
            
            theme = data.get('theme', 'light')
            language = data.get('language', 'zh-CN')
            notifications = data.get('notifications', True)
            
            if theme not in valid_themes:
                return jsonify({'error': '无效的主题设置'}), 400
            
            if language not in valid_languages:
                return jsonify({'error': '无效的语言设置'}), 400
            
            # 保存偏好设置到session
            preferences = {
                'theme': theme,
                'language': language,
                'notifications': bool(notifications)
            }
            
            session['user_preferences'] = preferences
            
            return jsonify({'message': '偏好设置保存成功'})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/user/admin-check')
@login_required
def check_admin():
    """检查用户是否为管理员"""
    return jsonify({
        'is_admin': current_user.is_admin,
        'username': current_user.username
    })

# 用户统计信息（仅管理员）
@settings_bp.route('/api/admin/users')
@login_required
def get_users():
    """获取用户列表（仅管理员）"""
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    try:
        users = User.query.all()
        users_data = [user.to_dict() for user in users]
        return jsonify(users_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """更新用户信息（仅管理员）"""
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # 更新用户信息
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        if 'is_admin' in data:
            # 防止删除最后一个管理员
            if not data['is_admin'] and user.is_admin:
                admin_count = User.query.filter_by(is_admin=True).count()
                if admin_count <= 1:
                    return jsonify({'error': '不能删除最后一个管理员'}), 400
            user.is_admin = bool(data['is_admin'])
        
        db.session.commit()
        
        return jsonify({'message': '用户信息更新成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """删除用户（仅管理员）"""
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        
        # 防止删除自己
        if user.id == current_user.id:
            return jsonify({'error': '不能删除自己的账户'}), 400
        
        # 防止删除最后一个管理员
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'error': '不能删除最后一个管理员'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': '用户删除成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 系统统计信息（仅管理员）
@settings_bp.route('/api/admin/stats')
@login_required
def get_system_stats():
    """获取系统统计信息（仅管理员）"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': '权限不足'}), 403
        
    try:
        from models import ChatSession, TopologyData, NetworkDevice
        
        # 获取用户统计
        user_count = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        # 获取聊天会话统计
        chat_session_count = ChatSession.query.count()
        
        # 获取拓扑数据统计
        topology_count = TopologyData.query.count()
        device_count = NetworkDevice.query.count()
        
        stats = {
            'users': {
                'total': user_count,
                'active': active_users,
                'admin': admin_users
            },
            'chat': {
                'sessions': chat_session_count
            },
            'topology': {
                'data': topology_count,
                'devices': device_count
            }
        }
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 模型配置获取路由已移除


# 模型配置保存路由已移除

def load_current_config(form):
    """加载当前配置到表单"""
    try:
        from config import Config
        from config_manager import get_config
        
        # 创建Config实例
        config = Config()
        
        # OpenAI配置
        form.openai_api_key.data = config.OPENAI_API_KEY
        form.openai_api_base.data = config.OPENAI_API_BASE
        form.openai_model.data = config.OPENAI_MODEL
        form.openai_max_tokens.data = config.OPENAI_MAX_TOKENS
        form.openai_temperature.data = config.OPENAI_TEMPERATURE
        
        # 新增的模型配置项
        form.openai_top_p.data = get_config('openai.top_p', 1.0)
        form.openai_presence_penalty.data = get_config('openai.presence_penalty', 0.0)
        form.openai_frequency_penalty.data = get_config('openai.frequency_penalty', 0.0)
        
        # 数据库配置
        form.database_uri.data = config.SQLALCHEMY_DATABASE_URI
        form.database_pool_size.data = config.DATABASE_POOL_SIZE
        
        # 网络扫描配置
        form.network_scan_timeout.data = config.NETWORK_SCAN_TIMEOUT
        form.network_scan_threads.data = config.NETWORK_SCAN_THREADS
        form.default_scan_range.data = config.DEFAULT_SCAN_RANGE
        
        # Redis配置
        form.redis_url.data = config.REDIS_URL
        form.redis_host.data = config.REDIS_HOST
        form.redis_port.data = config.REDIS_PORT
        form.redis_password.data = config.REDIS_PASSWORD
        
        # 应用配置
        form.app_name.data = config.APP_NAME
        form.app_version.data = config.APP_VERSION
        form.debug_mode.data = config.DEBUG_MODE
        
        # 日志配置
        form.log_level.data = config.LOG_LEVEL
        
    except Exception as e:
        print(f"加载配置时发生错误: {e}")

def save_config(form):
    """
    保存配置到JSON文件
    """
    try:
        from config_manager import set_config, config_manager
        
        # 映射表单字段到配置路径
        field_mapping = {
            'openai_api_key': 'openai.api_key',
            'openai_api_base': 'openai.api_base',
            'openai_model': 'openai.model',
            'openai_temperature': 'openai.temperature',
            'openai_max_tokens': 'openai.max_tokens',
            'openai_top_p': 'openai.top_p',
            'openai_presence_penalty': 'openai.presence_penalty',
            'openai_frequency_penalty': 'openai.frequency_penalty',
            'use_local_model': 'local_model.use_local',
            'local_model_base_url': 'local_model.base_url',
            'local_model_name': 'local_model.model_name',
            'database_uri': 'database.uri',
            'database_pool_size': 'database.pool_size',
            'network_scan_timeout': 'network.scan_timeout',
            'network_scan_threads': 'network.scan_threads',
            'default_scan_range': 'network.default_scan_range',
            'redis_url': 'redis.url',
            'redis_host': 'redis.host',
            'redis_port': 'redis.port',
            'redis_password': 'redis.password',
            'app_name': 'app.name',
            'app_version': 'app.version',
            'debug_mode': 'app.debug_mode',
            'log_level': 'logging.level'
        }
        
        # 保存配置到JSON文件
        for field, config_path in field_mapping.items():
            form_field = getattr(form, field, None)
            if form_field and hasattr(form_field, 'data'):
                value = form_field.data
                
                # 类型转换
                if field in ['openai_temperature', 'openai_top_p', 'openai_presence_penalty', 'openai_frequency_penalty']:
                    value = float(value) if value is not None else None
                    # 设置默认值
                    if field == 'openai_temperature' and value is None:
                        value = 0.7
                    elif field == 'openai_top_p' and value is None:
                        value = 1.0
                    elif field in ['openai_presence_penalty', 'openai_frequency_penalty'] and value is None:
                        value = 0.0
                elif field in ['openai_max_tokens', 'database_pool_size', 'network_scan_timeout', 'network_scan_threads', 'redis_port']:
                    value = int(value) if value else None
                elif field in ['use_local_model', 'debug_mode']:
                    value = bool(value)
                
                if value is not None:
                    set_config(config_path, value)
        
        # 保存配置文件
        config_manager.save_config()
        
        print(f"配置已保存到JSON文件")
        
    except ImportError:
        # 如果没有config_manager，回退到原来的方式
        config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
        
        # 读取当前配置文件
        with open(config_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建备份
        backup_path = f"{config_file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新配置值
        updates = {
            'OPENAI_API_KEY': form.openai_api_key.data or '',
            'OPENAI_API_BASE': form.openai_api_base.data or '',
            'OPENAI_MODEL': form.openai_model.data or 'gpt-4o-mini',
            'OPENAI_MAX_TOKENS': str(form.openai_max_tokens.data or 4096),
            'OPENAI_TEMPERATURE': str(form.openai_temperature.data or 0.7),
            'DATABASE_POOL_SIZE': str(form.database_pool_size.data or 10),
            'NETWORK_SCAN_TIMEOUT': str(form.network_scan_timeout.data or 30),
            'NETWORK_SCAN_THREADS': str(form.network_scan_threads.data or 50),
            'DEFAULT_SCAN_RANGE': form.default_scan_range.data or '192.168.1.0/24',
            'REDIS_URL': form.redis_url.data or 'redis://localhost:6379/0',
            'REDIS_HOST': form.redis_host.data or 'localhost',
            'REDIS_PORT': str(form.redis_port.data or 6379),
            'REDIS_PASSWORD': form.redis_password.data or '',
            'APP_NAME': form.app_name.data or 'AI网络管理系统',
            'APP_VERSION': form.app_version.data or '1.0.0',
            'DEBUG_MODE': 'true' if form.debug_mode.data else 'false',
            'LOG_LEVEL': form.log_level.data or 'INFO'
        }
        
        # 更新配置文件内容
        for key, value in updates.items():
            # 查找并替换配置项
            pattern = rf"({key}\s*=\s*(?:os\.environ\.get\([^)]+\)\s*or\s*)?['\"])([^'\"]*?)(['\"])"
            replacement = rf"\g<1>{value}\g<3>"
            content = re.sub(pattern, replacement, content)
        
        # 更新数据库URI（特殊处理）
        if form.database_uri.data:
            db_pattern = r'(SQLALCHEMY_DATABASE_URI\s*=\s*os\.environ\.get\([^)]+\)\s*or\s*[\'\"]) ([^\'\"]*?)([\'\"])'
            db_replacement = rf"\g<1>{form.database_uri.data}\g<3>"
            content = re.sub(db_pattern, db_replacement, content)
        
        # 写入更新后的配置文件
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新环境变量
        for key, value in updates.items():
            os.environ[key] = value
        
        print(f"配置已保存到 {config_file_path}")
        print(f"备份文件: {backup_path}")