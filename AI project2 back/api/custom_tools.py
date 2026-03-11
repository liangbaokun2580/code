from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, User, NetworkDevice, CommandSession, CommandHistory
import json
import uuid
import os
import subprocess
import tempfile
import time
from datetime import datetime
import importlib.util
import sys

custom_tools_bp = Blueprint('custom_tools', __name__)

# 自定义工具目录
TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools')

# 确保工具目录存在
os.makedirs(TOOLS_DIR, exist_ok=True)

@custom_tools_bp.route('/list', methods=['GET'])
@login_required
def list_tools():
    """获取所有自定义工具列表"""
    try:
        tools = []
        # 遍历工具目录中的所有Python文件
        for filename in os.listdir(TOOLS_DIR):
            if filename.endswith('.py') and not filename.startswith('__'):
                tool_path = os.path.join(TOOLS_DIR, filename)
                tool_info = get_tool_info(tool_path)
                if tool_info:
                    tools.append(tool_info)
        
        return jsonify({
            'success': True,
            'tools': tools
        })
    except Exception as e:
        current_app.logger.error(f"获取工具列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取工具列表失败: {str(e)}"
        }), 500

def get_tool_info(tool_path):
    """从工具文件中提取工具信息"""
    try:
        # 获取文件名（不含扩展名）作为工具ID
        tool_id = os.path.basename(tool_path).replace('.py', '')
        
        # 动态加载模块以获取元数据
        spec = importlib.util.spec_from_file_location(tool_id, tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 提取工具元数据
        return {
            'id': tool_id,
            'name': getattr(module, 'TOOL_NAME', tool_id),
            'description': getattr(module, 'TOOL_DESCRIPTION', ''),
            'author': getattr(module, 'TOOL_AUTHOR', ''),
            'version': getattr(module, 'TOOL_VERSION', '1.0'),
            'parameters': getattr(module, 'TOOL_PARAMETERS', []),
            'created_at': datetime.fromtimestamp(os.path.getctime(tool_path)).isoformat(),
            'updated_at': datetime.fromtimestamp(os.path.getmtime(tool_path)).isoformat()
        }
    except Exception as e:
        current_app.logger.error(f"获取工具信息失败 {tool_path}: {str(e)}")
        return None

@custom_tools_bp.route('/run/<tool_id>', methods=['POST'])
@login_required
def run_tool(tool_id):
    """运行指定的自定义工具"""
    try:
        # 检查工具是否存在
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 获取请求参数
        params = request.json or {}
        
        # 动态加载工具模块
        spec = importlib.util.spec_from_file_location(tool_id, tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 检查模块是否有run函数
        if not hasattr(module, 'run'):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 没有定义run函数"
            }), 400
        
        # 运行工具
        result = module.run(params)
        
        # 记录工具执行历史
        record_tool_execution(tool_id, params, result)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        current_app.logger.error(f"运行工具 {tool_id} 失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"运行工具失败: {str(e)}"
        }), 500

def record_tool_execution(tool_id, params, result):
    """记录工具执行历史"""
    # 这里可以实现记录工具执行历史的逻辑
    # 例如保存到数据库或日志文件
    pass

@custom_tools_bp.route('/create', methods=['POST'])
@login_required
def create_tool():
    """创建新的自定义工具"""
    try:
        data = request.json
        if not data or not data.get('name') or not data.get('code'):
            return jsonify({
                'success': False,
                'message': "缺少必要参数"
            }), 400
        
        # 生成工具ID（基于名称的小写和下划线形式）
        tool_id = data['name'].lower().replace(' ', '_')
        # 确保ID唯一
        counter = 1
        original_tool_id = tool_id
        while os.path.exists(os.path.join(TOOLS_DIR, f"{tool_id}.py")):
            tool_id = f"{original_tool_id}_{counter}"
            counter += 1
        
        # 创建工具文件
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        with open(tool_path, 'w', encoding='utf-8') as f:
            f.write(data['code'])
        
        return jsonify({
            'success': True,
            'tool_id': tool_id,
            'message': f"工具 {data['name']} 创建成功"
        })
    except Exception as e:
        current_app.logger.error(f"创建工具失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"创建工具失败: {str(e)}"
        }), 500

@custom_tools_bp.route('/update/<tool_id>', methods=['POST'])
@login_required
def update_tool(tool_id):
    """更新现有的自定义工具"""
    try:
        # 检查工具是否存在
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        data = request.json
        if not data or not data.get('code'):
            return jsonify({
                'success': False,
                'message': "缺少必要参数"
            }), 400
        
        # 更新工具文件
        with open(tool_path, 'w', encoding='utf-8') as f:
            f.write(data['code'])
        
        return jsonify({
            'success': True,
            'message': f"工具 {tool_id} 更新成功"
        })
    except Exception as e:
        current_app.logger.error(f"更新工具失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"更新工具失败: {str(e)}"
        }), 500

@custom_tools_bp.route('/delete/<tool_id>', methods=['DELETE'])
@login_required
def delete_tool(tool_id):
    """删除自定义工具"""
    try:
        # 检查工具是否存在
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 删除工具文件
        os.remove(tool_path)
        
        return jsonify({
            'success': True,
            'message': f"工具 {tool_id} 删除成功"
        })
    except Exception as e:
        current_app.logger.error(f"删除工具失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"删除工具失败: {str(e)}"
        }), 500

@custom_tools_bp.route('/get/<tool_id>', methods=['GET'])
@login_required
def get_tool(tool_id):
    """获取自定义工具的详细信息和代码"""
    try:
        # 检查工具是否存在
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 读取工具代码
        with open(tool_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 获取工具信息
        tool_info = get_tool_info(tool_path)
        if not tool_info:
            return jsonify({
                'success': False,
                'message': f"获取工具信息失败"
            }), 500
        
        # 添加代码到工具信息
        tool_info['code'] = code
        
        return jsonify({
            'success': True,
            'tool': tool_info
        })
    except Exception as e:
        current_app.logger.error(f"获取工具失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取工具失败: {str(e)}"
        }), 500