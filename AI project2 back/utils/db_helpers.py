from models import db
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

def safe_create_or_update(model_instance, **kwargs):
    """
    安全地创建或更新数据库记录
    
    Args:
        model_instance: 数据库模型实例
        **kwargs: 要更新的字段
    
    Returns:
        tuple: (success: bool, instance: model_instance or None, error: str or None)
    """
    try:
        # 更新实例属性
        for key, value in kwargs.items():
            if hasattr(model_instance, key):
                setattr(model_instance, key, value)
        
        # 添加到数据库会话
        db.session.add(model_instance)
        db.session.commit()
        
        logger.info(f"成功保存 {model_instance.__class__.__name__} 记录")
        return True, model_instance, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = f"数据库操作失败: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"未知错误: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def safe_delete(model_instance):
    """
    安全地删除数据库记录
    
    Args:
        model_instance: 要删除的数据库模型实例
    
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        db.session.delete(model_instance)
        db.session.commit()
        
        logger.info(f"成功删除 {model_instance.__class__.__name__} 记录")
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = f"删除记录失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"删除记录时发生未知错误: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def safe_query(model_class, **filters):
    """
    安全地查询数据库记录
    
    Args:
        model_class: 数据库模型类
        **filters: 查询过滤条件
    
    Returns:
        tuple: (success: bool, results: list or None, error: str or None)
    """
    try:
        query = db.session.query(model_class)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(model_class, key):
                query = query.filter(getattr(model_class, key) == value)
        
        results = query.all()
        return True, results, None
        
    except SQLAlchemyError as e:
        error_msg = f"查询数据库失败: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
        
    except Exception as e:
        error_msg = f"查询时发生未知错误: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg