# FTP配置
FTP_CONFIG = {
    'default_port': 21,
    'data_port': 38017,  # 使用固定的数据端口
    'timeout': 10,
    'buffer_size': 8192
}

# 临时文件目录
TEMP_DIR = {
    'uploads': './temp_uploads',
    'downloads': './temp_downloads'
}

# 用户认证配置
AUTH_CONFIG = {
    'users': {
        'admin': {
            'password': 'admin123',
            'permissions': ['read', 'write', 'delete']
        },
        'guest': {
            'password': 'guest123',
            'permissions': ['read']
        }
    }
} 