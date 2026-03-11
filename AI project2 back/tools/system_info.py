# 工具名称
TOOL_NAME = "系统信息"

# 工具描述
TOOL_DESCRIPTION = "获取系统基本信息，包括操作系统、CPU、内存和磁盘使用情况"

# 工具作者
TOOL_AUTHOR = "AI系统管理工具"

# 工具版本
TOOL_VERSION = "1.0"

# 工具分类
TOOL_CATEGORY = "system"

# 工具参数定义
TOOL_PARAMETERS = [
    {
        "name": "include_cpu",
        "type": "boolean",
        "label": "包含CPU信息",
        "description": "是否包含CPU详细信息",
        "required": False,
        "default": True
    },
    {
        "name": "include_memory",
        "type": "boolean",
        "label": "包含内存信息",
        "description": "是否包含内存使用情况",
        "required": False,
        "default": True
    },
    {
        "name": "include_disk",
        "type": "boolean",
        "label": "包含磁盘信息",
        "description": "是否包含磁盘使用情况",
        "required": False,
        "default": True
    },
    {
        "name": "include_network",
        "type": "boolean",
        "label": "包含网络信息",
        "description": "是否包含网络接口信息",
        "required": False,
        "default": False
    }
]

import platform
import psutil
import socket
import datetime
import os

def get_size(bytes, suffix="B"):
    """将字节转换为人类可读的格式"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def run(params):
    """获取系统信息"""
    # 获取参数
    include_cpu = params.get("include_cpu", True)
    include_memory = params.get("include_memory", True)
    include_disk = params.get("include_disk", True)
    include_network = params.get("include_network", False)
    
    result = {
        "success": True,
        "message": "成功获取系统信息",
        "data": {}
    }
    
    # 基本系统信息
    system_info = {
        "system": platform.system(),
        "node_name": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    }
    result["data"]["system"] = system_info
    
    # CPU信息
    if include_cpu:
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "max_frequency": f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else "Unknown",
            "current_frequency": f"{psutil.cpu_freq().current:.2f}Mhz" if psutil.cpu_freq() else "Unknown",
            "cpu_usage_per_core": [f"{percentage:.2f}%" for percentage in psutil.cpu_percent(percpu=True, interval=1)],
            "total_cpu_usage": f"{psutil.cpu_percent()}%"
        }
        result["data"]["cpu"] = cpu_info
    
    # 内存信息
    if include_memory:
        svmem = psutil.virtual_memory()
        memory_info = {
            "total": get_size(svmem.total),
            "available": get_size(svmem.available),
            "used": get_size(svmem.used),
            "percentage": f"{svmem.percent}%"
        }
        
        # 交换内存信息
        swap = psutil.swap_memory()
        swap_info = {
            "total": get_size(swap.total),
            "free": get_size(swap.free),
            "used": get_size(swap.used),
            "percentage": f"{swap.percent}%"
        }
        
        result["data"]["memory"] = memory_info
        result["data"]["swap"] = swap_info
    
    # 磁盘信息
    if include_disk:
        disk_info = []
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "file_system_type": partition.fstype,
                    "total_size": get_size(partition_usage.total),
                    "used": get_size(partition_usage.used),
                    "free": get_size(partition_usage.free),
                    "percentage": f"{partition_usage.percent}%"
                })
            except Exception:
                # 某些磁盘可能无法访问
                pass
        
        # 磁盘IO统计
        try:
            disk_io = psutil.disk_io_counters()
            disk_io_info = {
                "read_since_boot": get_size(disk_io.read_bytes),
                "written_since_boot": get_size(disk_io.write_bytes)
            }
            result["data"]["disk_io"] = disk_io_info
        except:
            pass
            
        result["data"]["disks"] = disk_info
    
    # 网络信息
    if include_network:
        network_info = []
        if_addrs = psutil.net_if_addrs()
        for interface_name, interface_addresses in if_addrs.items():
            for address in interface_addresses:
                if str(address.family) == 'AddressFamily.AF_INET':
                    network_info.append({
                        "interface": interface_name,
                        "ip": address.address,
                        "netmask": address.netmask,
                        "broadcast": address.broadcast
                    })
        
        # 网络IO统计
        try:
            net_io = psutil.net_io_counters()
            net_io_info = {
                "bytes_sent": get_size(net_io.bytes_sent),
                "bytes_received": get_size(net_io.bytes_recv)
            }
            result["data"]["net_io"] = net_io_info
        except:
            pass
            
        result["data"]["network_interfaces"] = network_info
    
    return result