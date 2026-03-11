from flask import Blueprint, request, jsonify, session, Response, stream_with_context
from flask_login import login_required, current_user
from datetime import datetime
import json
import uuid
import openai
import os

from models import db, ChatSession, ChatMessage
from services.ai_service import AIService
from services.cloud_sync import CloudSyncService

chat_bp = Blueprint('chat', __name__)
ai_service = AIService()
cloud_sync = CloudSyncService()


@chat_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """获取用户的聊天会话列表"""
    try:
        sessions = ChatSession.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(ChatSession.updated_at.desc()).all()

        return jsonify({
            'success': True,
            'data': [session.to_dict() for session in sessions]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions', methods=['POST'])
@login_required
def create_session():
    """创建新的聊天会话"""
    try:
        data = request.get_json()
        title = data.get('title', '新对话')
        mode = data.get('mode', 'chat')

        session_id = str(uuid.uuid4())

        chat_session = ChatSession(
            session_id=session_id,
            user_id=current_user.id,
            title=title,
            mode=mode
        )

        db.session.add(chat_session)
        db.session.commit()

        # 异步同步到云端
        cloud_sync.sync_chat_session(chat_session, 'create')

        return jsonify({
            'success': True,
            'data': chat_session.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """获取指定会话的详细信息"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        return jsonify({
            'success': True,
            'data': chat_session.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    """更新会话信息"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        data = request.get_json()
        if 'title' in data:
            chat_session.title = data['title']
        if 'mode' in data:
            chat_session.mode = data['mode']

        chat_session.updated_at = datetime.utcnow()
        db.session.commit()

        # 异步同步到云端
        cloud_sync.sync_chat_session(chat_session, 'update')

        return jsonify({
            'success': True,
            'data': chat_session.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions', methods=['DELETE'])
@login_required
def delete_all_sessions():
    """删除用户的所有会话"""
    try:
        # 查找用户的所有活跃会话
        sessions = ChatSession.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()

        deleted_count = 0
        for session in sessions:
            # 异步同步到云端（在删除前）
            cloud_sync.sync_chat_session(session, 'delete')
            # 真正删除数据库记录
            db.session.delete(session)
            deleted_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已删除 {deleted_count} 个会话'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """删除会话"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        # 异步同步到云端（在删除前）
        cloud_sync.sync_chat_session(chat_session, 'delete')

        # 真正删除数据库记录（由于设置了cascade='all, delete-orphan'，相关消息也会被删除）
        db.session.delete(chat_session)
        db.session.commit()

        return jsonify({'success': True, 'message': '会话已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    """获取会话的消息历史"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        messages = ChatMessage.query.filter_by(
            session_id=chat_session.id
        ).order_by(ChatMessage.created_at.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'data': {
                'messages': [msg.to_dict() for msg in messages.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': messages.total,
                    'pages': messages.pages
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/messages', methods=['POST'])
@login_required
def send_message(session_id):
    """发送消息并获取AI回复"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        data = request.get_json()
        user_message = data.get('message', '').strip()
        model = data.get('model', '').strip()
        mode = data.get('mode', '').strip()
        stream = bool(data.get('stream', False))

        if not user_message:
            return jsonify({'success': False, 'error': '消息内容不能为空'}), 400

        # 获取消息历史用于上下文
        message_history = ChatMessage.query.filter_by(
            session_id=chat_session.id
        ).order_by(ChatMessage.created_at.asc()).limit(20).all()

        # 构建对话上下文
        context = []
        context.append({
            'role': 'system',
            'content': ai_service.generate_system_prompt(mode)
        })
        for msg in message_history:
            if msg.role == 'assistant' and json.loads(msg.tool_calls):
                context.append({
                    'role': 'assistant',
                    'content': msg.content,
                    'tool_calls': json.loads(msg.tool_calls)
                })
            elif msg.role == 'tool':
                context.append({
                    'role': 'tool',
                    'content': msg.content,
                    'tool_call_id': msg.tool_call_id,
                    'name': json.loads(msg.message_metadata)['tool_name']
                })
            else:
                context.append({
                    'role': msg.role,
                    'content': msg.content
                })

        # 添加当前用户消息
        context.append({
            'role': 'user',
            'content': user_message
        })
        print(context)

        # 如果需要流式输出
        if stream:
            # 先保存用户消息，确保会话存在
            user_msg = ChatMessage(
                session_id=chat_session.id,
                message_id=str(uuid.uuid4()),
                role='user',
                content=user_message,
                message_metadata=json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': current_user.id
                })
            )
            db.session.add(user_msg)
            db.session.commit()

            def generate():
                content_parts = []
                for chunk in ai_service.chat_completion(
                    messages=context,
                    use_tools=True,
                    stream=True,
                    model=model,
                    mode=mode
                ):
                    if not chunk.get('success'):
                        yield json.dumps({
                            'success': False,
                            'error': chunk.get('error', 'stream_error')
                        }, ensure_ascii=False) + '\n'
                        return
                    delta = chunk.get('content', '')
                    if delta:
                        content_parts.append(delta)
                        yield json.dumps({
                            'success': True,
                            'delta': delta
                        }, ensure_ascii=False) + '\n'

                # 保存AI回复
                full_content = ''.join(content_parts)
                final_content = ai_service.ensure_chinese(full_content)
                ai_msg = ChatMessage(
                    session_id=chat_session.id,
                    message_id=str(uuid.uuid4()),
                    role='assistant',
                    content=final_content,
                    message_metadata=json.dumps({}),
                    tool_calls=json.dumps([]),
                    tool_results=json.dumps([]),
                    tool_status=json.dumps({})
                )
                db.session.add(ai_msg)
                chat_session.updated_at = datetime.utcnow()
                db.session.commit()

                # 异步同步到云端
                cloud_sync.sync_chat_message(user_msg, current_user.id, 'create')
                cloud_sync.sync_chat_message(ai_msg, current_user.id, 'create')

                if final_content != full_content:
                    yield json.dumps({'success': True, 'final': final_content}, ensure_ascii=False) + '\n'

                yield json.dumps({'success': True, 'done': True}, ensure_ascii=False) + '\n'

            return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

        # 非流式：调用AI服务获取回复
        ai_response = ai_service.chat_completion(
            messages=context,
            use_tools=True,
            stream=False,
            model=model,
            mode=mode
        )

        # 检查AI服务调用是否成功
        if not ai_response.get('success'):
            return jsonify({
                'success': False,
                'error': f"AI服务调用失败: {ai_response.get('error', '未知错误')}"
            }), 500

        # 保存用户消息
        user_msg = ChatMessage(
            session_id=chat_session.id,
            message_id=str(uuid.uuid4()),
            role='user',
            content=user_message,
            message_metadata=json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': current_user.id
            })
        )
        db.session.add(user_msg)

        # 保存AI回复
        response_data = ai_response.get('response', {})
        tool_calls = response_data.get('tool_calls', [])

        # 初始化工具状态
        tool_status = {}
        for tool_call in tool_calls:
            tool_name = tool_call.get('name') or (tool_call.get('function', {}).get('name'))
            if tool_name:
                tool_status[tool_name] = 'executing'

        ai_msg = ChatMessage(
            session_id=chat_session.id,
            message_id=str(uuid.uuid4()),
            role='assistant',
            content=response_data.get('content', ''),
            message_metadata=json.dumps(ai_response.get('usage', {})),
            tool_calls=json.dumps(tool_calls),
            tool_results=json.dumps([]),
            tool_status=json.dumps(tool_status)
        )
        db.session.add(ai_msg)

        # 更新会话时间
        chat_session.updated_at = datetime.utcnow()

        db.session.commit()

        # 异步同步到云端
        cloud_sync.sync_chat_message(user_msg, current_user.id, 'create')
        cloud_sync.sync_chat_message(ai_msg, current_user.id, 'create')

        return jsonify({
            'success': True,
            'data': {
                'user_message': user_msg.to_dict(),
                'ai_message': ai_msg.to_dict()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/clear', methods=['POST'])
@login_required
def clear_session(session_id):
    """清空会话消息"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        # 删除所有消息
        ChatMessage.query.filter_by(session_id=chat_session.id).delete()

        # 更新会话时间
        chat_session.updated_at = datetime.utcnow()

        db.session.commit()

        # 异步同步到云端
        cloud_sync.sync_chat_session(chat_session, 'update')

        return jsonify({'success': True, 'message': '会话已清空'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/export/<session_id>', methods=['GET'])
@login_required
def export_session(session_id):
    """导出会话数据"""
    try:
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        messages = ChatMessage.query.filter_by(
            session_id=chat_session.id
        ).order_by(ChatMessage.created_at.asc()).all()

        export_data = {
            'session': chat_session.to_dict(),
            'messages': [msg.to_dict() for msg in messages],
            'export_time': datetime.utcnow().isoformat()
        }

        return jsonify({
            'success': True,
            'data': export_data
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/tools/execute', methods=['POST'])
@login_required
def execute_tool():
    """执行工具调用"""
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        tool_params = data.get('tool_params', {})
        session_id = data.get('session_id')

        if not tool_name:
            return jsonify({'success': False, 'error': '工具名称不能为空'}), 400

        # 验证会话权限
        if session_id:
            chat_session = ChatSession.query.filter_by(
                session_id=session_id,
                user_id=current_user.id
            ).first()

            if not chat_session:
                return jsonify({'success': False, 'error': '会话不存在'}), 404

        # 执行工具
        result = ai_service.execute_tool(
            tool_name=tool_name,
            params=tool_params,
            user_id=current_user.id
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/tools/status', methods=['POST'])
@login_required
def update_tool_status():
    """更新工具执行状态"""
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        status = data.get('status')
        session_id = data.get('session_id')

        if not tool_name or not status:
            return jsonify({'success': False, 'error': '工具名称和状态不能为空'}), 400

        # 查找会话
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        # 查找最近的包含该工具调用的消息
        latest_message = ChatMessage.query.filter_by(
            session_id=chat_session.id
        ).filter(
            ChatMessage.tool_calls.isnot(None)
        ).order_by(ChatMessage.created_at.desc()).first()

        if latest_message:
            # 更新工具状态
            tool_status = json.loads(latest_message.tool_status) if latest_message.tool_status else {}
            tool_status[tool_name] = status
            latest_message.tool_status = json.dumps(tool_status)
            db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/tools/results', methods=['POST'])
@login_required
def process_tool_results():
    """处理工具执行结果"""
    try:
        data = request.get_json()
        tool_results = data.get('tool_results', [])
        mode = data.get('mode', 'chat')
        session_id = data.get('session_id')
        model = data.get('model', None)

        if not tool_results:
            return jsonify({'success': False, 'error': '工具结果不能为空'}), 400

        # 验证会话权限
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()

        if not chat_session:
            return jsonify({'success': False, 'error': '会话不存在'}), 404

        # 调用AI服务处理工具结果
        ai_response = ai_service.process_tool_results(
            tool_results=tool_results,
            user_id=current_user.id,
            session_id=session_id,
            mode=mode,
            model=model
        )

        # 保存工具结果消息到数据库
        for tool_result in tool_results:
            tool_msg = ChatMessage(
                session_id=chat_session.id,
                message_id=str(uuid.uuid4()),
                role='tool',
                content=json.dumps(tool_result.get('result', {}), ensure_ascii=False),
                message_metadata=json.dumps({
                    'tool_name': tool_result.get('tool_name'),
                    'tool_id': tool_result.get('tool_id'),
                    'success': tool_result.get('success', False),
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            # 设置tool_call_id用于OpenAI API
            tool_msg.tool_call_id = tool_result.get('tool_id')
            db.session.add(tool_msg)

        print(ai_response)

        # 保存AI响应到数据库
        if ai_response.get('ai_message'):
            ai_msg_data = ai_response['ai_message']['response']
            ai_msg = ChatMessage(
                session_id=chat_session.id,
                message_id=str(uuid.uuid4()),
                role='assistant',
                content=ai_msg_data.get('content', ''),
                message_metadata=json.dumps(ai_msg_data.get('choice', {})),
                tool_calls=json.dumps(ai_msg_data.get('tool_calls', [])),
                tool_results=json.dumps([]),
                tool_status=json.dumps({})
            )
            db.session.add(ai_msg)

            # 更新会话时间
            chat_session.updated_at = datetime.utcnow()

            db.session.commit()

            # 异步同步到云端
            if ai_response.get('ai_message'):
                cloud_sync.sync_chat_message(ai_msg, current_user.id, 'create')

        return jsonify({
            'success': True,
            'data': ai_response
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@chat_bp.route('/models', methods=['GET'])
def get_models():
    """获取可用的模型列表"""
    try:
        # 调用AI服务获取模型列表
        models_response = ai_service.get_available_models()
        
        if not models_response.get('success'):
            return jsonify({
                'success': False,
                'error': f"获取模型列表失败: {models_response.get('error', '未知错误')}"
            }), 500
            
        return jsonify(models_response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
