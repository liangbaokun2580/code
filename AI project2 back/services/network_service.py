import socket
import subprocess
import threading
import ipaddress
import uuid
import platform
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import time
import re
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

class NetworkService:
    """网络服务类，提供网络扫描和设备发现功能"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scan_timeout = 5  # 扫描超时时间（秒）
        self.max_threads = 50  # 最大并发线程数
        self.is_windows = platform.system().lower().startswith('win')
        self.is_macos = platform.system().lower() == 'darwin'

    _scan_jobs: Dict[str, Dict[str, Any]] = {}
    _scan_jobs_lock = Lock()

    def start_scan(self, target_network: str = '192.168.1.0/24', scan_type: str = 'ping',
                   user_id: Optional[int] = None) -> str:
        """Start a background scan and return a scan identifier."""
        scan_id = str(uuid.uuid4())
        job = {
            'scan_id': scan_id,
            'status': 'queued',
            'progress': 0,
            'target_network': target_network,
            'scan_type': scan_type,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None,
        }
        with self._scan_jobs_lock:
            self._scan_jobs[scan_id] = job

        worker = threading.Thread(
            target=self._run_scan_job,
            args=(scan_id, target_network, scan_type, user_id),
            daemon=True,
        )
        worker.start()
        return scan_id

    def _run_scan_job(self, scan_id: str, target_network: str, scan_type: str,
                      user_id: Optional[int]) -> None:
        """Execute a queued scan job."""
        with self._scan_jobs_lock:
            job = self._scan_jobs.get(scan_id)
            if not job:
                return
            job['status'] = 'running'
            job['progress'] = 10
            job['started_at'] = datetime.utcnow().isoformat()

        try:
            result = self.scan_network(
                scan_range=target_network,
                scan_type=scan_type,
                user_id=user_id,
            )
            status = 'failed' if result.get('error') else 'completed'
            with self._scan_jobs_lock:
                job = self._scan_jobs.get(scan_id)
                if not job:
                    return
                job['status'] = status
                job['progress'] = 100
                job['completed_at'] = datetime.utcnow().isoformat()
                job['result'] = result
                job['error'] = result.get('error')
        except Exception as exc:
            self.logger.error("Background scan %s failed: %s", scan_id, exc)
            with self._scan_jobs_lock:
                job = self._scan_jobs.get(scan_id)
                if not job:
                    return
                job['status'] = 'failed'
                job['progress'] = 100
                job['completed_at'] = datetime.utcnow().isoformat()
                job['error'] = str(exc)

    def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest snapshot of a background scan job."""
        with self._scan_jobs_lock:
            job = self._scan_jobs.get(scan_id)
            if not job:
                return None
            return dict(job)

    def _run_command(self, command: List[str], timeout: int = 10):
        """统一执行系统命令，避免重复异常处理逻辑。"""
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    def _build_ping_commands(self, host: str, timeout: int = 3) -> List[List[str]]:
        """构建跨平台ping命令候选列表，按顺序尝试。"""
        if self.is_windows:
            return [['ping', '-n', '1', '-w', str(timeout * 1000), host]]
        if self.is_macos:
            return [
                ['ping', '-c', '1', '-W', str(timeout * 1000), host],
                ['ping', '-c', '1', '-t', str(timeout), host]
            ]
        return [['ping', '-c', '1', '-W', str(timeout), host]]

    def _build_traceroute_command(self, target: str, max_hops: int = 30) -> List[str]:
        if self.is_windows:
            return ['tracert', '-h', str(max_hops), target]
        return ['traceroute', '-m', str(max_hops), target]

    def _extract_ping_latency(self, output: str) -> Optional[int]:
        """解析ping输出中的时延，兼容中英文及小于1ms场景。"""
        if not output:
            return None

        time_patterns = [
            r'(?:时间|time)[=<]\s*([0-9]+)\s*ms',
            r'(\d+(?:\.\d+)?)\s*ms'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(round(float(match.group(1))))
        return None
    
    def ping_host(self, host: str, timeout: int = 3) -> bool:
        """Ping主机检测是否在线"""
        for command in self._build_ping_commands(host, timeout):
            try:
                result = self._run_command(command, timeout=timeout + 2)
                return result.returncode == 0
            except FileNotFoundError:
                continue
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                return False
            except Exception as e:
                self.logger.error(f"Ping {host} 失败: {e}")
                return False
        return False
    
    def ping_host_with_latency(self, host: str, timeout: int = 3) -> dict:
        """Ping主机检测是否在线并返回延迟信息"""
        for command in self._build_ping_commands(host, timeout):
            try:
                start_time = time.time()
                result = self._run_command(command, timeout=timeout + 2)
                end_time = time.time()

                is_reachable = result.returncode == 0
                latency = None
                if is_reachable:
                    latency = self._extract_ping_latency(result.stdout)
                    if latency is None:
                        latency = round((end_time - start_time) * 1000)

                return {
                    'reachable': is_reachable,
                    'latency': latency,
                    'output': result.stdout if is_reachable else result.stderr
                }
            except FileNotFoundError:
                continue
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                return {
                    'reachable': False,
                    'latency': None,
                    'output': 'Ping超时'
                }
            except Exception as e:
                self.logger.error(f"Ping {host} 失败: {e}")
                return {
                    'reachable': False,
                    'latency': None,
                    'output': f'Ping失败: {str(e)}'
                }

        return {
            'reachable': False,
            'latency': None,
            'output': '系统缺少ping命令'
        }
    
    def scan_port(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """扫描单个端口"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def connectivity_test(self, target_ip: str, test_type: str, port: Optional[int] = None, count: int = 4) -> Dict[str, Any]:
        """网络连接性测试
        
        Args:
            target_ip: 目标IP地址
            test_type: 测试类型 (ping, traceroute, telnet, ssh)
            port: 端口号（用于telnet/ssh测试）
            count: ping测试次数
            
        Returns:
            测试结果字典
        """
        try:
            dispatch = {
                'ping': lambda: self._ping_test(target_ip, count),
                'traceroute': lambda: self._traceroute_test(target_ip),
                'telnet': lambda: self._telnet_test(target_ip, port if port is not None else 23),
                'ssh': lambda: self._ssh_test(target_ip, port if port is not None else 22),
            }
            if test_type not in dispatch:
                return {
                    'success': False,
                    'error': f'不支持的测试类型: {test_type}',
                    'test_type': test_type,
                    'target_ip': target_ip
                }
            return dispatch[test_type]()
        except Exception as e:
            self.logger.error(f"连接性测试失败 {target_ip}: {e}")
            return {
                'success': False,
                'error': str(e),
                'test_type': test_type,
                'target_ip': target_ip
            }
    
    def _ping_test(self, target_ip: str, count: int) -> Dict[str, Any]:
        """执行ping测试"""
        try:
            results = []
            success_count = 0
            total_latency = 0
            
            for i in range(count):
                result = self.ping_host_with_latency(target_ip)
                results.append(result)
                if result['reachable']:
                    success_count += 1
                    if result['latency']:
                        total_latency += result['latency']
            
            success_rate = (success_count / count) * 100
            avg_latency = total_latency / success_count if success_count > 0 else 0
            
            return {
                'success': True,
                'test_type': 'ping',
                'target_ip': target_ip,
                'count': count,
                'success_count': success_count,
                'success_rate': success_rate,
                'avg_latency': avg_latency,
                'results': results
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_type': 'ping',
                'target_ip': target_ip
            }
    
    def _traceroute_test(self, target_ip: str) -> Dict[str, Any]:
        """执行traceroute测试"""
        try:
            result = self._run_command(self._build_traceroute_command(target_ip, 30), timeout=60)
            
            return {
                'success': result.returncode == 0,
                'test_type': 'traceroute',
                'target_ip': target_ip,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Traceroute超时',
                'test_type': 'traceroute',
                'target_ip': target_ip
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_type': 'traceroute',
                'target_ip': target_ip
            }
    
    def _telnet_test(self, target_ip: str, port: int) -> Dict[str, Any]:
        """执行telnet连接测试"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            start_time = time.time()
            result = sock.connect_ex((target_ip, port))
            end_time = time.time()
            sock.close()
            
            is_connected = result == 0
            latency = round((end_time - start_time) * 1000, 2)
            
            return {
                'success': is_connected,
                'test_type': 'telnet',
                'target_ip': target_ip,
                'port': port,
                'latency': latency,
                'error': None if is_connected else f'无法连接到端口 {port}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_type': 'telnet',
                'target_ip': target_ip,
                'port': port
            }
    
    def _ssh_test(self, target_ip: str, port: int) -> Dict[str, Any]:
        """执行SSH连接测试"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            start_time = time.time()
            result = sock.connect_ex((target_ip, port))
            
            if result == 0:
                # 尝试读取SSH banner
                try:
                    sock.settimeout(5)
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    is_ssh = 'SSH' in banner
                except:
                    is_ssh = True  # 假设是SSH服务
            else:
                is_ssh = False
                banner = None
            
            end_time = time.time()
            sock.close()
            
            latency = round((end_time - start_time) * 1000, 2)
            
            return {
                'success': result == 0 and is_ssh,
                'test_type': 'ssh',
                'target_ip': target_ip,
                'port': port,
                'latency': latency,
                'banner': banner,
                'error': None if result == 0 else f'无法连接到SSH端口 {port}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_type': 'ssh',
                'target_ip': target_ip,
                'port': port
            }

    def scan_host_ports(self, host: str, ports: List[int]) -> List[int]:
        """扫描主机的多个端口"""
        open_ports = []
        if not ports:
            return open_ports

        max_workers = min(self.max_threads, len(ports))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_port = {
                executor.submit(self.scan_port, host, port): port
                for port in ports
            }
            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    if future.result():
                        open_ports.append(port)
                except Exception:
                    continue

        return sorted(open_ports)
    
    def get_hostname(self, ip: str) -> str:
        """获取IP地址的主机名"""
        try:
            if self.is_windows:
                result = subprocess.run(
                    ['nslookup', ip],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        stripped = line.strip()
                        if stripped.lower().startswith('name:'):
                            return stripped.split(':', 1)[1].strip()
                return ''

            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror, subprocess.TimeoutExpired, FileNotFoundError):
            return ''
        except Exception as e:
            self.logger.debug(f"获取 {ip} 主机名失败: {e}")
            return ''
    
    def get_mac_address(self, ip: str) -> str:
        """获取IP地址的MAC地址（Windows系统）"""
        try:
            # 使用arp命令获取MAC地址
            result = subprocess.run(
                ['arp', '-a', ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 解析arp输出
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ip in line:
                        # 查找MAC地址模式
                        mac_pattern = r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}'
                        match = re.search(mac_pattern, line)
                        if match:
                            return match.group(0).replace('-', ':').lower()
            
            return ''
        except Exception as e:
            self.logger.error(f"获取 {ip} 的MAC地址失败: {e}")
            return ''
    
    def detect_device_type(self, ip: str, open_ports: List[int], hostname: str = '') -> str:
        """根据开放端口和主机名检测设备类型"""
        # 常见端口对应的设备类型
        port_patterns = {
            'router': [22, 23, 80, 443, 161, 8080],
            'switch': [22, 23, 80, 161, 443],
            'server': [22, 80, 443, 3389, 5432, 3306, 1433],
            'printer': [80, 443, 515, 631, 9100],
            'camera': [80, 443, 554, 8080],
            'nas': [22, 80, 443, 139, 445, 548, 2049],
            'firewall': [22, 80, 443, 161, 4443, 8443]
        }
        
        # 根据主机名判断
        hostname_lower = hostname.lower()
        if any(keyword in hostname_lower for keyword in ['router', 'rt', 'gw', 'gateway']):
            return 'router'
        elif any(keyword in hostname_lower for keyword in ['switch', 'sw']):
            return 'switch'
        elif any(keyword in hostname_lower for keyword in ['server', 'srv']):
            return 'server'
        elif any(keyword in hostname_lower for keyword in ['printer', 'print']):
            return 'printer'
        elif any(keyword in hostname_lower for keyword in ['camera', 'cam', 'ipc']):
            return 'camera'
        elif any(keyword in hostname_lower for keyword in ['nas', 'storage']):
            return 'nas'
        
        # 根据端口组合判断
        device_scores = {}
        for device_type, typical_ports in port_patterns.items():
            score = len(set(open_ports) & set(typical_ports))
            if score > 0:
                device_scores[device_type] = score
        
        if device_scores:
            return max(device_scores, key=device_scores.get)
        
        # 默认判断
        if 22 in open_ports or 3389 in open_ports:
            return 'server'
        elif 80 in open_ports or 443 in open_ports:
            return 'web_device'
        else:
            return 'unknown'
    
    def detect_vendor(self, mac_address: str) -> str:
        """根据MAC地址检测设备厂商"""
        if not mac_address or len(mac_address) < 8:
            return ''
        
        # MAC地址前3字节（OUI）对应的厂商
        oui_vendors = {
            '00:1b:21': 'Cisco',
            '00:1c:0f': 'Cisco',
            '00:26:99': 'Cisco',
            '00:50:56': 'VMware',
            '08:00:27': 'Oracle VirtualBox',
            '52:54:00': 'QEMU/KVM',
            '00:15:5d': 'Microsoft Hyper-V',
            '00:0c:29': 'VMware',
            '00:1c:42': 'Parallels',
            '00:16:3e': 'Xen',
            '00:24:d7': 'Intel',
            '00:1f:16': 'Dell',
            '00:14:22': 'Dell',
            '70:b3:d5': 'IEEE Registration Authority',
            '00:90:27': 'Intel',
            '00:e0:81': 'Tyan Computer',
            '00:a0:c9': 'Intel',
            '00:d0:b7': 'Intel'
        }
        
        oui = mac_address[:8].lower()
        return oui_vendors.get(oui, '')

    def _build_device_info(self, host: str, scan_type: str, common_ports: List[int]) -> Dict[str, Any]:
        """构建单个主机的设备信息，避免 full 扫描串行阻塞整个请求。"""
        device_info = {
            'device_id': str(uuid.uuid4()),
            'ip_address': host,
            'hostname': '',
            'mac_address': '',
            'device_type': 'unknown',
            'vendor': '',
            'model': '',
            'status': 'online',
            'open_ports': [],
            'discovered_at': datetime.utcnow().isoformat()
        }

        if scan_type in ['full', 'snmp']:
            device_info['hostname'] = self.get_hostname(host)
            device_info['mac_address'] = self.get_mac_address(host)

        if scan_type == 'full':
            device_info['open_ports'] = self.scan_host_ports(host, common_ports)
        elif scan_type == 'snmp':
            device_info['open_ports'] = self.scan_host_ports(host, [161, 162])

        device_info['device_type'] = self.detect_device_type(
            host, device_info['open_ports'], device_info['hostname']
        )

        if device_info['mac_address']:
            device_info['vendor'] = self.detect_vendor(device_info['mac_address'])

        return device_info
    
    def scan_network_range(self, network_range: str) -> List[str]:
        """扫描网络范围内的活跃主机"""
        try:
            network = ipaddress.ip_network(network_range, strict=False)
            host_list = [str(ip) for ip in network.hosts()]
            active_hosts = []

            if not host_list:
                return active_hosts

            max_workers = min(self.max_threads, len(host_list))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_ip = {
                    executor.submit(self.ping_host, ip_str): ip_str
                    for ip_str in host_list
                }
                for future in as_completed(future_to_ip):
                    ip_str = future_to_ip[future]
                    try:
                        if future.result():
                            active_hosts.append(ip_str)
                    except Exception:
                        continue
            
            return sorted(active_hosts, key=lambda x: ipaddress.ip_address(x))
            
        except Exception as e:
            self.logger.error(f"扫描网络范围 {network_range} 失败: {e}")
            return []
    
    def scan_network(self, scan_range: str = '192.168.1.0/24', 
                    scan_type: str = 'ping', user_id: int = None) -> Dict[str, Any]:
        """扫描网络并返回设备信息"""
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"开始扫描网络: {scan_range}, 类型: {scan_type}")
            network = ipaddress.ip_network(scan_range, strict=False)
            
            # 扫描活跃主机
            active_hosts = self.scan_network_range(scan_range)
            
            devices = []
            common_ports = [22, 23, 53, 80, 110, 135, 139, 143, 443, 993, 995, 1723, 3389, 5900, 8080]

            if active_hosts:
                host_workers = min(max(4, self.max_threads // 5), len(active_hosts))
                with ThreadPoolExecutor(max_workers=host_workers) as executor:
                    future_to_host = {
                        executor.submit(self._build_device_info, host, scan_type, common_ports): host
                        for host in active_hosts
                    }
                    for future in as_completed(future_to_host):
                        host = future_to_host[future]
                        try:
                            devices.append(future.result())
                        except Exception as exc:
                            self.logger.warning("构建设备信息失败 %s: %s", host, exc)

                devices.sort(key=lambda item: ipaddress.ip_address(item['ip_address']))
                active_hosts = []
            
            for host in active_hosts:
                device_info = {
                    'device_id': str(uuid.uuid4()),
                    'ip_address': host,
                    'hostname': '',
                    'mac_address': '',
                    'device_type': 'unknown',
                    'vendor': '',
                    'model': '',
                    'status': 'online',
                    'open_ports': [],
                    'discovered_at': datetime.utcnow().isoformat()
                }
                
                # 获取主机名
                if scan_type in ['full', 'snmp']:
                    device_info['hostname'] = self.get_hostname(host)
                
                # 获取MAC地址
                if scan_type in ['full', 'snmp']:
                    device_info['mac_address'] = self.get_mac_address(host)
                
                # 端口扫描
                if scan_type == 'full':
                    device_info['open_ports'] = self.scan_host_ports(host, common_ports)
                elif scan_type == 'snmp':
                    # 只扫描SNMP相关端口
                    device_info['open_ports'] = self.scan_host_ports(host, [161, 162])
                
                # 设备类型检测
                device_info['device_type'] = self.detect_device_type(
                    host, device_info['open_ports'], device_info['hostname']
                )
                
                # 厂商检测
                if device_info['mac_address']:
                    device_info['vendor'] = self.detect_vendor(device_info['mac_address'])
                
                devices.append(device_info)
            
            end_time = datetime.utcnow()
            scan_duration = (end_time - start_time).total_seconds()
            
            scan_result = {
                'scan_id': str(uuid.uuid4()),
                'user_id': user_id,
                'scan_range': scan_range,
                'scan_type': scan_type,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': scan_duration,
                'total_hosts_scanned': sum(1 for _ in network.hosts()),
                'active_hosts_found': len(active_hosts),
                'devices': devices
            }
            
            self.logger.info(f"网络扫描完成: 发现 {len(devices)} 个设备，耗时 {scan_duration:.2f} 秒")
            
            return scan_result
            
        except Exception as e:
            self.logger.error(f"网络扫描失败: {e}")
            return {
                'scan_id': str(uuid.uuid4()),
                'user_id': user_id,
                'scan_range': scan_range,
                'scan_type': scan_type,
                'start_time': start_time.isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'error': str(e),
                'devices': []
            }
    
    def get_local_network_info(self) -> Dict[str, Any]:
        """获取详细的本地网络信息（类似ipconfig/ip a命令）"""
        try:
            import psutil
            
            # 获取本机基本信息
            hostname = socket.gethostname()
            
            # 获取所有网络接口信息
            interfaces = []
            network_stats = psutil.net_if_stats()
            network_addrs = psutil.net_if_addrs()
            
            for interface_name, addrs in network_addrs.items():
                if interface_name in network_stats:
                    stats = network_stats[interface_name]
                    
                    interface_info = {
                        'name': interface_name,
                        'is_up': stats.isup,
                        'speed': stats.speed if stats.speed > 0 else None,
                        'mtu': stats.mtu,
                        'addresses': []
                    }
                    
                    for addr in addrs:
                        addr_info = {
                            'type': str(addr.family.name) if hasattr(addr.family, 'name') else str(addr.family),
                            'address': addr.address
                        }
                        
                        if addr.netmask:
                            addr_info['netmask'] = addr.netmask
                        if addr.broadcast:
                            addr_info['broadcast'] = addr.broadcast
                            
                        interface_info['addresses'].append(addr_info)
                    
                    interfaces.append(interface_info)
            
            # 获取默认网关
            try:
                gateways = psutil.net_if_addrs()
                default_gateway = None
                # 简单方式获取默认网关
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '默认网关' in line or 'Default Gateway' in line:
                            parts = line.split(':')
                            if len(parts) > 1:
                                gateway = parts[1].strip()
                                if gateway and gateway != '':
                                    default_gateway = gateway
                                    break
            except Exception:
                default_gateway = None
            
            # 获取DNS服务器
            dns_servers = []
            try:
                result = subprocess.run(['nslookup', 'google.com'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Server:' in line:
                            dns = line.split(':')[1].strip()
                            if dns:
                                dns_servers.append(dns)
            except Exception:
                pass
            
            # 获取主要IP地址
            primary_ip = None
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(('8.8.8.8', 80))
                    primary_ip = s.getsockname()[0]
            except Exception:
                primary_ip = socket.gethostbyname(hostname)
            
            # 推断网络范围
            suggested_range = '192.168.1.0/24'
            if primary_ip:
                ip_parts = primary_ip.split('.')
                if ip_parts[0] == '192' and ip_parts[1] == '168':
                    suggested_range = f"192.168.{ip_parts[2]}.0/24"
                elif ip_parts[0] == '10':
                    suggested_range = f"10.{ip_parts[1]}.{ip_parts[2]}.0/24"
                elif ip_parts[0] == '172' and 16 <= int(ip_parts[1]) <= 31:
                    suggested_range = f"172.{ip_parts[1]}.{ip_parts[2]}.0/24"
                else:
                    suggested_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
            
            return {
                'hostname': hostname,
                'primary_ip': primary_ip,
                'default_gateway': default_gateway,
                'dns_servers': dns_servers,
                'interfaces': interfaces,
                'suggested_scan_range': suggested_range,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取本地网络信息失败: {e}")
            # 回退到简单模式
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                return {
                    'hostname': hostname,
                    'primary_ip': local_ip,
                    'default_gateway': None,
                    'dns_servers': [],
                    'interfaces': [],
                    'suggested_scan_range': '192.168.1.0/24',
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
            except Exception as e2:
                return {
                    'hostname': 'unknown',
                    'primary_ip': '127.0.0.1',
                    'default_gateway': None,
                    'dns_servers': [],
                    'interfaces': [],
                    'suggested_scan_range': '192.168.1.0/24',
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e2)
                }
    
    def trace_route(self, target: str, max_hops: int = 30) -> List[Dict[str, Any]]:
        """执行路由跟踪"""
        try:
            result = self._run_command(self._build_traceroute_command(target, max_hops), timeout=60)
            
            hops = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit():
                    # 解析tracert输出
                    parts = line.split()
                    if len(parts) >= 2:
                        hop_num = int(parts[0])
                        
                        # 查找IP地址
                        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                        ip_matches = re.findall(ip_pattern, line)
                        
                        hop_info = {
                            'hop': hop_num,
                            'ip': ip_matches[0] if ip_matches else '',
                            'hostname': '',
                            'response_times': []
                        }
                        
                        # 查找响应时间
                        time_pattern = r'(\d+)\s*ms'
                        time_matches = re.findall(time_pattern, line)
                        hop_info['response_times'] = [int(t) for t in time_matches]
                        
                        hops.append(hop_info)
            
            return hops
            
        except Exception as e:
            self.logger.error(f"路由跟踪失败: {e}")
            return []
    
    def get_network_status(self, include_recent_activity: bool = True, include_device_groups: bool = True) -> Dict[str, Any]:
        """获取网络状态概览，与拓扑页面数据保持一致"""
        try:
            # 尝试从拓扑数据获取设备信息
            try:
                from .topology_service import TopologyService
                topology_service = TopologyService()
                topology_data = topology_service.get_topology_data()
            except ImportError:
                # 如果topology_service不可用，使用数据库数据
                topology_data = self._get_topology_data_from_db()
            
            devices = topology_data.get('devices', [])
            connections = topology_data.get('connections', [])
            
            # 统计设备状态
            total_devices = len(devices)
            online_devices = sum(1 for device in devices if device.get('status') == 'online')
            offline_devices = total_devices - online_devices
            
            # 计算网络健康度
            if total_devices > 0:
                health_score = (online_devices / total_devices) * 100
            else:
                health_score = 0
            
            # 统计连接状态
            total_connections = len(connections)
            active_connections = sum(1 for conn in connections if conn.get('status') == 'active')
            
            status = {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'total_connections': total_connections,
                'active_connections': active_connections,
                'health_score': round(health_score, 1),
                'last_updated': datetime.now().isoformat()
            }
            
            # 添加最近活动（可选）
            if include_recent_activity:
                recent_activity = []
                # 按最后更新时间排序设备
                sorted_devices = sorted(devices, 
                                       key=lambda x: x.get('last_seen', ''), 
                                       reverse=True)[:10]
                
                for device in sorted_devices:
                    if device.get('last_seen'):
                        recent_activity.append({
                            'device_name': device.get('name', device.get('hostname', device.get('ip', 'Unknown'))),
                            'ip': device.get('ip'),
                            'mac': device.get('mac'),
                            'action': 'online' if device.get('status') == 'online' else 'offline',
                            'timestamp': device.get('last_seen')
                        })
                status['recent_activity'] = recent_activity
            
            # 添加设备分组统计（可选）
            if include_device_groups:
                device_types = {}
                for device in devices:
                    device_type = device.get('type', device.get('device_type', 'unknown'))
                    if device_type not in device_types:
                        device_types[device_type] = {'total': 0, 'online': 0}
                    device_types[device_type]['total'] += 1
                    if device.get('status') == 'online':
                        device_types[device_type]['online'] += 1
                
                status['device_groups'] = device_types
            
            # 添加拓扑统计信息
            status['topology_stats'] = {
                'devices_by_type': device_types if include_device_groups else {},
                'connection_types': {},
                'network_segments': []
            }
            
            # 统计连接类型
            connection_types = {}
            for conn in connections:
                conn_type = conn.get('type', 'unknown')
                if conn_type not in connection_types:
                    connection_types[conn_type] = 0
                connection_types[conn_type] += 1
            status['topology_stats']['connection_types'] = connection_types
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取网络状态失败: {e}")
            # 回退到原有逻辑
            try:
                devices = self.get_all_devices()
                total_devices = len(devices)
                online_devices = sum(1 for device in devices if device.get('status') == 'online')
                offline_devices = total_devices - online_devices
                
                if total_devices > 0:
                    health_score = (online_devices / total_devices) * 100
                else:
                    health_score = 0
                
                return {
                    'total_devices': total_devices,
                    'online_devices': online_devices,
                    'offline_devices': offline_devices,
                    'total_connections': 0,
                    'active_connections': 0,
                    'health_score': round(health_score, 1),
                    'last_updated': datetime.now().isoformat(),
                    'error': str(e)
                }
            except Exception as e2:
                return {
                    'total_devices': 0,
                    'online_devices': 0,
                    'offline_devices': 0,
                    'total_connections': 0,
                    'active_connections': 0,
                    'health_score': 0,
                    'last_updated': datetime.now().isoformat(),
                    'error': str(e2)
                }
    
    def _get_topology_data_from_db(self) -> Dict[str, Any]:
        """从数据库获取拓扑数据"""
        try:
            from models import TopologyData
            
            # 获取最新的拓扑数据
            topology = TopologyData.query.order_by(TopologyData.updated_at.desc()).first()
            
            if topology and topology.topology_data:
                import json
                if isinstance(topology.topology_data, str):
                    return json.loads(topology.topology_data)
                else:
                    return topology.topology_data
            else:
                # 如果没有拓扑数据，从NetworkDevice表构建基本数据
                devices = self.get_all_devices()
                return {
                    'devices': devices,
                    'connections': [],
                    'metadata': {
                        'source': 'database_fallback',
                        'created_at': datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            self.logger.error(f"从数据库获取拓扑数据失败: {e}")
            return {
                'devices': [],
                'connections': [],
                'metadata': {
                    'source': 'empty_fallback',
                    'error': str(e)
                }
            }
