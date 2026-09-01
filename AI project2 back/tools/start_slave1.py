# 工具名称
TOOL_NAME = "开启slave1"

# 工具描述
TOOL_DESCRIPTION = "输入“开启slave1”后，通过SSH连接192.168.1.7并执行 virsh start s1"

# 工具作者
TOOL_AUTHOR = "AI系统管理工具"

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "system"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "input",
        "type": "string",
        "label": "输入命令",
        "description": "请输入：开启slave1",
        "required": True,
        "default": ""
    }
]

import socket
import subprocess

import paramiko


EXPECTED_INPUT = "开启slave1"
SSH_HOST = "192.168.1.7"
SSH_PORT = 22
SSH_USERNAME = "root"
SSH_PASSWORD = "Key-1122"
REMOTE_COMMAND = ["virsh", "start", "s1"]


def _tcp_reachable(host: str, port: int, timeout: float = 3) -> str:
    """快速检测目标端口是否可达，返回错误描述（空字符串表示可达）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return ""
    except Exception as exc:
        return str(exc)
    finally:
        sock.close()


def _ping_result(host: str) -> str:
    """获取 ping 结果作为诊断信息。"""
    try:
        proc = subprocess.run(
            ["ping", "-n", "1", host],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def run(params):
    """通过SSH启动远程虚拟机s1。"""
    user_input = str(params.get("input", "")).strip()

    if user_input != EXPECTED_INPUT:
        return {
            "success": False,
            "message": "输入不匹配，请输入：开启slave1",
            "data": {
                "expected_input": EXPECTED_INPUT
            }
        }

    command = " ".join(REMOTE_COMMAND)

    # 先检测 TCP 连通性，给出明确诊断
    conn_error = _tcp_reachable(SSH_HOST, SSH_PORT)
    if conn_error:
        return {
            "success": False,
            "message": f"无法连接 {SSH_HOST}:{SSH_PORT}（{conn_error}），请检查网络可达性",
            "data": {
                "host": SSH_HOST,
                "port": SSH_PORT,
                "username": SSH_USERNAME,
                "command": command,
                "error": conn_error,
                "ping": _ping_result(SSH_HOST),
            }
        }

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USERNAME,
            password=SSH_PASSWORD,
            timeout=10,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()

        return {
            "success": exit_code == 0,
            "message": "slave1启动命令已执行" if exit_code == 0 else "slave1启动命令执行失败",
            "data": {
                "host": SSH_HOST,
                "username": SSH_USERNAME,
                "command": command,
                "return_code": exit_code,
                "stdout": out,
                "stderr": err,
            }
        }
    except paramiko.AuthenticationException:
        return {
            "success": False,
            "message": "SSH认证失败，请检查用户名或密码",
            "data": {
                "host": SSH_HOST,
                "username": SSH_USERNAME,
                "command": command,
            }
        }
    except paramiko.SSHException as exc:
        return {
            "success": False,
            "message": f"SSH连接失败: {exc}",
            "data": {
                "host": SSH_HOST,
                "username": SSH_USERNAME,
                "command": command,
                "error": str(exc),
            }
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"执行SSH命令时出错: {str(exc)}",
            "data": {
                "host": SSH_HOST,
                "username": SSH_USERNAME,
                "command": command,
                "error": str(exc),
            }
        }
    finally:
        client.close()
