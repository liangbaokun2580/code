from datetime import datetime
import re
import uuid

from flask import Blueprint, flash, jsonify, make_response, redirect, render_template, request, session, url_for, current_app
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db


auth_bp = Blueprint('auth', __name__)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('login.html')

    data = request.get_json() if request.is_json else request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    remember_me = _to_bool(data.get('remember_me'))

    if not username or not password:
        error = '用户名和密码不能为空'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return render_template('login.html')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        error = '用户名或密码错误'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 401
        flash(error, 'error')
        return render_template('login.html')

    if not user.is_active:
        error = '账户已被禁用，请联系管理员'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 403
        flash(error, 'error')
        return render_template('login.html')

    # 将登录态持久化到 cookie，避免浏览器或系统重启后丢失会话。
    session.permanent = True
    login_user(user, remember=remember_me)
    user.last_login = datetime.utcnow()
    db.session.commit()

    if request.is_json:
        token = str(uuid.uuid4())
        return jsonify(
            {
                'success': True,
                'message': '登录成功',
                'data': {
                    'token': token,
                    'user': user.to_dict(),
                    'redirect_url': request.args.get('next') or url_for('index'),
                },
            }
        )

    next_page = request.args.get('next')
    return redirect(next_page) if next_page else redirect(url_for('index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('register.html')

    data = request.get_json() if request.is_json else request.form
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''
    remember_me = _to_bool(data.get('remember_me'))

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

    try:
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        session.permanent = True
        login_user(user, remember=remember_me)
        user.last_login = datetime.utcnow()
        db.session.commit()

        if request.is_json:
            token = str(uuid.uuid4())
            return jsonify(
                {
                    'success': True,
                    'message': '注册成功',
                    'data': {
                        'token': token,
                        'user': user.to_dict(),
                        'redirect_url': url_for('index'),
                    },
                }
            )

        flash('注册成功，欢迎使用系统', 'success')
        return redirect(url_for('index'))

    except Exception:
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
    session.clear()

    if request.is_json:
        response = jsonify({'success': True, 'message': '已退出登录'})
    else:
        flash('已退出登录', 'info')
        response = make_response(redirect(url_for('auth.login')))

    response.delete_cookie('remember_token')
    response.delete_cookie(current_app.config.get('SESSION_COOKIE_NAME', 'session'))
    return response


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() if request.is_json else request.form
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not check_password_hash(current_user.password_hash, current_password):
        error = '当前密码错误'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('auth.profile'))

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

    try:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': '密码修改成功'})
        flash('密码修改成功', 'success')
        return redirect(url_for('auth.profile'))

    except Exception:
        db.session.rollback()
        error = '密码修改失败，请稍后重试'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        flash(error, 'error')
        return redirect(url_for('auth.profile'))


@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()

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
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()

    if not email:
        return jsonify({'available': False, 'message': '邮箱不能为空'})

    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return jsonify({'available': False, 'message': '邮箱格式不正确'})

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'available': False, 'message': '邮箱已被注册'})

    return jsonify({'available': True, 'message': '邮箱可用'})
