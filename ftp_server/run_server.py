import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from ftp_server.server.ftp_server import FTPService
from ftp_server.config import FTP_CONFIG
import time

def main():
    # 创建服务器实例
    server = FTPService(
        host=FTP_CONFIG['host'],
        port=FTP_CONFIG['port']
    )
    
    try:
        # 启动服务器
        server.start()
        print("\nFTP服务器已启动，按Ctrl+C停止...")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器运行出错: {e}")
        server.stop()

if __name__ == '__main__':
    main() 