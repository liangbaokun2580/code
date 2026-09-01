#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 服务主启动脚本
提供统一的服务启动入口和命令行参数支持
"""

import argparse
import sys
import os
from ai_api_server import app, mode_manager


def parse_arguments():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description='AI API 服务 - 兼容 OpenAI API 的智能服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                          # 使用默认配置启动
  python main.py --port 8080              # 指定端口启动
  python main.py --mode ollama             # 指定初始模式启动
  python main.py --host 0.0.0.0 --debug   # 调试模式启动
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='服务监听地址 (默认: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='服务监听端口 (默认: 5000)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['if_else', 'ollama'],
        default='if_else',
        help='初始运行模式 (默认: if_else)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='ollama_config.json',
        help='Ollama 配置文件路径 (默认: ollama_config.json)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='AI API 服务 v1.0.0'
    )
    
    return parser.parse_args()


def validate_config(config_path: str) -> bool:
    """验证配置文件
    
    Args:
        config_path (str): 配置文件路径
        
    Returns:
        bool: 配置文件是否有效
    """
    if not os.path.exists(config_path):
        print(f"警告: 配置文件 {config_path} 不存在")
        print("将使用默认配置，Ollama 模式可能不可用")
        return False
    
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ['base_url', 'default_model']
        for key in required_keys:
            if key not in config:
                print(f"错误: 配置文件缺少必需的键: {key}")
                return False
        
        print(f"配置文件 {config_path} 验证通过")
        return True
        
    except json.JSONDecodeError as e:
        print(f"错误: 配置文件格式无效: {e}")
        return False
    except Exception as e:
        print(f"错误: 读取配置文件失败: {e}")
        return False


def print_startup_info(args):
    """打印启动信息
    
    Args:
        args: 命令行参数
    """
    print("=" * 60)
    print("🚀 AI API 服务启动中...")
    print("=" * 60)
    print(f"📡 服务地址: http://{args.host}:{args.port}")
    print(f"🔧 运行模式: {args.mode}")
    print(f"📁 配置文件: {args.config}")
    print(f"🐛 调试模式: {'启用' if args.debug else '禁用'}")
    print("=" * 60)
    print("\n📋 可用的 API 端点:")
    print(f"  • 聊天完成: POST http://{args.host}:{args.port}/v1/chat/completions")
    print(f"  • 模型列表: GET  http://{args.host}:{args.port}/v1/models")
    print(f"  • 工具列表: GET  http://{args.host}:{args.port}/v1/tools")
    print(f"  • 模式管理: GET  http://{args.host}:{args.port}/v1/mode")
    print(f"  • 健康检查: GET  http://{args.host}:{args.port}/health")
    print("\n💡 使用 Ctrl+C 停止服务")
    print("=" * 60)


def setup_mode(initial_mode: str) -> bool:
    """设置初始运行模式
    
    Args:
        initial_mode (str): 初始模式
        
    Returns:
        bool: 设置是否成功
    """
    try:
        if initial_mode == 'ollama':
            # 检查 Ollama 模式是否可用
            if mode_manager.can_switch_to_ollama():
                mode_manager.set_mode('ollama')
                print(f"✅ 成功设置为 {initial_mode} 模式")
            else:
                print("⚠️  Ollama 服务不可用，回退到 if_else 模式")
                mode_manager.set_mode('if_else')
        else:
            mode_manager.set_mode('if_else')
            print(f"✅ 成功设置为 {initial_mode} 模式")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置模式失败: {e}")
        print("使用默认的 if_else 模式")
        mode_manager.set_mode('if_else')
        return False


def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 验证配置文件
        validate_config(args.config)
        
        # 设置初始模式
        setup_mode(args.mode)
        
        # 打印启动信息
        print_startup_info(args)
        
        # 启动服务
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()