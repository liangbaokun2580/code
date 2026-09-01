#!/usr/bin/env python3
"""
数据库工具模块
提供数据库连接管理和错误处理功能
"""

import sqlite3
import time
import logging
from contextlib import contextmanager
from functools import wraps
from sqlalchemy.exc import OperationalError, DatabaseError, IntegrityError
from flask import current_app

logger = logging.getLogger(__name__)


def is_database_corruption_error(error) -> bool:
    """判断是否为SQLite数据库损坏错误。"""
    error_msg = str(error).lower()
    return (
        'database disk image is malformed' in error_msg or
        'malformed' in error_msg or
        'file is not a database' in error_msg
    )


def safe_create_or_update(db, model_class, filter_kwargs, update_kwargs=None, create_kwargs=None):
    """
    安全地创建或更新数据库记录，处理唯一性约束冲突

    Args:
        db: 数据库实例
        model_class: 模型类
        filter_kwargs: 用于查询的过滤条件
        update_kwargs: 更新时使用的字段（可选）
        create_kwargs: 创建时使用的字段（可选，默认使用filter_kwargs）

    Returns:
        tuple: (instance, created) - 实例对象和是否为新创建的标志
    """
    try:
        # 首先尝试查找现有记录
        instance = model_class.query.filter_by(**filter_kwargs).first()

        if instance:
            # 记录存在，更新字段
            if update_kwargs:
                for key, value in update_kwargs.items():
                    setattr(instance, key, value)
            db.session.commit()
            logger.info(f"更新了 {model_class.__name__} 记录: {filter_kwargs}")
            return instance, False
        else:
            # 记录不存在，创建新记录
            create_data = create_kwargs or filter_kwargs
            instance = model_class(**create_data)
            db.session.add(instance)
            db.session.commit()
            logger.info(f"创建了新的 {model_class.__name__} 记录: {filter_kwargs}")
            return instance, True

    except IntegrityError as e:
        db.session.rollback()

        # 处理唯一性约束冲突
        if 'UNIQUE constraint failed' in str(e):
            logger.warning(f"唯一性约束冲突，重新查询 {model_class.__name__}: {e}")

            # 重新查询记录
            instance = model_class.query.filter_by(**filter_kwargs).first()
            if instance:
                # 如果找到了记录，尝试更新
                if update_kwargs:
                    try:
                        for key, value in update_kwargs.items():
                            setattr(instance, key, value)
                        db.session.commit()
                        logger.info(f"在约束冲突后成功更新 {model_class.__name__} 记录")
                    except Exception as update_error:
                        db.session.rollback()
                        logger.error(f"更新记录失败: {update_error}")
                        raise
                return instance, False
            else:
                logger.error(f"约束冲突后仍无法找到记录: {filter_kwargs}")
                raise
        else:
            logger.error(f"数据库完整性错误: {e}")
            raise

    except Exception as e:
        db.session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise


def handle_unique_constraint_error(db, error, retry_func, *args, **kwargs):
    """
    处理唯一性约束错误的通用函数

    Args:
        db: 数据库实例
        error: 捕获的异常
        retry_func: 重试执行的函数
        *args, **kwargs: 传递给重试函数的参数

    Returns:
        重试函数的返回值
    """
    db.session.rollback()

    if 'UNIQUE constraint failed' in str(error):
        logger.warning(f"检测到唯一性约束冲突，尝试重试操作: {error}")
        try:
            return retry_func(*args, **kwargs)
        except Exception as retry_error:
            logger.error(f"重试操作失败: {retry_error}")
            raise
    else:
        logger.error(f"非唯一性约束错误: {error}")
        raise error


