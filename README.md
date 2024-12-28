# Python FTP 文件管理系统

一个基于 Python 的 Web FTP 文件管理系统，提供图形化界面和多用户权限管理。

## 功能特点

- 🔐 用户认证和权限管理
  - 支持多用户系统（admin/guest/anonymous）
  - 可配置的用户权限（读/写/删除）
  - 用户目录隔离

- 📂 文件管理
  - 文件上传/下载
  - 文件列表浏览
  - 目录导航
  - 文件传输进度显示

- 🌐 Web 界面
  - 响应式设计
  - 拖拽上传
  - 实时进度显示
  - 直观的文件操作

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动FTP服务器：
```bash
python -m ftp_server.run_server
```

3. 启动Web应用：
```bash
python -m web.app
```

4. 访问Web界面：
   - 打开浏览器访问 `http://localhost:5000`
   - 使用以下账号连接FTP服务器：
     - 管理员：admin/admin123
     - 访客：guest/guest123
     - 匿名：anonymous（无需密码）

## 项目结构
```
project/
├── ftp_server/          # FTP服务器
│   ├── config.py        # 服务器配置
│   ├── run_server.py    # 服务器启动脚本
│   └── server/
│       └── ftp_server.py
├── ftp_client/          # FTP客户端
│   └── ftp_client.py
└── web/                 # Web应用
    ├── app.py          # Web应用主程序
    ├── config.py       # Web配置
    ├── server_manager.py
    ├── static/
    │   ├── css/
    │   │   └── style.css
    │   └── js/
    │       └── file-manager.js
    └── templates/
        └── dashboard.html
```

## 配置说明

1. FTP服务器配置（`ftp_server/config.py`）：
```python
FTP_USERS = {
    'admin': {
        'password': 'admin123',
        'permissions': ['read', 'write', 'delete']
    },
    'guest': {
        'password': 'guest123',
        'permissions': ['read']
    },
    'anonymous': {
        'password': '',
        'permissions': ['read']
    }
}
```

2. Web应用配置（`web/config.py`）：
```python
FTP_CONFIG = {
    'default_port': 21,
    'data_port': 38017
}
```

## 使用说明

1. 连接服务器：
   - 输入服务器地址和端口
   - 选择用户类型（管理员/访客/匿名）
   - 点击连接按钮

2. 文件操作：
   - 点击文件夹进入目录
   - 点击下载按钮下载文件
   - 拖拽文件到上传区域上传文件

## 注意事项

- 确保防火墙允许FTP端口（21）和数据端口（38017）
- 上传大文件时请耐心等待
- 建议在本地网络环境使用

## 许可证

MIT License