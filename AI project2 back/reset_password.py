#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from models import db, User
from app import create_app
from werkzeug.security import generate_password_hash

def reset_admin_password():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password_hash = generate_password_hash('admin')
            db.session.commit()
            print('admin密码已重置为: admin')
        else:
            print('未找到admin用户')

if __name__ == '__main__':
    reset_admin_password()