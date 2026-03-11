# -*- coding: utf-8 -*-
"""
设备管理器基础类
定义所有设备管理器的统一接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import paramiko
import time
from pysnmp.hlapi import *

class BaseDeviceManager(ABC):
    """设备管理器基础类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ssh_timeout = 30
        self.command_timeout = 10
        
    def connect_ssh(self, device_ip: str, username: str, password: str, port: int = 22) -> Optional[paramiko.SSHClient]:
        """建立SSH连接"""
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=device_ip,
                port=port,
                username=username,
                password=password,
                timeout=self.ssh_timeout
            )
            return ssh_client
        except Exception as e:
            self.logger.error(f"SSH连接失败 {device_ip}: {e}")
            return None
    
    def create_interactive_shell(self, ssh_client: paramiko.SSHClient) -> Optional[paramiko.Channel]:
        """创建交互式shell会话"""
        try:
            shell = ssh_client.invoke_shell()
            shell.settimeout(self.command_timeout)
            # 等待初始提示符
            time.sleep(1)
            # 清空初始输出
            if shell.recv_ready():
                shell.recv(4096)
            return shell
        except Exception as e:
            self.logger.error(f"创建交互式shell失败: {e}")
            return None
    
    def execute_command(self, ssh_client: paramiko.SSHClient, command: str) -> Dict[str, Any]:
        """执行SSH命令（非交互式，保持向后兼容）"""
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=self.command_timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            return {
                'success': True,
                'output': output,
                'error': error,
                'command': command
            }
        except Exception as e:
            self.logger.error(f"命令执行失败 '{command}': {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command
            }
    
    def execute_interactive_command(self, shell: paramiko.Channel, command: str, wait_time: float = 1.0, expect_prompt: str = None) -> Dict[str, Any]:
        """在交互式shell中执行命令"""
        try:
            # 发送命令
            shell.send(command + '\n')
            time.sleep(wait_time)
            
            # 读取输出
            output = ''
            while shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)
            
            # 如果指定了期望的提示符，等待直到出现
            if expect_prompt:
                max_wait = 10  # 最大等待10秒
                wait_count = 0
                while expect_prompt not in output and wait_count < max_wait:
                    time.sleep(1)
                    wait_count += 1
                    if shell.recv_ready():
                        chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                        output += chunk
            
            return {
                'success': True,
                'output': output,
                'command': command
            }
        except Exception as e:
            self.logger.error(f"交互式命令执行失败 '{command}': {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command
            }
    
    def execute_commands_interactive(self, shell: paramiko.Channel, commands: List[str], wait_time: float = 1.0) -> List[Dict[str, Any]]:
        """在交互式shell中执行多个命令"""
        results = []
        for command in commands:
            result = self.execute_interactive_command(shell, command, wait_time)
            results.append(result)
            if not result['success']:
                break
        return results
    
    def snmp_get(self, device_ip: str, oid: str, community: str = 'public') -> Optional[str]:
        """SNMP GET操作"""
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((device_ip, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            ):
                if errorIndication:
                    self.logger.error(f"SNMP错误: {errorIndication}")
                    return None
                elif errorStatus:
                    self.logger.error(f"SNMP错误: {errorStatus.prettyPrint()}")
                    return None
                else:
                    for varBind in varBinds:
                        return str(varBind[1])
        except Exception as e:
            self.logger.error(f"SNMP GET失败 {device_ip}: {e}")
            return None
    
    def snmp_walk(self, device_ip: str, oid: str, community: str = 'public') -> List[str]:
        """SNMP WALK操作"""
        results = []
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((device_ip, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if errorIndication:
                    self.logger.error(f"SNMP错误: {errorIndication}")
                    break
                elif errorStatus:
                    self.logger.error(f"SNMP错误: {errorStatus.prettyPrint()}")
                    break
                else:
                    for varBind in varBinds:
                        results.append(str(varBind[1]))
        except Exception as e:
            self.logger.error(f"SNMP WALK失败 {device_ip}: {e}")
        
        return results
    
    @abstractmethod
    def get_config(self, device_ip: str, config_type: str) -> Dict[str, Any]:
        """获取设备配置"""
        pass
    
    @abstractmethod
    def modify_config(self, device_ip: str, config_type: str, commands: List[str], save_config: bool = True) -> Dict[str, Any]:
        """修改设备配置"""
        pass
    
    @abstractmethod
    def reboot_device(self, device_ip: str, force_reboot: bool = False, delay_seconds: int = 0) -> Dict[str, Any]:
        """重启设备"""
        pass
    
    @abstractmethod
    def get_device_info(self, device_ip: str) -> Dict[str, Any]:
        """获取设备基本信息"""
        pass
    
    def get_credentials(self, device_ip: str) -> Dict[str, str]:
        """获取设备认证信息"""
        # 这里应该从数据库或配置文件中获取设备的认证信息
        # 暂时返回默认值
        return {
            'username': 'test',
            'password': '123456',
            'snmp_community': 'public'
        }
    
    def validate_ip(self, ip_address: str) -> bool:
        """验证IP地址格式"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    def ping_test(self, device_ip: str, count: int = 4) -> Dict[str, Any]:
        """Ping测试"""
        import subprocess
        import platform
        
        try:
            # 根据操作系统选择ping命令
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', str(count), device_ip]
            else:
                cmd = ['ping', '-c', str(count), device_ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'reachable': result.returncode == 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'reachable': False
            }