from pathlib import Path
from ftp_client.ftp_client import FTPClient
import time
import os

class ServerManager:
    def __init__(self):
        self.local_server = {
            'id': 'local',
            'host': 'localhost',
            'type': 'local',
            'ftp_port': 21
        }
        self.remote_servers = {}
        self.ftp_client = FTPClient()
        
    def connect_remote(self, host, username, password='', port=21):
        """连接远程FTP服务器"""
        try:
            connection_id = self.ftp_client.connect(
                host=host,
                username=username,
                password=password,
                port=port
            )
            
            self.remote_servers[connection_id] = {
                'id': connection_id,
                'host': host,
                'username': username,
                'type': 'remote',
                'ftp_port': port
            }
            
            return connection_id
            
        except Exception as e:
            raise Exception(f"连接服务器失败: {str(e)}")
            
    def disconnect(self, connection_id):
        """断开FTP连接"""
        try:
            if self.ftp_client.disconnect(connection_id):
                if connection_id in self.remote_servers:
                    del self.remote_servers[connection_id]
                return True
            return False
        except Exception as e:
            raise Exception(f"断开连接失败: {str(e)}")
            
    def list_files(self, connection_id, path='/'):
        """列出远程服务器上的文件"""
        try:
            if connection_id not in self.remote_servers:
                raise Exception("未找到连接")
            return self.ftp_client.list_files(connection_id, path)
        except Exception as e:
            raise Exception(f"获取文件列表失败: {str(e)}")
            
    def upload_file(self, connection_id, local_path, remote_path):
        """上传文件到远程服务器"""
        try:
            if connection_id not in self.remote_servers:
                raise Exception("未找到连接")
            return self.ftp_client.upload_file(connection_id, local_path, remote_path)
        except Exception as e:
            raise Exception(f"上传文件失败: {str(e)}")
            
    def download_file(self, connection_id, remote_path, local_path):
        """从远程服务器下载文件"""
        try:
            if connection_id not in self.remote_servers:
                raise Exception("未找到连接")
            return self.ftp_client.download_file(connection_id, remote_path, local_path)
        except Exception as e:
            raise Exception(f"下载文件失败: {str(e)}")
            
    def get_transfer_status(self, connection_id, transfer_id):
        """获取传输状态"""
        try:
            if connection_id not in self.remote_servers:
                raise Exception("未找到连接")
            return self.ftp_client.get_transfer_status(connection_id, transfer_id)
        except Exception as e:
            raise Exception(f"获取传输状态失败: {str(e)}")

    def get_connection(self, connection_id):
        """获取FTP连接"""
        if connection_id not in self.remote_servers:
            return None
        return self.ftp_client.connections[connection_id]['socket']

# 创建全局实例
server_manager = ServerManager() 