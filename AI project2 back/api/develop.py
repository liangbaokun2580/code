from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import subprocess
import tempfile
import os
import json
import uuid
from datetime import datetime
import threading
import time

from models import db
from services.cloud_sync import CloudSyncService

develop_bp = Blueprint('develop', __name__)
cloud_sync = CloudSyncService()

# 存储运行中的进程
running_processes = {}

@develop_bp.route('/run', methods=['POST'])
@login_required
def run_code():
    """执行Python代码"""
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({'success': False, 'error': '代码不能为空'}), 400
        
        code = data['code']
        language = data.get('language', 'python')
        
        if language != 'python':
            return jsonify({'success': False, 'error': '目前只支持Python代码执行'}), 400
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # 执行代码
            result = subprocess.run(
                ['python', temp_file_path],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超时
                cwd=os.path.dirname(temp_file_path)
            )
            
            # 清理临时文件
            os.unlink(temp_file_path)
            
            execution_result = {
                'success': True,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode,
                'execution_time': datetime.utcnow().isoformat()
            }
            
            # 记录执行历史（可选）
            execution_log = {
                'user_id': current_user.id,
                'code': code,
                'result': execution_result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # 异步保存到云端
            cloud_sync.sync_code_execution(execution_log)
            
            return jsonify(execution_result)
            
        except subprocess.TimeoutExpired:
            os.unlink(temp_file_path)
            return jsonify({
                'success': False,
                'error': '代码执行超时（30秒）',
                'output': '',
                'return_code': -1
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/save', methods=['POST'])
@login_required
def save_code():
    """保存代码"""
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({'success': False, 'error': '代码不能为空'}), 400
        
        code = data['code']
        filename = data.get('filename', f'code_{uuid.uuid4().hex[:8]}.py')
        description = data.get('description', '')
        
        # 确保文件名有正确的扩展名
        if not filename.endswith('.py'):
            filename += '.py'
        
        # 创建用户代码目录
        user_code_dir = os.path.join('user_codes', str(current_user.id))
        os.makedirs(user_code_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(user_code_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 创建代码记录
        code_record = {
            'user_id': current_user.id,
            'filename': filename,
            'file_path': file_path,
            'description': description,
            'code': code,
            'created_at': datetime.utcnow().isoformat(),
            'file_size': len(code.encode('utf-8'))
        }
        
        # 异步同步到云端
        cloud_sync.sync_code_file(code_record)
        
        return jsonify({
            'success': True,
            'message': '代码保存成功',
            'data': {
                'filename': filename,
                'file_path': file_path,
                'file_size': len(code.encode('utf-8'))
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/load', methods=['GET'])
@login_required
def load_code():
    """加载保存的代码文件列表"""
    try:
        user_code_dir = os.path.join('user_codes', str(current_user.id))
        
        if not os.path.exists(user_code_dir):
            return jsonify({
                'success': True,
                'data': {'files': []}
            })
        
        files = []
        for filename in os.listdir(user_code_dir):
            if filename.endswith('.py'):
                file_path = os.path.join(user_code_dir, filename)
                stat = os.stat(file_path)
                
                files.append({
                    'filename': filename,
                    'file_path': file_path,
                    'size': stat.st_size,
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # 按修改时间排序
        files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {'files': files}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/load/<filename>', methods=['GET'])
@login_required
def load_code_file(filename):
    """加载指定的代码文件"""
    try:
        # 安全检查文件名
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'error': '无效的文件名'}), 400
        
        user_code_dir = os.path.join('user_codes', str(current_user.id))
        file_path = os.path.join(user_code_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        stat = os.stat(file_path)
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'code': code,
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/delete/<filename>', methods=['DELETE'])
@login_required
def delete_code_file(filename):
    """删除代码文件"""
    try:
        # 安全检查文件名
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'error': '无效的文件名'}), 400
        
        user_code_dir = os.path.join('user_codes', str(current_user.id))
        file_path = os.path.join(user_code_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        os.remove(file_path)
        
        # 记录删除操作
        delete_record = {
            'user_id': current_user.id,
            'filename': filename,
            'action': 'delete',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 异步同步到云端
        cloud_sync.sync_code_file_operation(delete_record)
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/examples', methods=['GET'])
@login_required
def get_examples():
    """获取示例代码"""
    try:
        examples = [
            {
                'id': 'hello_world',
                'title': 'Hello World',
                'description': '基础的Hello World程序',
                'code': '''# Hello World 示例\nprint("Hello, World!")\nprint("欢迎使用AI开发环境！")
'''
            },
            {
                'id': 'variables',
                'title': '变量和数据类型',
                'description': 'Python基础变量和数据类型示例',
                'code': '''# 变量和数据类型示例\n\n# 字符串\nname = "AI助手"\nprint(f"你好，{name}！")\n\n# 数字\nage = 25\nheight = 1.75\nprint(f"年龄：{age}，身高：{height}米")\n\n# 列表\nfruits = ["苹果", "香蕉", "橙子"]\nprint("水果列表：", fruits)\n\n# 字典\nperson = {\n    "name": "张三",\n    "age": 30,\n    "city": "北京"\n}\nprint("个人信息：", person)
'''
            },
            {
                'id': 'functions',
                'title': '函数定义',
                'description': 'Python函数定义和调用示例',
                'code': '''# 函数定义示例\n\ndef greet(name, age=None):\n    """问候函数"""\n    if age:\n        return f"你好，{name}！你今年{age}岁。"\n    else:\n        return f"你好，{name}！"\n\ndef calculate_area(length, width):\n    """计算矩形面积"""\n    return length * width\n\n# 函数调用\nprint(greet("小明"))\nprint(greet("小红", 20))\n\narea = calculate_area(5, 3)\nprint(f"矩形面积：{area}")
'''
            },
            {
                'id': 'loops',
                'title': '循环结构',
                'description': 'for循环和while循环示例',
                'code': '''# 循环结构示例\n\n# for循环\nprint("=== for循环 ===")\nfor i in range(5):\n    print(f"第{i+1}次循环")\n\n# 遍历列表\ncolors = ["红色", "绿色", "蓝色"]\nfor color in colors:\n    print(f"我喜欢{color}")\n\n# while循环\nprint("\n=== while循环 ===")\ncount = 0\nwhile count < 3:\n    print(f"计数：{count}")\n    count += 1\n\n# 列表推导式\nsquares = [x**2 for x in range(1, 6)]\nprint(f"\n平方数列表：{squares}")
'''
            },
            {
                'id': 'file_operations',
                'title': '文件操作',
                'description': '文件读写操作示例',
                'code': '''# 文件操作示例\nimport os\nimport tempfile\n\n# 创建临时文件\nwith tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:\n    temp_file.write("这是一个测试文件\\n")\n    temp_file.write("包含多行内容\\n")\n    temp_file.write("用于演示文件操作\\n")\n    temp_filename = temp_file.name\n\nprint(f"创建临时文件：{temp_filename}")\n\n# 读取文件\nwith open(temp_filename, 'r', encoding='utf-8') as file:\n    content = file.read()\n    print("文件内容：")\n    print(content)\n\n# 按行读取\nwith open(temp_filename, 'r', encoding='utf-8') as file:\n    lines = file.readlines()\n    print(f"文件共有{len(lines)}行")\n\n# 清理临时文件\nos.unlink(temp_filename)\nprint("临时文件已删除")
'''
            },
            {
                'id': 'network_scan',
                'title': '网络扫描',
                'description': '简单的网络扫描示例',
                'code': '''# 网络扫描示例\nimport socket\nimport threading\nfrom datetime import datetime\n\ndef scan_port(host, port, timeout=1):\n    """扫描单个端口"""\n    try:\n        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n        sock.settimeout(timeout)\n        result = sock.connect_ex((host, port))\n        sock.close()\n        return result == 0\n    except:\n        return False\n\ndef scan_host(host, ports):\n    """扫描主机的多个端口"""\n    print(f"正在扫描主机：{host}")\n    open_ports = []\n    \n    for port in ports:\n        if scan_port(host, port):\n            open_ports.append(port)\n            print(f"  端口 {port}: 开放")\n    \n    return open_ports\n\n# 扫描本地主机的常见端口\nhost = "127.0.0.1"\ncommon_ports = [22, 23, 53, 80, 110, 443, 993, 995]\n\nprint(f"开始扫描 {host} - {datetime.now()}")\nopen_ports = scan_host(host, common_ports)\n\nif open_ports:\n    print(f"\\n发现开放端口：{open_ports}")\nelse:\n    print("\\n未发现开放端口")\n\nprint(f"扫描完成 - {datetime.now()}")
'''
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {'examples': examples}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/format', methods=['POST'])
@login_required
def format_code():
    """格式化Python代码"""
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({'success': False, 'error': '代码不能为空'}), 400
        
        code = data['code']
        
        try:
            # 使用autopep8格式化代码（如果可用）
            import autopep8
            formatted_code = autopep8.fix_code(code)
        except ImportError:
            # 如果autopep8不可用，进行基础格式化
            lines = code.split('\n')
            formatted_lines = []
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    formatted_lines.append('')
                    continue
                
                # 减少缩进
                if stripped.startswith(('except', 'elif', 'else', 'finally')):
                    indent_level = max(0, indent_level - 1)
                elif stripped.startswith(('def ', 'class ')) and indent_level > 0:
                    indent_level = 0
                
                # 添加缩进
                formatted_line = '    ' * indent_level + stripped
                formatted_lines.append(formatted_line)
                
                # 增加缩进
                if stripped.endswith(':'):
                    indent_level += 1
            
            formatted_code = '\n'.join(formatted_lines)
        
        return jsonify({
            'success': True,
            'data': {'formatted_code': formatted_code}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@develop_bp.route('/docs', methods=['GET'])
@login_required
def get_api_docs():
    """获取API文档"""
    try:
        docs = {
            'title': 'AI开发环境 API文档',
            'version': '1.0.0',
            'description': '提供代码执行、保存、加载等功能的API接口',
            'endpoints': [
                {
                    'path': '/api/develop/run',
                    'method': 'POST',
                    'description': '执行Python代码',
                    'parameters': {
                        'code': '要执行的Python代码（必需）',
                        'language': '编程语言，目前只支持python（可选）'
                    },
                    'example': {
                        'request': {
                            'code': 'print("Hello, World!")',
                            'language': 'python'
                        },
                        'response': {
                            'success': True,
                            'output': 'Hello, World!\n',
                            'error': '',
                            'return_code': 0
                        }
                    }
                },
                {
                    'path': '/api/develop/save',
                    'method': 'POST',
                    'description': '保存代码到文件',
                    'parameters': {
                        'code': '要保存的代码（必需）',
                        'filename': '文件名（可选）',
                        'description': '文件描述（可选）'
                    }
                },
                {
                    'path': '/api/develop/load',
                    'method': 'GET',
                    'description': '获取保存的代码文件列表'
                },
                {
                    'path': '/api/develop/load/<filename>',
                    'method': 'GET',
                    'description': '加载指定的代码文件'
                },
                {
                    'path': '/api/develop/examples',
                    'method': 'GET',
                    'description': '获取示例代码'
                },
                {
                    'path': '/api/develop/format',
                    'method': 'POST',
                    'description': '格式化Python代码',
                    'parameters': {
                        'code': '要格式化的代码（必需）'
                    }
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'data': docs
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500