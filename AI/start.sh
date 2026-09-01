#!/bin/bash

# AI API 服务启动脚本 (Linux/macOS)
# 自动检测环境并启动服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo "========================================"
    echo "🚀 AI API 服务启动脚本"
    echo "========================================"
    echo
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 环境
check_python() {
    if ! command_exists python3; then
        if ! command_exists python; then
            print_error "未找到 Python，请先安装 Python 3.7+"
            echo "Ubuntu/Debian: sudo apt-get install python3"
            echo "CentOS/RHEL: sudo yum install python3"
            echo "macOS: brew install python3"
            exit 1
        else
            PYTHON_CMD="python"
        fi
    else
        PYTHON_CMD="python3"
    fi
    
    # 检查 Python 版本
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_info "检测到的 Python 版本: $PYTHON_VERSION"
    
    # 检查版本是否满足要求 (3.7+)
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
        print_error "Python 版本过低，需要 Python 3.7+"
        exit 1
    fi
}

# 检查必需文件
check_files() {
    if [ ! -f "requirements.txt" ]; then
        print_error "未找到 requirements.txt 文件"
        exit 1
    fi
    
    if [ ! -f "ai_api_server.py" ]; then
        print_error "未找到 ai_api_server.py 文件"
        exit 1
    fi
    
    if [ ! -f "main.py" ]; then
        print_error "未找到 main.py 文件"
        exit 1
    fi
}

# 检查和设置虚拟环境
check_venv() {
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        print_info "检测到虚拟环境，正在激活..."
        source venv/bin/activate
        print_success "虚拟环境已激活"
        PYTHON_CMD="python"
    else
        print_warning "未检测到虚拟环境，建议创建虚拟环境:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo
        print_info "继续使用系统 Python 环境..."
    fi
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖包..."
    
    if ! $PYTHON_CMD -c "import flask, requests" >/dev/null 2>&1; then
        print_warning "依赖包未完全安装，正在安装..."
        
        # 检查 pip
        if ! command_exists pip && ! command_exists pip3; then
            print_error "未找到 pip，请先安装 pip"
            exit 1
        fi
        
        PIP_CMD="pip"
        if command_exists pip3; then
            PIP_CMD="pip3"
        fi
        
        $PIP_CMD install -r requirements.txt
        
        if [ $? -ne 0 ]; then
            print_error "依赖安装失败，请手动执行: $PIP_CMD install -r requirements.txt"
            exit 1
        fi
        
        print_success "依赖安装完成"
    else
        print_success "依赖包检查通过"
    fi
}

# 检查配置文件
check_config() {
    if [ ! -f "ollama_config.json" ]; then
        print_warning "未找到 ollama_config.json，Ollama 模式可能不可用"
    else
        print_success "配置文件检查通过"
    fi
}

# 显示启动选项
show_options() {
    echo
    print_info "启动选项:"
    echo "[1] 默认启动 (localhost:5000, if_else模式)"
    echo "[2] 自定义端口启动"
    echo "[3] Ollama 模式启动"
    echo "[4] 调试模式启动"
    echo "[5] 外网访问启动 (0.0.0.0)"
    echo "[0] 退出"
    echo
}

# 启动服务
start_service() {
    case $1 in
        1)
            print_info "使用默认配置启动服务..."
            $PYTHON_CMD main.py
            ;;
        2)
            echo -n "请输入端口号 (默认5000): "
            read port
            if [ -z "$port" ]; then
                port=5000
            fi
            print_info "在端口 $port 启动服务..."
            $PYTHON_CMD main.py --port $port
            ;;
        3)
            print_info "使用 Ollama 模式启动服务..."
            $PYTHON_CMD main.py --mode ollama
            ;;
        4)
            print_info "使用调试模式启动服务..."
            $PYTHON_CMD main.py --debug
            ;;
        5)
            print_warning "启动外网访问模式..."
            print_warning "警告: 服务将监听所有网络接口，请确保网络安全"
            $PYTHON_CMD main.py --host 0.0.0.0
            ;;
        0)
            print_info "再见！"
            exit 0
            ;;
        *)
            print_warning "无效选择，使用默认配置启动..."
            $PYTHON_CMD main.py
            ;;
    esac
}

# 主函数
main() {
    print_header
    
    # 检查环境
    check_python
    check_files
    check_venv
    check_dependencies
    check_config
    
    # 如果有命令行参数，直接启动
    if [ $# -gt 0 ]; then
        case $1 in
            --default)
                start_service 1
                ;;
            --ollama)
                start_service 3
                ;;
            --debug)
                start_service 4
                ;;
            --external)
                start_service 5
                ;;
            *)
                print_error "未知参数: $1"
                echo "可用参数: --default, --ollama, --debug, --external"
                exit 1
                ;;
        esac
    else
        # 交互式选择
        show_options
        echo -n "请选择启动方式 (1-5, 0退出): "
        read choice
        start_service $choice
    fi
    
    # 服务结束后的处理
    echo
    print_info "服务已停止"
    print_info "如需重新启动，请重新运行此脚本"
}

# 信号处理
trap 'echo; print_info "收到中断信号，正在停止服务..."; exit 0' INT TERM

# 运行主函数
main "$@"