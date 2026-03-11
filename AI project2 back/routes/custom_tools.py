from flask import Blueprint, request, jsonify, current_app, g
import os
import json
import importlib.util
import sys
import traceback
import uuid
import datetime
from werkzeug.utils import secure_filename
from models import db, User, CommandSession

# 创建蓝图
custom_tools_bp = Blueprint('custom_tools', __name__)

# 工具目录
TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools')

# 确保工具目录存在
if not os.path.exists(TOOLS_DIR):
    os.makedirs(TOOLS_DIR)


@custom_tools_bp.route('/list', methods=['GET'])
def list_tools():
    """获取所有自定义工具列表"""
    try:
        tools = []
        
        # 遍历工具目录
        for filename in os.listdir(TOOLS_DIR):
            if filename.endswith('.py') and not filename.startswith('__'):
                tool_path = os.path.join(TOOLS_DIR, filename)
                tool_info = get_tool_info(tool_path)
                
                if tool_info:
                    tools.append({
                        'id': os.path.splitext(filename)[0],
                        'name': tool_info.get('name', 'Unnamed Tool'),
                        'description': tool_info.get('description', ''),
                        'category': tool_info.get('category', 'other'),
                        'version': tool_info.get('version', '1.0'),
                        'author': tool_info.get('author', '')
                    })
        
        return jsonify({
            'success': True,
            'tools': tools
        })
    except Exception as e:
        current_app.logger.error(f"Error listing tools: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取工具列表失败: {str(e)}"
        }), 500


@custom_tools_bp.route('/get/<tool_id>', methods=['GET'])
def get_tool(tool_id):
    """获取自定义工具的详细信息和代码"""
    try:
        # 安全检查工具ID
        if not tool_id or '..' in tool_id or '/' in tool_id or '\\' in tool_id:
            return jsonify({
                'success': False,
                'message': "无效的工具ID"
            }), 400
        
        # 构建工具文件路径
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        
        # 检查文件是否存在
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 读取工具文件内容
        with open(tool_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 获取工具信息
        tool_info = get_tool_info(tool_path)
        
        if not tool_info:
            return jsonify({
                'success': False,
                'message': f"无法解析工具 {tool_id} 的信息"
            }), 500
        
        # 构建工具对象
        tool = {
            'id': tool_id,
            'name': tool_info.get('name', 'Unnamed Tool'),
            'description': tool_info.get('description', ''),
            'category': tool_info.get('category', 'other'),
            'version': tool_info.get('version', '1.0'),
            'author': tool_info.get('author', ''),
            'parameters': tool_info.get('parameters', []),
            'code': code
        }
        
        return jsonify({
            'success': True,
            'tool': tool
        })
    except Exception as e:
        current_app.logger.error(f"Error getting tool {tool_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"获取工具失败: {str(e)}"
        }), 500


@custom_tools_bp.route('/create', methods=['POST'])
def create_tool():
    """创建新的自定义工具"""
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': "请求数据无效"
            }), 400
        
        # 获取工具名称和代码
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        category = data.get('category', 'other').strip()
        code = data.get('code', '').strip()
        
        # 验证工具名称
        if not name:
            return jsonify({
                'success': False,
                'message': "工具名称不能为空"
            }), 400
        
        # 生成工具ID（使用安全的文件名）
        tool_id = secure_filename(name.lower().replace(' ', '_'))
        
        # 如果ID已存在，添加随机后缀
        if os.path.exists(os.path.join(TOOLS_DIR, f"{tool_id}.py")):
            tool_id = f"{tool_id}_{uuid.uuid4().hex[:6]}"
        
        # 创建工具文件
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        
        with open(tool_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return jsonify({
            'success': True,
            'message': f"工具 {name} 创建成功",
            'tool_id': tool_id
        })
    except Exception as e:
        current_app.logger.error(f"Error creating tool: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"创建工具失败: {str(e)}"
        }), 500


