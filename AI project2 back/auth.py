from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import uuid

from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # 如果已经登录，重定向到首页
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # POST请求处理登录
    data = request.get_json() if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    # 验证输入
    if not username or not password:
        error = '用户名和密码不能为空'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return render_template('login.html')
    
    # 查找用户
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        if not user.is_active:
            error = '账户已被禁用，请联系管理员'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 403
            flash(error, 'error')
            return render_template('login.html')
        
        # 登录成功
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        if request.is_json:
            # 生成一个简单的token（在生产环境中应使用JWT）
            token = str(uuid.uuid4())
            return jsonify({
                'success': True,
                'message': '登录成功',
                'data': {
                    'token': token,
                    'user': user.to_dict(),
                    'redirect_url': request.args.get('next') or url_for('index')
                }
            })
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))
    else:
        error = '用户名或密码错误'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 401
        flash(error, 'error')
        return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # 如果已经登录，重定向到首页
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('register.html')
    
    # POST请求处理注册
    data = request.get_json() if request.is_json else request.form
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    
    # 验证输入
    errors = []
    
    if not username:
        errors.append('用户名不能为空')
    elif len(username) < 3 or len(username) > 20:
        errors.append('用户名长度必须在3-20个字符之间')
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append('用户名只能包含字母、数字和下划线')
    
    if not email:
        errors.append('邮箱不能为空')
    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append('邮箱格式不正确')
    
    if not password:
        errors.append('密码不能为空')
    elif len(password) < 6:
        errors.append('密码长度至少6个字符')
    
    if password != confirm_password:
        errors.append('两次输入的密码不一致')
    
    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(username=username).first():
        errors.append('用户名已存在')
    
    if User.query.filter_by(email=email).first():
        errors.append('邮箱已被注册')
    
    if errors:
        if request.is_json:
            return jsonify({'success': False, 'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return render_template('register.html')
    
    # 创建新用户
    try:
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        # 自动登录
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        if request.is_json:
            # 生成一个token，与登录接口保持一致
            token = str(uuid.uuid4())
            return jsonify({
                'success': True,
                'message': '注册成功',
                'data': {
                    'token': token,
                    'user': user.to_dict(),
                    'redirect_url': url_for('index')
                }
            })
        
        flash('注册成功，欢迎使用AI网络工程系统！', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        error = '注册失败，请稍后重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        flash(error, 'error')
        return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({'success': True, 'message': '已退出登录'})
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() if request.is_json else request.form
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    # 验证当前密码
    if not check_password_hash(current_user.password_hash, current_password):
        error = '当前密码错误'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('auth.profile'))
    
    # 验证新密码
    if len(new_password) < 6:
        error = '新密码长度至少6个字符'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        error = '两次输入的新密码不一致'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('auth.profile'))
    
    # 更新密码
    try:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': '密码修改成功'})
        flash('密码修改成功', 'success')
        return redirect(url_for('auth.profile'))
        
    except Exception as e:
        db.session.rollback()
        error = '密码修改失败，请稍后重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        flash(error, 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    """检查用户名是否可用"""
    data = request.get_json()
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'available': False, 'message': '用户名不能为空'})
    
    if len(username) < 3 or len(username) > 20:
        return jsonify({'available': False, 'message': '用户名长度必须在3-20个字符之间'})
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'available': False, 'message': '用户名只能包含字母、数字和下划线'})
    
    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({'available': False, 'message': '用户名已存在'})
    
    return jsonify({'available': True, 'message': '用户名可用'})

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """检查邮箱是否可用"""
    data = request.get_json()
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'available': False, 'message': '邮箱不能为空'})
    
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return jsonify({'available': False, 'message': '邮箱格式不正确'})
    
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'available': False, 'message': '邮箱已被注册'})
    
    return jsonify({'available': True, 'message': '邮箱可用'})