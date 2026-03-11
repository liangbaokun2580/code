# 工具名称
TOOL_NAME = "文件查找器"

# 工具描述
TOOL_DESCRIPTION = "在指定目录中查找文件，支持按名称、大小、修改时间等条件筛选"

# 工具作者
TOOL_AUTHOR = "AI文件管理工具"

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "system"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "directory",
        "type": "string",
        "label": "搜索目录",
        "description": "要搜索的目录路径",
        "required": True,
        "default": ""
    },
    {
        "name": "filename",
        "type": "string",
        "label": "文件名",
        "description": "要查找的文件名或模式（支持*通配符）",
        "required": False,
        "default": "*"
    },
    {
        "name": "min_size",
        "type": "number",
        "label": "最小大小(KB)",
        "description": "文件最小大小（KB）",
        "required": False,
        "default": 0
    },
    {
        "name": "max_size",
        "type": "number",
        "label": "最大大小(KB)",
        "description": "文件最大大小（KB）",
        "required": False,
        "default": 0
    },
    {
        "name": "days",
        "type": "number",
        "label": "修改天数",
        "description": "最近多少天内修改的文件",
        "required": False,
        "default": 0
    },
    {
        "name": "recursive",
        "type": "boolean",
        "label": "递归搜索",
        "description": "是否递归搜索子目录",
        "required": False,
        "default": True
    },
    {
        "name": "limit",
        "type": "number",
        "label": "结果限制",
        "description": "最多返回的结果数量",
        "required": False,
        "default": 100
    }
]

import os
import glob
import time
from datetime import datetime, timedelta

def get_size_str(size_in_bytes):
    """将字节转换为人类可读的格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def run(params):
    """查找文件"""
    # 获取参数
    directory = params.get("directory", "")
    filename = params.get("filename", "*")
    min_size = float(params.get("min_size", 0)) * 1024  # 转换为字节
    max_size = float(params.get("max_size", 0)) * 1024  # 转换为字节
    days = int(params.get("days", 0))
    recursive = params.get("recursive", True)
    limit = int(params.get("limit", 100))
    
    if not directory:
        return {
            "success": False,
            "message": "搜索目录不能为空"
        }
    
    if not os.path.exists(directory):
        return {
            "success": False,
            "message": f"目录 '{directory}' 不存在"
        }
    
    if not os.path.isdir(directory):
        return {
            "success": False,
            "message": f"'{directory}' 不是一个目录"
        }
    
    # 计算时间阈值
    time_threshold = 0
    if days > 0:
        time_threshold = time.time() - (days * 24 * 60 * 60)
    
    # 构建搜索路径
    search_path = os.path.join(directory, "**", filename) if recursive else os.path.join(directory, filename)
    
    # 查找文件
    found_files = []
    try:
        for file_path in glob.glob(search_path, recursive=recursive):
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                file_size = file_stat.st_size
                file_mtime = file_stat.st_mtime
                
                # 应用过滤条件
                if min_size > 0 and file_size < min_size:
                    continue
                if max_size > 0 and file_size > max_size:
                    continue
                if days > 0 and file_mtime < time_threshold:
                    continue
                
                # 添加到结果列表
                found_files.append({
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "size": file_size,
                    "size_human": get_size_str(file_size),
                    "modified": datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "modified_timestamp": file_mtime
                })
                
                # 检查是否达到限制
                if len(found_files) >= limit:
                    break
    except Exception as e:
        return {
            "success": False,
            "message": f"搜索文件时出错: {str(e)}"
        }
    
    # 按修改时间排序（最新的在前）
    found_files.sort(key=lambda x: x["modified_timestamp"], reverse=True)
    
    # 移除时间戳（仅用于排序）
    for file in found_files:
        del file["modified_timestamp"]
    
    return {
        "success": True,
        "message": f"找到 {len(found_files)} 个文件" + (" (已达到限制)" if len(found_files) >= limit else ""),
        "data": {
            "directory": directory,
            "pattern": filename,
            "recursive": recursive,
            "count": len(found_files),
            "files": found_files
        }
    }