def safe_bulk_insert(db, model_class, data_list, conflict_resolution='ignore'):
    """
    安全地批量插入数据，处理冲突

    Args:
        db: 数据库实例
        model_class: 模型类
        data_list: 要插入的数据列表
        conflict_resolution: 冲突解决策略 ('ignore', 'update', 'error')

    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []

    for data in data_list:
        try:
            instance = model_class(**data)
            db.session.add(instance)
            db.session.commit()
            success_count += 1

        except IntegrityError as e:
            db.session.rollback()

            if conflict_resolution == 'ignore':
                logger.debug(f"忽略重复记录: {data}")
                continue
            elif conflict_resolution == 'update':
                # 尝试更新现有记录
                try:
                    # 这里需要根据具体模型的唯一约束来实现更新逻辑
                    logger.warning(f"批量更新功能需要根据具体模型实现: {data}")
                    error_count += 1
                    errors.append(f"更新功能未实现: {e}")
                except Exception as update_error:
                    error_count += 1
                    errors.append(f"更新失败: {update_error}")
            else:  # 'error'
                error_count += 1
                errors.append(f"完整性错误: {e}")

        except Exception as e:
            db.session.rollback()
            error_count += 1
            errors.append(f"插入失败: {e}")

    logger.info(f"批量插入完成: 成功 {success_count}, 失败 {error_count}")
    return success_count, error_count, errors

def retry_db_operation(max_retries=3, delay=1):
    """数据库操作重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DatabaseError, sqlite3.OperationalError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # 检查是否是I/O错误
                    if 'disk i/o error' in error_msg or 'database is locked' in error_msg:
                        logger.warning(f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        
                        if attempt < max_retries - 1:
                            time.sleep(delay * (attempt + 1))  # 递增延迟
                            continue
                    elif is_database_corruption_error(e):
                        logger.error(f"检测到数据库损坏，停止重试: {e}")
                        raise
                    else:
                        # 非I/O错误，直接抛出
                        raise
                except Exception as e:
                    # 其他异常直接抛出
                    raise
            
            # 所有重试都失败了
            logger.error(f"数据库操作最终失败: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator

@contextmanager
def safe_db_session(db):
    """安全的数据库会话上下文管理器"""
    session = db.session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话错误: {e}")
        raise
    finally:
        session.close()

def check_database_health():
    """检查数据库健康状态"""
    try:
        from models import db, User
        
        # 简单查询测试
        result = db.session.execute(db.text('SELECT 1')).fetchone()
        
        if result and result[0] == 1:
            logger.info("数据库连接正常")
            return True
        else:
            logger.error("数据库查询返回异常结果")
            return False
            
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False

def optimize_sqlite_connection():
    """优化SQLite连接设置"""
    try:
        from models import db
        
        # 检查数据库类型，只对SQLite执行PRAGMA优化
        engine_name = db.engine.name.lower()
        if engine_name != 'sqlite':
            logger.info(f"当前数据库类型为 {engine_name}，跳过SQLite特有的优化设置")
            return
        
        # 执行SQLite优化设置
        optimizations = [
            'PRAGMA journal_mode=WAL;',  # 使用WAL模式提高并发性
            'PRAGMA synchronous=NORMAL;',  # 平衡性能和安全性
            'PRAGMA cache_size=10000;',  # 增加缓存大小
            'PRAGMA temp_store=memory;',  # 临时表存储在内存中
            'PRAGMA mmap_size=268435456;',  # 使用内存映射
        ]
        
        for pragma in optimizations:
            try:
                db.session.execute(db.text(pragma))
                logger.debug(f"执行优化: {pragma}")
            except Exception as e:
                logger.warning(f"优化设置失败 {pragma}: {e}")
        
        db.session.commit()
        logger.info("SQLite连接优化完成")
        
    except Exception as e:
        logger.error(f"SQLite优化失败: {e}")

def handle_database_error(error):
    """处理数据库错误"""
    error_msg = str(error).lower()
    
    if 'disk i/o error' in error_msg:
        return {
            'error_type': 'io_error',
            'message': '数据库I/O错误，可能是磁盘空间不足或文件权限问题',
            'suggestions': [
                '检查磁盘空间是否充足',
                '检查数据库文件权限',
                '运行数据库恢复工具',
                '重启应用程序'
            ]
        }
    elif 'database is locked' in error_msg:
        return {
            'error_type': 'lock_error',
            'message': '数据库被锁定，可能有其他进程正在使用',
            'suggestions': [
                '等待其他操作完成',
                '检查是否有其他应用实例在运行',
                '重启应用程序'
            ]
        }
    elif is_database_corruption_error(error):
        return {
            'error_type': 'corruption_error',
            'message': 'SQLite数据库文件已损坏，需要恢复或重建数据库',
            'suggestions': [
                '先备份当前的 .db/.db-wal/.db-shm 文件',
                '使用 sqlite3 的 .recover 恢复到新数据库文件',
                '如果没有可恢复内容，则重新创建数据库',
                '恢复后重启应用程序'
            ]
        }
    elif 'no such table' in error_msg:
        return {
            'error_type': 'schema_error',
            'message': '数据库表不存在，需要初始化数据库',
            'suggestions': [
                '运行数据库迁移',
                '重新创建数据库表',
                '检查数据库初始化脚本'
            ]
        }
    else:
        return {
            'error_type': 'unknown_error',
            'message': f'未知数据库错误: {error}',
            'suggestions': [
                '查看详细错误日志',
                '联系技术支持',
                '尝试重启应用程序'
            ]
        }

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        self.app = app
        
        # 注册数据库健康检查
        with app.app_context():
            try:
                optimize_sqlite_connection()
                if not check_database_health():
                    logger.warning("数据库健康检查失败")
            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
    
    @retry_db_operation(max_retries=3, delay=1)
    def safe_execute(self, operation, *args, **kwargs):
        """安全执行数据库操作"""
        return operation(*args, **kwargs)
    
    def get_database_info(self):
        """获取数据库信息"""
        try:
            from models import db
            
            info = {
                'database_url': self.app.config.get('SQLALCHEMY_DATABASE_URI'),
                'engine_options': self.app.config.get('SQLALCHEMY_ENGINE_OPTIONS'),
                'health_status': check_database_health()
            }
            
            # 获取SQLite特定信息
            if 'sqlite' in info['database_url'] and db.engine.name.lower() == 'sqlite':
                try:
                    result = db.session.execute(db.text('PRAGMA database_list;')).fetchall()
                    info['sqlite_databases'] = [dict(row._mapping) for row in result]
                    
                    result = db.session.execute(db.text('PRAGMA journal_mode;')).fetchone()
                    info['journal_mode'] = result[0] if result else 'unknown'
                    
                except Exception as e:
                    logger.warning(f"获取SQLite信息失败: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'error': str(e)}

# 全局数据库管理器实例
db_manager = DatabaseManager()
