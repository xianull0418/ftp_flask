# Python FTP 文件管理系统

一个基于 Python 的 Web FTP 文件管理系统，提供图形化界面和多用户权限管理。

## 功能特点

- 🔐 用户认证和权限管理
  - 支持多用户系统
  - 三种用户级别：管理员、普通用户、匿名用户
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

- 🔧 技术特性
  - 固定数据端口模式
  - 多线程文件传输
  - 断点续传支持
  - 错误处理和重试机制

## 系统要求

- Python 3.7+
- 操作系统：Windows/Linux/MacOS

## 项目结构
```txt
project/
├── ftp_server/
│ ├── init.py
│ ├── config.py # 服务器配置
│ ├── run_server.py # 服务器启动脚本
│ └── server/
│ ├── init.py
│ └── ftp_server.py # FTP服务器实现
├── ftp_client/
│ ├── init.py
│ └── ftp_client.py # FTP客户端实现
├── web/
│ ├── init.py
│ ├── app.py # Web应用主程序
│ ├── config.py # Web配置
│ ├── server_manager.py # 服务器管理
│ ├── static/
│ │ ├── css/
│ │ │ └── style.css
│ │ └── js/
│ │ └── file-manager.js
│ └── templates/
│ ├── dashboard.html
│ └── login.html
└── requirements.txt
```