@custom_tools_bp.route('/update/<tool_id>', methods=['POST'])
def update_tool(tool_id):
    """更新现有的自定义工具"""
    try:
        # 安全检查工具ID
        if not tool_id or '..' in tool_id or '/' in tool_id or '\\' in tool_id:
            return jsonify({
                'success': False,
                'message': "无效的工具ID"
            }), 400
        
        # 构建工具文件路径
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        
        # 检查文件是否存在
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 获取请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': "请求数据无效"
            }), 400
        
        # 获取工具代码
        code = data.get('code', '').strip()
        
        # 更新工具文件
        with open(tool_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return jsonify({
            'success': True,
            'message': f"工具 {tool_id} 更新成功"
        })
    except Exception as e:
        current_app.logger.error(f"Error updating tool {tool_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"更新工具失败: {str(e)}"
        }), 500


@custom_tools_bp.route('/delete/<tool_id>', methods=['DELETE'])
def delete_tool(tool_id):
    """删除自定义工具"""
    try:
        # 安全检查工具ID
        if not tool_id or '..' in tool_id or '/' in tool_id or '\\' in tool_id:
            return jsonify({
                'success': False,
                'message': "无效的工具ID"
            }), 400
        
        # 构建工具文件路径
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        
        # 检查文件是否存在
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
        current_app.logger.error(f"Error deleting tool {tool_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"删除工具失败: {str(e)}"
        }), 500


@custom_tools_bp.route('/run/<tool_id>', methods=['POST'])
def run_tool(tool_id):
    """运行自定义工具"""
    try:
        # 安全检查工具ID
        if not tool_id or '..' in tool_id or '/' in tool_id or '\\' in tool_id:
            return jsonify({
                'success': False,
                'message': "无效的工具ID"
            }), 400
        
        # 构建工具文件路径
        tool_path = os.path.join(TOOLS_DIR, f"{tool_id}.py")
        
        # 检查文件是否存在
        if not os.path.exists(tool_path):
            return jsonify({
                'success': False,
                'message': f"工具 {tool_id} 不存在"
            }), 404
        
        # 获取请求参数
        params = request.get_json() or {}
        
        # 动态导入工具模块
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
        
        # 记录工具执行
        user_id = g.user.id if hasattr(g, 'user') else None
        record_tool_execution(tool_id, params, result, user_id)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        current_app.logger.error(f"Error running tool {tool_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"运行工具失败: {str(e)}"
        }), 500


def get_tool_info(tool_path):
    """从工具文件中提取元数据"""
    try:
        # 动态导入工具模块
        spec = importlib.util.spec_from_file_location("tool_module", tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 提取工具信息
        tool_info = {
            'name': getattr(module, 'TOOL_NAME', os.path.basename(tool_path).split('.')[0]),
            'description': getattr(module, 'TOOL_DESCRIPTION', ''),
            'category': getattr(module, 'TOOL_CATEGORY', 'other'),
            'version': getattr(module, 'TOOL_VERSION', '1.0'),
            'author': getattr(module, 'TOOL_AUTHOR', ''),
            'parameters': getattr(module, 'TOOL_PARAMETERS', [])
        }
        
        return tool_info
    except Exception as e:
        current_app.logger.error(f"Error getting tool info from {tool_path}: {str(e)}")
        return None


def record_tool_execution(tool_id, params, result, user_id=None):
    """记录工具执行历史"""
    try:
        # 这里可以实现记录工具执行历史的逻辑
        # 例如，将执行记录保存到数据库中
        
        # 简单记录到日志
        current_app.logger.info(f"Tool {tool_id} executed by user {user_id} with params: {json.dumps(params)}")
        
        # 如果需要，可以将执行记录保存到数据库
        # 这里是一个示例，实际实现可能需要根据项目需求调整
        '''
        execution_record = ToolExecution(
            tool_id=tool_id,
            user_id=user_id,
            params=json.dumps(params),
            result=json.dumps(result),
            executed_at=datetime.datetime.now()
        )
        db.session.add(execution_record)
        db.session.commit()
        '''
    except Exception as e:
        current_app.logger.error(f"Error recording tool execution: {str(e)}")