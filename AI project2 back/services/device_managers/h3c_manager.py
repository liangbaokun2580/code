# -*- coding: utf-8 -*-
"""
新华三(H3C)设备管理器
支持H3C路由器、交换机等设备的配置管理
"""

import re
from typing import Dict, List, Any, Optional
from .base_manager import BaseDeviceManager

class H3CDeviceManager(BaseDeviceManager):
    """新华三设备管理器"""
    
    def __init__(self):
        super().__init__()
        self.vendor = 'h3c'
        self.config_command = 'system-view'
        self.exit_command = 'quit'
        self.end_command = 'end'
        
    def get_config(self, device_ip: str, config_type: str) -> Dict[str, Any]:
        """获取H3C设备配置（使用交互式shell）"""
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
            commands = self._get_config_commands(config_type)
            results = []
            
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
        """修改H3C设备配置（使用交互式shell）"""
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
            
            # 进入系统视图
            config_result = self.execute_interactive_command(shell, self.config_command, wait_time=2.0)
            if not config_result['success']:
                shell.close()
                ssh_client.close()
                return {'success': False, 'error': '无法进入系统视图'}
            
            # 执行配置命令
            for command in commands:
                result = self.execute_interactive_command(shell, command, wait_time=2.0)
                results.append({
                    'command': command,
                    'success': result['success'],
                    'output': result.get('output', ''),
                    'error': result.get('error', '')
                })
            
            # 退出系统视图
            self.execute_interactive_command(shell, self.end_command, wait_time=1.0)
            
            # 保存配置
            if save_config:
                save_result = self.execute_interactive_command(shell, 'save', wait_time=3.0)
                results.append({
                    'command': 'save',
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
        """重启H3C设备"""
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
            if delay_seconds > 0:
                command = f'reboot at {delay_seconds}'
            else:
                command = 'reboot'
            
            result = self.execute_command(ssh_client, command)
            
            ssh_client.close()
            
            return {
                'success': True,
                'device_ip': device_ip,
                'command': command,
                'output': result.get('output', ''),
                'message': '重启命令已发送'
            }
            
        except Exception as e:
            ssh_client.close()
            return {'success': False, 'error': str(e)}
    
    def get_device_info(self, device_ip: str) -> Dict[str, Any]:
        """获取H3C设备基本信息"""
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
            info_commands = [
                'display version',
                'display device',
                'display interface brief',
                'display cpu-usage',
                'display memory'
            ]
            
            device_info = {
                'device_ip': device_ip,
                'vendor': self.vendor
            }
            
            for command in info_commands:
                result = self.execute_command(ssh_client, command)
                if result['success']:
                    device_info[command.replace('display ', '').replace('-', '_')] = result['output']
            
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
            'running': ['display current-configuration'],
            'startup': ['display saved-configuration'],
            'interface': ['display interface brief'],
            'routing': ['display ip routing-table'],
            'ospf': ['display ospf peer', 'display ospf lsdb'],
            'bgp': ['display bgp peer', 'display bgp routing-table'],
            'rip': ['display rip database'],
            'lldp': ['display lldp neighbor-information']
        }
        
        return command_map.get(config_type, ['display current-configuration'])
    
    def _parse_version_info(self, version_output: str) -> Dict[str, str]:
        """解析H3C设备版本信息"""
        info = {}
        
        # 解析设备型号
        model_match = re.search(r'H3C\s+([\w-]+)', version_output, re.IGNORECASE)
        if model_match:
            info['model'] = model_match.group(1)
        
        # 解析软件版本
        version_match = re.search(r'Software Version\s+([\d\.\w\(\)]+)', version_output)
        if version_match:
            info['software_version'] = version_match.group(1)
        
        # 解析序列号
        sn_match = re.search(r'Device serial number\s+([\w]+)', version_output)
        if sn_match:
            info['serial_number'] = sn_match.group(1)
        
        # 解析运行时间
        uptime_match = re.search(r'Uptime is\s+(.+)', version_output)
        if uptime_match:
            info['uptime'] = uptime_match.group(1).strip()
        
        # 解析内存信息
        memory_match = re.search(r'Memory size\s+:\s+(\d+)\s*KB', version_output)
        if memory_match:
            info['memory'] = f"{memory_match.group(1)}KB"
        
        return info
    
    def get_interface_status(self, device_ip: str) -> Dict[str, Any]:
        """获取接口状态"""
        return self.get_config(device_ip, 'interface')
    
    def configure_ospf(self, device_ip: str, process_id: str, network: str, area: str) -> Dict[str, Any]:
        """配置OSPF"""
        commands = [
            f'ospf {process_id}',
            f'area {area}',
            f'network {network}',
            'quit',
            'quit'
        ]
        return self.modify_config(device_ip, 'ospf', commands)
    
    def configure_bgp(self, device_ip: str, as_number: str, neighbor_ip: str, neighbor_as: str) -> Dict[str, Any]:
        """配置BGP"""
        commands = [
            f'bgp {as_number}',
            f'peer {neighbor_ip} as-number {neighbor_as}',
            'quit'
        ]
        return self.modify_config(device_ip, 'bgp', commands)
    
    def configure_rip(self, device_ip: str, version: str = '2', network: str = None) -> Dict[str, Any]:
        """配置RIP"""
        commands = [
            'rip',
            f'version {version}'
        ]
        if network:
            commands.append(f'network {network}')
        commands.append('quit')
        return self.modify_config(device_ip, 'rip', commands)
    
    def configure_static_route(self, device_ip: str, destination: str, mask: str, next_hop: str) -> Dict[str, Any]:
        """配置静态路由"""
        commands = [
            f'ip route-static {destination} {mask} {next_hop}'
        ]
        return self.modify_config(device_ip, 'static_route', commands)
    
    def configure_interface(self, device_ip: str, interface_name: str, ip_address: str, subnet_mask: str) -> Dict[str, Any]:
        """配置接口IP地址"""
        commands = [
            f'interface {interface_name}',
            f'ip address {ip_address} {subnet_mask}',
            'undo shutdown',
            'quit'
        ]
        return self.modify_config(device_ip, 'interface', commands)
    
    def configure_vlan(self, device_ip: str, vlan_id: str, vlan_name: str = None) -> Dict[str, Any]:
        """配置VLAN"""
        commands = [
            f'vlan {vlan_id}'
        ]
        if vlan_name:
            commands.append(f'name {vlan_name}')
        commands.append('quit')
        return self.modify_config(device_ip, 'vlan', commands)
    
    def enable_lldp(self, device_ip: str) -> Dict[str, Any]:
        """启用LLDP"""
        commands = ['lldp global enable']
        return self.modify_config(device_ip, 'lldp', commands)
    
    def disable_lldp(self, device_ip: str) -> Dict[str, Any]:
        """禁用LLDP"""
        commands = ['undo lldp global enable']
        return self.modify_config(device_ip, 'lldp', commands)