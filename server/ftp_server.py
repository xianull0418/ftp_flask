import socket
import threading
import os
from pathlib import Path
import json
from auth import authenticate_user

class FTPServer:
    def __init__(self, host='0.0.0.0', port=21, web_port=5000):
        self.host = host
        self.port = port
        self.web_port = web_port
        self.root_dir = Path('./files')
        self.root_dir.mkdir(exist_ok=True)
        
        # 创建命令socket
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.command_socket.bind((self.host, self.port))
        self.command_socket.listen(5)
        
    def start(self):
        print(f"FTP服务器启动在 {self.host}:{self.port}")
        while True:
            client_sock, addr = self.command_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_sock, addr)
            )
            client_thread.start()
            
    def handle_client(self, client_sock, addr):
        print(f"客户端连接：{addr}")
        try:
            # 身份验证
            auth_data = client_sock.recv(1024).decode()
            username, password = json.loads(auth_data)
            if not authenticate_user(username, password):
                client_sock.send("认证失败".encode())
                return
                
            client_sock.send("认证成功".encode())
            
            while True:
                cmd = client_sock.recv(1024).decode()
                if not cmd:
                    break
                    
                cmd_parts = cmd.split()
                if not cmd_parts:
                    continue
                    
                command = cmd_parts[0].upper()
                
                if command == "UPLOAD":
                    self.handle_upload(client_sock, cmd_parts[1])
                elif command == "DOWNLOAD":
                    self.handle_download(client_sock, cmd_parts[1])
                elif command == "LIST":
                    self.handle_list(client_sock)
                elif command == "QUIT":
                    break
                    
        except Exception as e:
            print(f"处理客户端出错: {e}")
        finally:
            client_sock.close()
            
    def handle_upload(self, client_sock, filename):
        file_path = self.root_dir / filename
        try:
            # 获取文件大小
            file_size = int(client_sock.recv(1024).decode())
            client_sock.send(b"ready")
            
            # 检查是否存在部分文件
            start_pos = 0
            if file_path.exists():
                start_pos = file_path.stat().st_size
                client_sock.send(str(start_pos).encode())
            else:
                client_sock.send(b"0")
                
            with open(file_path, 'ab') as f:
                received_size = start_pos
                while received_size < file_size:
                    data = client_sock.recv(8192)
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)
                    
            client_sock.send(b"success")
        except Exception as e:
            client_sock.send(f"error: {str(e)}".encode()) 