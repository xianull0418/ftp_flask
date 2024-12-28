import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# FTP服务器配置
FTP_CONFIG = {
    'host': '0.0.0.0',
    'port': 21,
    'data_port': 38017,
    'root_dir': 'files',  # 相对于服务器目录的路径
    'buffer_size': 65536  # 64KB
}

# FTP用户配置
FTP_USERS = {
    'admin': {
        'password': 'admin123',
        'permissions': ['read', 'write', 'delete'],
        'home_dir': '/',  # 用户主目录
        'description': '管理员账户'
    },
    'guest': {
        'password': 'guest123',
        'permissions': ['read'],
        'home_dir': '/public',  # 限制在public目录
        'description': '访客账户'
    },
    'anonymous': {
        'password': '',  # 匿名用户无需密码
        'permissions': ['read'],
        'home_dir': '/public',
        'description': '匿名账户'
    }
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.path.join(PROJECT_ROOT, 'ftp_server.log')
} 