from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import uuid
from functools import wraps

# 导入自定义模块
from auth import auth_bp
from api.chat import chat_bp
from api.topology import topology_bp
from api.develop import develop_bp
from api.network import network_bp
from api.command_line import command_line_bp
from api.custom_tools import custom_tools_bp
from api.webssh import webssh_bp

from api.settings import settings_bp
from models import db, User, ChatSession, TopologyData, NetworkDevice
from config import Config
from utils.database_utils import db_manager, handle_database_error, is_database_corruption_error
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())
    
    # 初始化扩展
    db.init_app(app)
    db_manager.init_app(app)
    
    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    app.socketio = socketio
    
    # 初始化登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(topology_bp, url_prefix='/api/topology')
    app.register_blueprint(develop_bp, url_prefix='/api/develop')
    app.register_blueprint(network_bp, url_prefix='/api/network')
    app.register_blueprint(command_line_bp, url_prefix='/api/command_line')
    app.register_blueprint(custom_tools_bp, url_prefix='/api/custom_tools')
    app.register_blueprint(webssh_bp, url_prefix='/api/webssh')

    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    
    # 全局错误处理
    @app.errorhandler(Exception)
    def handle_exception(e):
        # 检查是否是数据库错误
        if (
            'sqlite3.OperationalError' in str(type(e)) or
            'disk I/O error' in str(e) or
            is_database_corruption_error(e)
        ):
            error_info = handle_database_error(e)
            logging.error(f"数据库错误: {error_info}")
            
            return jsonify({
                'success': False,
                'error': error_info['message'],
                'error_type': error_info['error_type'],
                'suggestions': error_info['suggestions']
            }), 500
        
        # 其他错误的默认处理
        logging.error(f"未处理的异常: {e}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误',
            'details': str(e)
        }), 500
    
    # 主页路由
    @app.route('/')
    def index():
        return render_template('index.html')
        
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')
        
    @app.route('/login')
    def login_redirect():
        return redirect(url_for('auth.login'))
        
    @app.route('/register')
    def register_redirect():
        return redirect(url_for('auth.register'))
    
    @app.route('/chat')
    @login_required
    def chat():
        return render_template('chat.html')
    
    @app.route('/topology')
    @login_required
    def topology():
        return render_template('topology.html')
    
    @app.route('/develop')
    @login_required
    def develop():
        return render_template('develop.html')

    @app.route('/remote_test')
    def remote_test():
        return render_template('remote_test.html')

    @app.route('/command_line')
    @login_required
    def command_line():
        return render_template('command_line.html')
    
    @app.route('/custom_tools')
    @login_required
    def custom_tools():
        return render_template('custom_tools.html')
        
    @app.route('/webssh')
    @login_required
    def webssh():
        return render_template('webssh.html')
    
    # API路由 - 用户信息
    @app.route('/api/user/info')
    @login_required
    def user_info():
        return jsonify({
            'success': True,
            'data': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
                'is_active': current_user.is_active,
                'is_admin': current_user.is_admin
            }
        })
    
    # 错误处理
    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_json:
            return jsonify({'success': False, 'error': '未授权访问'}), 401
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'success': False, 'error': '资源未找到'}), 404
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': '服务器内部错误'}), 500
        return render_template('500.html'), 500
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员用户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('默认管理员用户已创建: admin/admin123')
        elif not admin.is_admin:
            # 如果admin用户存在但不是管理员，则更新为管理员
            admin.is_admin = True
            db.session.commit()
            print('admin用户已更新为管理员')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5002)
