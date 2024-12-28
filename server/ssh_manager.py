import paramiko
import os
from pathlib import Path
from server.config import SSH_CONFIG

class SSHManager:
    def __init__(self):
        self.connections = {}
        self.key_folder = Path(SSH_CONFIG['key_folder'])
        self.key_folder.mkdir(exist_ok=True)
        
    def connect_with_password(self, host, username, password, port=22):
        """使用密码连接远程服务器"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=SSH_CONFIG['connection_timeout']
            )
            
            # 存储连接信息
            connection_id = f"{username}@{host}:{port}"
            self.connections[connection_id] = {
                'client': ssh,
                'type': 'password'
            }
            return connection_id
            
        except Exception as e:
            raise Exception(f"SSH连接失败: {str(e)}")
            
    def connect_with_key(self, host, username, key_path, key_password=None, port=22):
        """使用SSH密钥连接远程服务器"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 加载私钥
            private_key = paramiko.RSAKey.from_private_key_file(
                key_path,
                password=key_password
            )
            
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                pkey=private_key,
                timeout=SSH_CONFIG['connection_timeout']
            )
            
            connection_id = f"{username}@{host}:{port}"
            self.connections[connection_id] = {
                'client': ssh,
                'type': 'key'
            }
            return connection_id
            
        except Exception as e:
            raise Exception(f"SSH密钥连接失败: {str(e)}")
            
    def execute_command(self, connection_id, command):
        """在远程服务器上执行命令"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        ssh = self.connections[connection_id]['client']
        stdin, stdout, stderr = ssh.exec_command(command)
        return {
            'stdout': stdout.read().decode(),
            'stderr': stderr.read().decode()
        }
        
    def upload_file(self, connection_id, local_path, remote_path):
        """上传文件到远程服务器"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        ssh = self.connections[connection_id]['client']
        sftp = ssh.open_sftp()
        
        try:
            # 规范化远程路径
            remote_path = remote_path.replace('\\', '/')
            remote_dir = os.path.dirname(remote_path)
            
            print(f"本地文件路径: {local_path}")  # 添加调试日志
            print(f"远程文件路径: {remote_path}")
            print(f"远程目录: {remote_dir}")
            
            # 确保远程目录存在
            try:
                sftp.stat(remote_dir)
            except IOError:
                print(f"创建远程目录: {remote_dir}")  # 添加调试日志
                # 创建所有必要的父目录
                current_dir = ''
                for dir_part in remote_dir.split('/'):
                    if dir_part:
                        current_dir += '/' + dir_part
                        try:
                            sftp.stat(current_dir)
                        except IOError:
                            ssh.exec_command(f'mkdir -p "{current_dir}"')
            
            # 上传文件
            print(f"开始上传文件...")  # 添加调试日志
            sftp.put(local_path, remote_path)
            print(f"文件上传完成")
            
            # 验证文件是否存在
            try:
                sftp.stat(remote_path)
                print(f"文件验证成功")
            except IOError as e:
                raise Exception(f"文件上传后无法验证: {str(e)}")
            
        except Exception as e:
            print(f"上传出错: {str(e)}")  # 添加错误日志
            raise
        finally:
            sftp.close()
            
    def download_file(self, connection_id, remote_path, local_path):
        """从远程服务器下载文件"""
        if connection_id not in self.connections:
            raise Exception("未找到连接")
            
        ssh = self.connections[connection_id]['client']
        sftp = ssh.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()
            
    def close_connection(self, connection_id):
        """关闭SSH连接"""
        if connection_id in self.connections:
            self.connections[connection_id]['client'].close()
            del self.connections[connection_id]
            
    def __del__(self):
        """清理所有连接"""
        for connection_id in list(self.connections.keys()):
            self.close_connection(connection_id)

ssh_manager = SSHManager() 