import socket
import threading
import os
from pathlib import Path
import json
import time
import uuid
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from ftp_server.config import FTP_CONFIG, FTP_USERS

class FTPService:
    def __init__(self, host=None, port=None):
        self.host = host or FTP_CONFIG['host']
        self.port = port or FTP_CONFIG['port']
        self.data_port = FTP_CONFIG['data_port']
        self.buffer_size = FTP_CONFIG['buffer_size']
        
        # 使用绝对路径，并规范化
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_dir = os.path.dirname(current_dir)
        self.root_dir = Path(os.path.join(server_dir, FTP_CONFIG['root_dir'])).resolve()
        
        # 确保根目录存在
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保public目录存在
        (self.root_dir / 'public').mkdir(exist_ok=True)
        
        print(f"\n=== FTP服务器初始化 ===")
        print(f"根目录: {self.root_dir}")
        print(f"监听地址: {self.host}:{self.port}")
        
        # 初始化其他属性
        self.clients = {}
        self.transfers = {}
        self.command_socket = None
        self.running = False
        
        # 使用配置文件中的用户信息
        self.users = FTP_USERS

    def start(self):
        """启动FTP服务器"""
        try:
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 添加地址重用选项
            self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.command_socket.bind((self.host, self.port))
            self.command_socket.listen(5)
            self.running = True
            
            print(f"FTP服务器启动成功，等待连接...")
            
            # 在新线程中运行服务器
            threading.Thread(target=self._accept_connections, daemon=True).start()
            
        except Exception as e:
            print(f"启动FTP服务器失败: {e}")
            raise
        
    def _accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_sock, addr = self.command_socket.accept()
                print(f"新客户端连接: {addr}")
                threading.Thread(target=self.handle_client,
                              args=(client_sock, addr)).start()
            except Exception as e:
                if self.running:
                    print(f"接受连接出错: {e}")
                    
    def stop(self):
        """停止FTP服务器"""
        self.running = False
        if self.command_socket:
            self.command_socket.close()

    def handle_client(self, client_sock, addr):
        """处理客户端连接"""
        print(f"开始处理客户端 {addr} 的请求")
        try:
            while True:
                # 接收命令
                print(f"等待客户端 {addr} 的命令...")  # 添加日志
                cmd_data = client_sock.recv(1024).decode()
                if not cmd_data:
                    print(f"客户端 {addr} 断开连接")
                    break
                    
                print(f"收到客户端 {addr} 的命令: {cmd_data}")
                
                # 解析命令
                try:
                    cmd = json.loads(cmd_data)
                    print(f"解析命令: {cmd}")  # 添加日志
                    response = self.handle_command(cmd, addr)
                    print(f"向客户端 {addr} 发送响应: {response}")
                    client_sock.send(json.dumps(response).encode())
                except json.JSONDecodeError as e:
                    print(f"命令格式错误: {e}")  # 添加日志
                    error_response = {
                        'status': 'error',
                        'message': '无效的命令格式'
                    }
                    client_sock.send(json.dumps(error_response).encode())
                    
        except Exception as e:
            print(f"处理客户端 {addr} 时出错: {e}")
        finally:
            client_sock.close()
            if addr in self.clients:
                del self.clients[addr]
                
    def handle_command(self, cmd, addr):
        """处理FTP命令"""
        command = cmd.get('command')
        args = cmd.get('args', {})
        
        if command == 'AUTH':
            return self.cmd_auth(args, addr)
        elif command == 'LIST':
            return self.cmd_list(args.get('path', '/'))
        elif command == 'UPLOAD':
            return self.cmd_upload(args, addr)
        elif command == 'DOWNLOAD':
            return self.cmd_download(args, addr)
        elif command == 'CHECK':
            return self.cmd_check(args)
        else:
            return {'status': 'error', 'message': '未知命令'}
            
    def cmd_auth(self, args, addr):
        """处理认证命令"""
        username = args.get('username', 'anonymous')
        password = args.get('password', '')
        
        # 验证用户
        if username not in self.users:
            return {'status': 'error', 'message': '用户不存在'}
            
        # 验证密码（匿名用户不需要密码）
        if username != 'anonymous' and self.users[username]['password'] != password:
            return {'status': 'error', 'message': '密码错误'}
            
        # 存储客户端信息
        self.clients[addr] = {
            'username': username,
            'authenticated': True,
            'permissions': self.users[username]['permissions'],
            'home_dir': self.users[username]['home_dir']
        }
        
        return {
            'status': 'success',
            'message': f'欢迎 {username}',
            'permissions': self.users[username]['permissions']
        }
            
    def cmd_list(self, path):
        """处理LIST命令"""
        try:
            print(f"\n=== 开始处理LIST命令 ===")
            print(f"请求路径: {path}")
            print(f"FTP根目录: {self.root_dir}")
            
            # 规范化请求路径
            if path == '/':
                target_path = self.root_dir
            else:
                target_path = (self.root_dir / path.lstrip('/')).resolve()
            
            print(f"目标完整路径: {target_path}")
            print(f"root_dir: {self.root_dir}")
            
            # 安全检查：确保目标路径在root_dir内
            try:
                target_path.relative_to(self.root_dir)
            except ValueError:
                print(f"错误：访问限制 - 路径在root_dir外")
                return {'status': 'error', 'message': '访问被拒绝'}
            
            if not target_path.exists():
                print(f"错误：路径不存在")
                return {'status': 'error', 'message': '路径不存在'}
                
            if not target_path.is_dir():
                print(f"错误：路径不是目录")
                return {'status': 'error', 'message': '路径不是目录'}
                
            files = []
            print("\n开始扫描目录内容:")
            
            try:
                for item in target_path.iterdir():
                    try:
                        stat = item.stat()
                        file_info = {
                            'name': item.name,
                            'type': 'directory' if item.is_dir() else 'file',
                            'size': stat.st_size if item.is_file() else 0,
                            'modified': stat.st_mtime,
                            'permissions': oct(stat.st_mode)[-3:]
                        }
                        files.append(file_info)
                        print(f"找到: {item.name} ({file_info['type']})")
                    except Exception as e:
                        print(f"处理文件 {item.name} 时出错: {e}")
                        continue
                        
            except Exception as e:
                print(f"扫描目录时出错: {e}")
                return {'status': 'error', 'message': f'扫描目录失败: {str(e)}'}
                
            print(f"\n扫描完成，共找到 {len(files)} 个文件/目录")
            print("文件列表:")
            for f in files:
                print(f"- {f['name']} ({f['type']})")
                
            return {'status': 'success', 'files': files}
            
        except Exception as e:
            print(f"\n处理LIST命令出错: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def cmd_check(self, args):
        """检查文件是否存在及其大小"""
        filename = args.get('filename')
        if not filename:
            return {'status': 'error', 'message': '未提供文件名'}
            
        file_path = self.root_dir / filename.lstrip('/')
        if file_path.exists() and file_path.is_file():
            return {
                'status': 'exists',
                'size': file_path.stat().st_size
            }
        return {'status': 'not_found'}
            
    def _get_next_data_port(self):
        """获取下一个可用的数据端口"""
        for port in range(self.data_port_range[0], self.data_port_range[1]):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('0.0.0.0', port))
                sock.close()
                return port
            except:
                continue
        raise Exception("没有可用的数据端口")

    def cmd_upload(self, args, addr):
        """处理UPLOAD命令"""
        if not self.check_permission(addr, 'write'):
            return {'status': 'error', 'message': '没有上传权限'}
        try:
            filename = args.get('filename')
            filesize = args.get('size')
            resume_pos = args.get('resume_pos', 0)
            
            if not filename or filesize is None:
                return {'status': 'error', 'message': '参数不完整'}
            
            # 规范化文件路径
            filename = filename.lstrip('/')
            file_path = (self.root_dir / filename).resolve()
            
            # 安全检查：确保文件路径在root_dir内
            try:
                file_path.relative_to(self.root_dir)
            except ValueError:
                return {'status': 'error', 'message': '访问被拒绝'}
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建数据连接
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                data_sock.bind(('0.0.0.0', self.data_port))
            except OSError as e:
                if e.errno == 98:  # 端口已被占用
                    return {'status': 'error', 'message': '数据端口被占用，请稍后重试'}
                raise
                
            data_sock.listen(1)
            
            print(f"数据连接已创建，监听端口: {self.data_port}")
            
            # 生成传输ID
            transfer_id = str(uuid.uuid4())
            
            # 记录传输信息
            self.transfers[transfer_id] = {
                'type': 'upload',
                'filename': filename,
                'total_size': filesize,
                'current_size': resume_pos,
                'start_time': time.time(),
                'data_sock': data_sock  # 保存socket引用
            }
            
            # 启动传输处理线程
            threading.Thread(target=self._handle_upload,
                           args=(transfer_id, file_path, resume_pos)).start()
            
            return {
                'status': 'ready',
                'port': self.data_port,
                'transfer_id': transfer_id
            }
            
        except Exception as e:
            print(f"处理上传命令时出错: {e}")
            return {'status': 'error', 'message': f'上传文件失败: {str(e)}'}
        
    def _handle_upload(self, transfer_id, file_path, resume_pos):
        """处理上传数据传输"""
        transfer = self.transfers[transfer_id]
        data_sock = transfer['data_sock']
        client_sock = None
        
        try:
            print(f"等待数据连接...")
            data_sock.settimeout(30)  # 设置30秒超时
            client_sock, addr = data_sock.accept()
            print(f"数据连接已建立: {addr}")
            
            client_sock.settimeout(30)  # 设置30秒超时
            mode = 'ab' if resume_pos > 0 else 'wb'
            
            with open(file_path, mode) as f:
                if resume_pos > 0:
                    f.seek(resume_pos)
                    
                received_size = resume_pos
                while received_size < transfer['total_size']:
                    try:
                        data = client_sock.recv(self.buffer_size)
                        if not data:
                            break
                        f.write(data)
                        received_size += len(data)
                        transfer['current_size'] = received_size
                        print(f"\r上传进度: {received_size}/{transfer['total_size']} bytes", end='')
                    except socket.timeout:
                        print(f"\n接收数据超时")
                        break
                    
                print(f"\n文件上传完成: {file_path}")
                
        except socket.timeout:
            print(f"等待数据连接超时")
            transfer['error'] = "连接超时"
        except Exception as e:
            print(f"上传处理出错: {e}")
            transfer['error'] = str(e)
        finally:
            if client_sock:
                client_sock.close()
            data_sock.close()
            
    def cmd_download(self, args, addr):
        """处理DOWNLOAD命令"""
        if not self.check_permission(addr, 'read'):
            return {'status': 'error', 'message': '��有下载权限'}
        filename = args.get('filename')
        if not filename:
            return {'status': 'error', 'message': '未提供文件名'}
            
        file_path = self.root_dir / filename.lstrip('/')
        if not file_path.exists() or not file_path.is_file():
            return {'status': 'error', 'message': '文件不存在'}
            
        # 创建数据连接
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            data_sock.bind(('0.0.0.0', self.data_port))
        except OSError as e:
            if e.errno == 98:  # 端口已被占用
                return {'status': 'error', 'message': '数据端口被占用，请稍后重试'}
            raise
            
        data_sock.listen(1)
        
        # 生成传输ID
        transfer_id = str(uuid.uuid4())
        file_size = file_path.stat().st_size
        
        # 记录传输信息
        self.transfers[transfer_id] = {
            'type': 'download',
            'filename': filename,
            'total_size': file_size,
            'current_size': 0,
            'start_time': time.time()
        }
        
        # 启动传输处理线程
        threading.Thread(target=self._handle_download,
                       args=(transfer_id, file_path, data_sock)).start()
        
        return {
            'status': 'ready',
            'port': self.data_port,
            'transfer_id': transfer_id,
            'size': file_size
        }
        
    def _handle_download(self, transfer_id, file_path, data_sock):
        """处理下载数据传输"""
        try:
            client_sock, _ = data_sock.accept()
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)  # 设置发送缓冲区为256KB
            
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(self.buffer_size)
                    if not data:
                        break
                    client_sock.send(data)
                    self.transfers[transfer_id]['current_size'] += len(data)
                    
        except Exception as e:
            self.transfers[transfer_id]['error'] = str(e)
        finally:
            client_sock.close()
            data_sock.close()

    def check_permission(self, addr, required_permission):
        """检查客户端权限"""
        if addr not in self.clients:
            return False
        return required_permission in self.clients[addr]['permissions']

    def get_user_root_dir(self, addr):
        """获取用户的根目录"""
        if addr not in self.clients:
            return self.root_dir
        return self.root_dir / self.clients[addr]['home_dir'].lstrip('/')

if __name__ == '__main__':
    server = FTPService()
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop() 