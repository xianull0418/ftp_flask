import socket
import json
import os
from pathlib import Path
import time

class FTPClient:
    def __init__(self):
        self.connections = {}  # 存储所有FTP连接
        self.transfers = {}    # 存储传输状态
        
    def connect(self, host, username='anonymous', password='', port=21):
        """连接到FTP服务器"""
        try:
            print(f"尝试连接到FTP服务器 {host}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 设置超时时间
            sock.connect((host, port))
            print("成功建立Socket连接")
            
            # 发送认证信息
            auth_data = {
                'command': 'AUTH',
                'args': {
                    'username': username,
                    'password': password
                }
            }
            print(f"发送认证信息: {auth_data}")
            sock.send(json.dumps(auth_data).encode())
            
            # 接收认证响应
            response = json.loads(sock.recv(1024).decode())
            print(f"收到认证响应: {response}")
            if response['status'] != 'success':
                raise Exception(response['message'])
            
            connection_id = f"{host}:{port}"
            self.connections[connection_id] = {
                'socket': sock,
                'host': host,
                'port': port,
                'username': username,
                'permissions': response['permissions']
            }
            print(f"FTP连接成功建立，connection_id: {connection_id}")
            return connection_id
            
        except Exception as e:
            print(f"连接失败: {str(e)}")
            raise

    def disconnect(self, connection_id):
        """断开FTP连接"""
        if connection_id in self.connections:
            try:
                self.connections[connection_id]['socket'].close()
                del self.connections[connection_id]
                return True
            except Exception as e:
                print(f"断开连接失败: {str(e)}")
                return False
        return False

    def list_files(self, connection_id, path='/'):
        """获取文件列表"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        sock = self.connections[connection_id]['socket']
        try:
            # 发送LIST命令
            command = {
                'command': 'LIST',
                'args': {'path': path}
            }
            sock.send(json.dumps(command).encode())
            
            # 接收响应
            response = json.loads(sock.recv(1024).decode())
            if response['status'] != 'success':
                raise Exception(response['message'])
                
            return response['files']
            
        except Exception as e:
            raise Exception(f"获取文件列表失败: {str(e)}")

    def upload_file(self, connection_id, local_path, remote_path):
        """上传文件到FTP服务器"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        sock = self.connections[connection_id]['socket']
        try:
            # 获取文件大小
            file_size = os.path.getsize(local_path)
            
            # 发送UPLOAD命令
            command = {
                'command': 'UPLOAD',
                'args': {
                    'filename': remote_path,
                    'size': file_size
                }
            }
            sock.send(json.dumps(command).encode())
            
            # 接收响应
            response = json.loads(sock.recv(1024).decode())
            if response['status'] != 'ready':
                raise Exception(response.get('message', '准备上传失败'))
                
            # 连接数据端口
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(30)
            data_sock.connect((self.connections[connection_id]['host'], response['port']))
            
            # 发送文件数据
            with open(local_path, 'rb') as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    data_sock.send(data)
                    
            data_sock.close()
            return response['transfer_id']
            
        except Exception as e:
            raise Exception(f"上传文件失败: {str(e)}")

    def download_file(self, connection_id, remote_path, local_path):
        """下载文件"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        sock = self.connections[connection_id]['socket']
        try:
            # 发送DOWNLOAD命令
            command = {
                'command': 'DOWNLOAD',
                'args': {
                    'filename': remote_path
                }
            }
            sock.send(json.dumps(command).encode())
            
            # 接收响应
            response = json.loads(sock.recv(1024).decode())
            if response['status'] != 'ready':
                raise Exception(response['message'])
                
            # 创建数据连接
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((self.connections[connection_id]['host'], response['port']))
            
            # 接收文件数据
            with open(local_path, 'wb') as f:
                while True:
                    data = data_sock.recv(8192)
                    if not data:
                        break
                    f.write(data)
                    
            data_sock.close()
            return response['transfer_id']
            
        except Exception as e:
            raise Exception(f"下载文件失败: {str(e)}")

    def get_transfer_status(self, connection_id, transfer_id):
        """获取传输状态"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        sock = self.connections[connection_id]['socket']
        try:
            # 发送CHECK命令
            command = {
                'command': 'CHECK',
                'args': {
                    'transfer_id': transfer_id
                }
            }
            sock.send(json.dumps(command).encode())
            
            # 接收响应
            response = json.loads(sock.recv(1024).decode())
            if response['status'] != 'success':
                raise Exception(response['message'])
                
            return response['transfer']
            
        except Exception as e:
            raise Exception(f"获取传输状态失败: {str(e)}")

# 创建全局FTP客户端实例
ftp_client = FTPClient() 