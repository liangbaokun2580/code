#!/usr/bin/env python3
"""
数据库恢复和维护脚本
用于修复SQLite数据库的I/O错误和其他问题
"""

import os
import sqlite3
import shutil
from datetime import datetime
from flask import Flask
from config import Config
from models import db

def backup_database(db_path):
    """备份数据库"""
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"数据库备份成功: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"备份失败: {e}")
        return None

def check_database_integrity(db_path):
    """检查数据库完整性（仅适用于SQLite）"""
    if not db_path.endswith('.db') and 'sqlite' not in db_path.lower():
        print("此函数仅适用于SQLite数据库")
        return False
        
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # 检查完整性
        cursor.execute('PRAGMA integrity_check;')
        result = cursor.fetchone()
        
        if result[0] == 'ok':
            print("数据库完整性检查: 通过")
            integrity_ok = True
        else:
            print(f"数据库完整性检查: 失败 - {result[0]}")
            integrity_ok = False
        
        # 检查WAL模式
        cursor.execute('PRAGMA journal_mode;')
        journal_mode = cursor.fetchone()[0]
        print(f"当前日志模式: {journal_mode}")
        
        # 获取数据库信息
        cursor.execute('PRAGMA database_list;')
        db_info = cursor.fetchall()
        print(f"数据库信息: {db_info}")
        
        conn.close()
        return integrity_ok
        
    except Exception as e:
        print(f"数据库检查失败: {e}")
        return False

def repair_database(db_path):
    """修复数据库（仅适用于SQLite）"""
    if not db_path.endswith('.db') and 'sqlite' not in db_path.lower():
        print("此函数仅适用于SQLite数据库")
        return False
        
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        print("开始数据库修复...")
        
        # 设置为DELETE模式（更稳定）
        cursor.execute('PRAGMA journal_mode=DELETE;')
        print("设置日志模式为DELETE")
        
        # 重建数据库
        cursor.execute('VACUUM;')
        print("执行VACUUM操作")
        
        # 分析数据库
        cursor.execute('ANALYZE;')
        print("执行ANALYZE操作")
        
        # 重新检查完整性
        cursor.execute('PRAGMA integrity_check;')
        result = cursor.fetchone()
        
        conn.close()
        
        if result[0] == 'ok':
            print("数据库修复成功")
            return True
        else:
            print(f"数据库修复失败: {result[0]}")
            return False
            
    except Exception as e:
        print(f"数据库修复过程中出错: {e}")
        return False

def recreate_database():
    """重新创建数据库"""
    try:
        app = Flask(__name__)
        app.config.from_object(Config())
        
        with app.app_context():
            db.init_app(app)
            
            # 删除所有表
            db.drop_all()
            print("删除所有数据库表")
            
            # 重新创建所有表
            db.create_all()
            print("重新创建所有数据库表")
            
            return True
            
    except Exception as e:
        print(f"重新创建数据库失败: {e}")
        return False

def main():
    """主函数"""
    db_path = os.path.join('instance', 'ai_network_system.db')
    
    print("=== 数据库恢复工具 ===")
    print(f"数据库路径: {db_path}")
    
    # 1. 备份数据库
    backup_path = backup_database(db_path)
    if not backup_path:
        print("无法备份数据库，退出")
        return
    
    # 2. 检查数据库完整性
    if check_database_integrity(db_path):
        print("数据库完整性良好，尝试修复配置问题")
        if repair_database(db_path):
            print("修复完成")
        else:
            print("修复失败，建议重新创建数据库")
    else:
        print("数据库损坏，需要重新创建")
        
        # 询问是否重新创建
        response = input("是否重新创建数据库？这将丢失所有数据 (y/N): ")
        if response.lower() == 'y':
            if recreate_database():
                print("数据库重新创建成功")
            else:
                print("数据库重新创建失败")
        else:
            print("取消操作")
    
    print("\n=== 建议 ===")
    print("1. 定期备份数据库")
    print("2. 确保有足够的磁盘空间")
    print("3. 避免在数据库操作期间强制关闭应用")
    print("4. 考虑使用PostgreSQL或MySQL作为生产数据库")

if __name__ == '__main__':
    main()