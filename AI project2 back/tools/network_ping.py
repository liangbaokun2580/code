# 工具名称
TOOL_NAME = "网络Ping测试"

# 工具描述
TOOL_DESCRIPTION = "测试与目标主机的网络连接，发送ICMP请求并显示响应时间"

# 工具作者
TOOL_AUTHOR = "AI网络管理系统"

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "network"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "host",
        "type": "string",
        "label": "目标主机",
        "description": "要测试连接的IP地址或域名",
        "required": True,
        "default": ""
    },
    {
        "name": "count",
        "type": "number",
        "label": "请求次数",
        "description": "发送ICMP请求的次数",
        "required": False,
        "default": 4
    },
    {
        "name": "timeout",
        "type": "number",
        "label": "超时时间(秒)",
        "description": "等待响应的最长时间",
        "required": False,
        "default": 2
    }
]

import subprocess
import platform
import re
import time

def run(params):
    """执行Ping测试"""
    # 获取参数
    host = params.get("host", "")
    count = int(params.get("count", 4))
    timeout = int(params.get("timeout", 2))
    
    if not host:
        return {
            "success": False,
            "message": "目标主机不能为空"
        }
    
    # 根据操作系统构建ping命令
    system = platform.system().lower()
    
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:  # Linux, MacOS
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
    
    try:
        # 执行ping命令
        start_time = time.time()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        end_time = time.time()
        
        # 解析结果
        if process.returncode == 0:
            # 提取统计信息
            stats = {}
            
            if system == "windows":
                # Windows格式解析
                sent_match = re.search(r"已发送 = (\d+)", stdout)
                received_match = re.search(r"已接收 = (\d+)", stdout)
                lost_match = re.search(r"丢失 = (\d+)", stdout)
                time_match = re.search(r"平均 = (\d+)ms", stdout)
                
                if sent_match and received_match and lost_match:
                    stats["sent"] = int(sent_match.group(1))
                    stats["received"] = int(received_match.group(1))
                    stats["lost"] = int(lost_match.group(1))
                    stats["loss_percentage"] = (stats["lost"] / stats["sent"]) * 100 if stats["sent"] > 0 else 0
                
                if time_match:
                    stats["avg_time"] = int(time_match.group(1))
            else:
                # Linux/MacOS格式解析
                stats_match = re.search(r"(\d+) packets transmitted, (\d+) received, (\d+)% packet loss", stdout)
                time_match = re.search(r"min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+", stdout)
                
                if stats_match:
                    stats["sent"] = int(stats_match.group(1))
                    stats["received"] = int(stats_match.group(2))
                    stats["loss_percentage"] = float(stats_match.group(3))
                    stats["lost"] = stats["sent"] - stats["received"]
                
                if time_match:
                    stats["avg_time"] = float(time_match.group(1))
            
            return {
                "success": True,
                "message": f"成功完成对 {host} 的Ping测试",
                "data": {
                    "host": host,
                    "status": "reachable",
                    "raw_output": stdout,
                    "stats": stats,
                    "total_time": round((end_time - start_time) * 1000, 2)  # 毫秒
                }
            }
        else:
            return {
                "success": False,
                "message": f"无法连接到 {host}",
                "data": {
                    "host": host,
                    "status": "unreachable",
                    "raw_output": stdout,
                    "error": stderr
                }
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"执行Ping测试时出错: {str(e)}",
            "data": {
                "host": host,
                "status": "error",
                "error": str(e)
            }
        }