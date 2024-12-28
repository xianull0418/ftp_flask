# FTP服务器配置
FTP_CONFIG = {
    'host': '0.0.0.0',
    'port': 21,
    'web_port': 5000,
    'max_connections': 5,
    'timeout': 300,
    'buffer_size': 8192,
    'anonymous_enabled': True,
    'upload_folder': './files',
    'max_file_size': 1024 * 1024 * 1024  # 1GB
}

# SSH连接配置
SSH_CONFIG = {
    'default_port': 22,
    'key_folder': './ssh_keys',  # 存储SSH密钥的文件夹
    'known_hosts_file': './known_hosts',
    'connection_timeout': 30
}

# 文件传输配置
TRANSFER_CONFIG = {
    'allowed_extensions': ['*'],  # '*' 表示允许所有文件类型
    'chunk_size': 8192,
    'resume_support': True,
    'compression_enabled': True
}

# 安全配置
SECURITY_CONFIG = {
    'ssl_enabled': False,
    'ssl_cert': 'cert.pem',
    'ssl_key': 'key.pem',
    'ip_blacklist': [],
    'max_login_attempts': 3
} 