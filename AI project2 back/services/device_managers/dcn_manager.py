# -*- coding: utf-8 -*-
"""
神州数码(DCN)设备管理器
支持神州数码路由器、交换机等设备的配置管理
"""

import re
from typing import Dict, List, Any, Optional
from .base_manager import BaseDeviceManager

class DCNDeviceManager(BaseDeviceManager):
    """神州数码设备管理器"""
    
    def __init__(self):
        super().__init__()
        self.vendor = 'dcn'
        self.enable_command = 'enable'
        self.config_command = 'config terminal'
        self.exit_command = 'exit'
        self.end_command = 'end'
        
    def get_config(self, device_ip: str, config_type: str) -> Dict[str, Any]:
        """获取神州数码设备配置（使用交互式shell）"""
        if not self.validate_ip(device_ip):
            return {'success': False, 'error': '无效的IP地址'}
        
        credentials = self.get_credentials(device_ip)
        ssh_client = self.connect_ssh(
            device_ip, 
            credentials['username'], 
            credentials['password']
        )
        
        if not ssh_client:
            return {'success': False, 'error': 'SSH连接失败'}

        try:
            results = []
            
            # 进入特权模式
            enable_result = self.execute_command(ssh_client, self.enable_command)
            if not enable_result['success']:
                ssh_client.close()
                return {'success': False, 'error': '无法进入特权模式'}
            
            commands = self._get_config_commands(config_type)
            
            # 使用交互式方式执行命令
            for command in commands:
                result = self.execute_command(ssh_client, command)
                if result['success']:
                    results.append({
                        'command': command,
                        'output': result['output']
                    })
                else:
                    results.append({
                        'command': command,
                        'error': result['error']
                    })

            ssh_client.close()
            
            return {
                'success': True,
                'device_ip': device_ip,
                'config_type': config_type,
                'results': results
            }
            
        except Exception as e:
            ssh_client.close()
            return {'success': False, 'error': str(e)}
    
    def modify_config(self, device_ip: str, config_type: str, commands: List[str], save_config: bool = True) -> Dict[str, Any]:
        """修改神州数码设备配置（使用交互式shell）"""
        if not self.validate_ip(device_ip):
            return {'success': False, 'error': '无效的IP地址'}
        
        credentials = self.get_credentials(device_ip)
        ssh_client = self.connect_ssh(
            device_ip, 
            credentials['username'], 
            credentials['password']
        )
        
        if not ssh_client:
            return {'success': False, 'error': 'SSH连接失败'}
        
        shell = self.create_interactive_shell(ssh_client)
        if not shell:
            ssh_client.close()
            return {'success': False, 'error': '创建交互式shell失败'}
        
        try:
            results = []
            
            # 进入特权模式
            enable_result = self.execute_interactive_command(shell, self.enable_command, wait_time=2.0)
            if not enable_result['success']:
                shell.close()
                ssh_client.close()
                return {'success': False, 'error': '无法进入特权模式'}
            
            # 进入配置模式
            config_result = self.execute_interactive_command(shell, self.config_command, wait_time=2.0)
            if not config_result['success']:
                shell.close()
                ssh_client.close()
                return {'success': False, 'error': '无法进入配置模式'}
            
            # 执行配置命令
            for command in commands:
                result = self.execute_interactive_command(shell, command, wait_time=2.0)
                results.append({
                    'command': command,
                    'success': result['success'],
                    'output': result.get('output', ''),
                    'error': result.get('error', '')
                })
            
            # 退出配置模式
            self.execute_interactive_command(shell, self.end_command, wait_time=1.0)
            
            # 保存配置
            if save_config:
                save_result = self.execute_interactive_command(shell, 'write', wait_time=3.0)
                results.append({
                    'command': 'write',
                    'success': save_result['success'],
                    'output': save_result.get('output', ''),
                    'error': save_result.get('error', '')
                })
            
            shell.close()
            ssh_client.close()
            
            return {
                'success': True,
                'device_ip': device_ip,
                'config_type': config_type,
                'results': results
            }
            
        except Exception as e:
            shell.close()
            ssh_client.close()
            return {'success': False, 'error': str(e)}
    
    def reboot_device(self, device_ip: str, force_reboot: bool = False, delay_seconds: int = 0) -> Dict[str, Any]:
        """重启神州数码设备"""
        if not self.validate_ip(device_ip):
            return {'success': False, 'error': '无效的IP地址'}
        
        credentials = self.get_credentials(device_ip)
        ssh_client = self.connect_ssh(
            device_ip, 
            credentials['username'], 
            credentials['password']
        )
        
        if not ssh_client:
            return {'success': False, 'error': 'SSH连接失败'}
        
        try:
            # 进入特权模式
            enable_result = self.execute_command(ssh_client, self.enable_command)
            if not enable_result['success']:
                ssh_client.close()
                return {'success': False, 'error': '无法进入特权模式'}
            
            # 发送重启命令
            reboot_command = 'reload\ny\n'
            if force_reboot:
                reboot_command += ' force'
            if delay_seconds > 0:
                reboot_command += f' in {delay_seconds}'
            
            result = self.execute_command(ssh_client, reboot_command)
            
            ssh_client.close()
            
            return {
                'success': True,
                'device_ip': device_ip,
                'command': reboot_command,
                'output': result.get('output', ''),
                'message': '重启命令已发送'
            }
            
        except Exception as e:
            ssh_client.close()
            return {'success': False, 'error': str(e)}
    
    def get_device_info(self, device_ip: str) -> Dict[str, Any]:
        """获取神州数码设备基本信息"""
        if not self.validate_ip(device_ip):
            return {'success': False, 'error': '无效的IP地址'}
        
        credentials = self.get_credentials(device_ip)
        ssh_client = self.connect_ssh(
            device_ip, 
            credentials['username'], 
            credentials['password']
        )
        
        if not ssh_client:
            return {'success': False, 'error': 'SSH连接失败'}
        
        try:
            # 进入特权模式
            enable_result = self.execute_command(ssh_client, self.enable_command)
            if not enable_result['success']:
                ssh_client.close()
                return {'success': False, 'error': '无法进入特权模式'}
            
            info_commands = [
                'show version',
                'show ip interface brief',
                'show interface',
                'show cpu usage',
                'show memory usage'
            ]
            
            device_info = {
                'device_ip': device_ip,
                'vendor': self.vendor
            }
            
            for command in info_commands:
                result = self.execute_command(ssh_client, command)
                if result['success']:
                    device_info[command.replace('show ', '').replace(' ', '_')] = result['output']
            
            # 解析版本信息
            if 'version' in device_info:
                version_output = device_info['version']
                device_info.update(self._parse_version_info(version_output))
            
            ssh_client.close()
            
            return {
                'success': True,
                'device_info': device_info
            }
            
        except Exception as e:
            ssh_client.close()
            return {'success': False, 'error': str(e)}
    
    def _get_config_commands(self, config_type: str) -> List[str]:
        """根据配置类型获取对应的查看命令"""
        command_map = {
            'running': ['show running-config'],
            'startup': ['show startup-config'],
            'interface': ['show interface'],
            'routing': ['show ip route'],
            'ospf': ['show ip ospf neighbor', 'show ip ospf database'],
            'bgp': ['show ip bgp summary', 'show ip bgp'],
            'rip': ['show ip rip'],
            'lldp': ['show lldp neighbors']
        }
        
        return command_map.get(config_type, ['show running-config'])
    
    def _parse_version_info(self, version_output: str) -> Dict[str, str]:
        """解析神州数码设备版本信息"""
        info = {}
        
        # 解析设备型号
        model_match = re.search(r'DCN\s+([\w-]+)', version_output, re.IGNORECASE)
        if model_match:
            info['model'] = model_match.group(1)
        
        # 解析软件版本
        version_match = re.search(r'Software Version\s+([\d\.\w\(\)]+)', version_output)
        if version_match:
            info['software_version'] = version_match.group(1)
        
        # 解析序列号
        sn_match = re.search(r'Serial Number\s+([\w]+)', version_output)
        if sn_match:
            info['serial_number'] = sn_match.group(1)
        
        # 解析运行时间
        uptime_match = re.search(r'System uptime\s+(.+)', version_output)
        if uptime_match:
            info['uptime'] = uptime_match.group(1).strip()
        
        # 解析内存信息
        memory_match = re.search(r'Memory\s+(\d+)\s*MB', version_output)
        if memory_match:
            info['memory'] = f"{memory_match.group(1)}MB"
        
        return info
    
    def get_interface_status(self, device_ip: str) -> Dict[str, Any]:
        """获取接口状态"""
        return self.get_config(device_ip, 'interface')
    
    def configure_ospf(self, device_ip: str, process_id: str, network: str, area: str) -> Dict[str, Any]:
        """配置OSPF"""
        commands = [
            f'router ospf {process_id}',
            f'network {network} area {area}',
            'exit'
        ]
        return self.modify_config(device_ip, 'ospf', commands)
    
    def configure_bgp(self, device_ip: str, as_number: str, neighbor_ip: str, neighbor_as: str) -> Dict[str, Any]:
        """配置BGP"""
        commands = [
            f'router bgp {as_number}',
            f'neighbor {neighbor_ip} remote-as {neighbor_as}',
            'exit'
        ]
        return self.modify_config(device_ip, 'bgp', commands)
    
    def configure_rip(self, device_ip: str, version: str = '2', network: str = None) -> Dict[str, Any]:
        """配置RIP"""
        commands = [
            'router rip'
        ]
        if version:
            commands.append(f'version {version}')
        if network:
            commands.append(f'network {network}')
        commands.append('exit')
        return self.modify_config(device_ip, 'rip', commands)
    
    def configure_static_route(self, device_ip: str, destination: str, mask: str, next_hop: str) -> Dict[str, Any]:
        """配置静态路由"""
        commands = [
            f'ip route {destination} {mask} {next_hop}'
        ]
        return self.modify_config(device_ip, 'static_route', commands)
    
    def configure_interface(self, device_ip: str, interface_name: str, ip_address: str, subnet_mask: str) -> Dict[str, Any]:
        """配置接口IP地址"""
        commands = [
            f'interface {interface_name}',
            f'ip address {ip_address} {subnet_mask}',
            'no shutdown',
            'exit'
        ]
        return self.modify_config(device_ip, 'interface', commands)
    
    def configure_vlan(self, device_ip: str, vlan_id: str, vlan_name: str = None) -> Dict[str, Any]:
        """配置VLAN"""
        commands = [
            f'vlan {vlan_id}'
        ]
        if vlan_name:
            commands.append(f'name {vlan_name}')
        commands.append('exit')
        return self.modify_config(device_ip, 'vlan', commands)
    
    def enable_lldp(self, device_ip: str) -> Dict[str, Any]:
        """启用LLDP"""
        commands = ['lldp enable']
        return self.modify_config(device_ip, 'lldp', commands)
    
    def disable_lldp(self, device_ip: str) -> Dict[str, Any]:
        """禁用LLDP"""
        commands = ['no lldp enable']
        return self.modify_config(device_ip, 'lldp', commands)
    
    def configure_trunk_port(self, device_ip: str, interface_name: str, allowed_vlans: str) -> Dict[str, Any]:
        """配置Trunk端口"""
        commands = [
            f'interface {interface_name}',
            'switchport mode trunk',
            f'switchport trunk allowed vlan {allowed_vlans}',
            'exit'
        ]
        return self.modify_config(device_ip, 'interface', commands)
    
    def configure_access_port(self, device_ip: str, interface_name: str, vlan_id: str) -> Dict[str, Any]:
        """配置Access端口"""
        commands = [
            f'interface {interface_name}',
            'switchport mode access',
            f'switchport access vlan {vlan_id}',
            'exit'
        ]
        return self.modify_config(device_ip, 'interface', commands)