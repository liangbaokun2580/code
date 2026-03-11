# -*- coding: utf-8 -*-
"""
华为设备管理器
支持华为路由器、交换机等设备的配置管理
"""

import re
from typing import Dict, List, Any, Optional
from .base_manager import BaseDeviceManager

class HuaweiDeviceManager(BaseDeviceManager):
    """华为设备管理器"""
    
    def __init__(self):
        super().__init__()
        self.vendor = 'huawei'
        self.enable_command = 'system-view'
        self.exit_command = 'quit'
        self.end_command = 'end'
        
    def get_config(self, device_ip: str, config_type: str) -> Dict[str, Any]:
        """获取华为设备配置"""
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
        """修改华为设备配置（使用交互式shell）"""
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
            result = self.execute_interactive_command(shell, self.enable_command, wait_time=2.0)
            if not result['success']:
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
            
            # 保存配置
            if save_config:
                save_result = self.execute_interactive_command(shell, 'save', wait_time=2.0)
                # 华为设备保存配置需要确认
                if 'Y/N' in save_result.get('output', ''):
                    confirm_result = self.execute_interactive_command(shell, 'Y', wait_time=3.0)
                    results.append({
                        'command': 'save (confirmed)',
                        'success': confirm_result['success'],
                        'output': confirm_result.get('output', ''),
                        'error': confirm_result.get('error', '')
                    })
            
            # 退出配置模式
            self.execute_interactive_command(shell, self.end_command, wait_time=1.0)
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
        """重启华为设备"""
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
            
            if force_reboot:
                command += ' force'
            
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
        """获取华为设备基本信息"""
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
                'display memory-usage'
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
            'interface': ['display interface'],
            'routing': ['display ip routing-table'],
            'ospf': ['display ospf peer', 'display ospf routing'],
            'bgp': ['display bgp peer', 'display bgp routing-table'],
            'rip': ['display rip database'],
            'lldp': ['display lldp neighbor']
        }
        
        return command_map.get(config_type, ['display current-configuration'])
    
    def _parse_version_info(self, version_output: str) -> Dict[str, str]:
        """解析华为设备版本信息"""
        info = {}
        
        # 解析设备型号
        model_match = re.search(r'Huawei\s+([\w-]+)', version_output)
        if model_match:
            info['model'] = model_match.group(1)
        
        # 解析软件版本
        version_match = re.search(r'Version\s+([\d\.\w]+)', version_output)
        if version_match:
            info['software_version'] = version_match.group(1)
        
        # 解析序列号
        sn_match = re.search(r'ESN\s+([\w]+)', version_output)
        if sn_match:
            info['serial_number'] = sn_match.group(1)
        
        # 解析运行时间
        uptime_match = re.search(r'uptime is\s+(.+)', version_output)
        if uptime_match:
            info['uptime'] = uptime_match.group(1).strip()
        
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
    
    def configure_static_route(self, device_ip: str, destination: str, mask: str, next_hop: str) -> Dict[str, Any]:
        """配置静态路由"""
        commands = [
            f'ip route-static {destination} {mask} {next_hop}'
        ]
        return self.modify_config(device_ip, 'static_route', commands)