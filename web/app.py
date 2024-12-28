from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import os
import sys
import time
import socket
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from .config import FTP_CONFIG, TEMP_DIR
from .server_manager import server_manager

# 获取当前文件所在目录
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/files')
def list_files():
    root_dir = Path('./files')
    files = []
    for file_path in root_dir.glob('**/*'):
        if file_path.is_file():
            files.append({
                'name': file_path.name,
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime
            })
    return jsonify({'files': files})

@app.route('/connect/password', methods=['POST'])
def connect_with_password():
    data = request.json
    try:
        connection_id = ssh_manager.connect_with_password(
            host=data['host'],
            username=data['ssh_username'],
            password=data['ssh_password'],
            port=int(data.get('port', 22))
        )
        return jsonify({
            'success': True,
            'connection_id': connection_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/connect/key', methods=['POST'])
def connect_with_key():
    if 'key_file' not in request.files:
        return jsonify({'error': '未提供密钥文件'})
        
    key_file = request.files['key_file']
    key_path = os.path.join(SSH_CONFIG['key_folder'], f"key_{key_file.filename}")
    key_file.save(key_path)
    
    try:
        connection_id = ssh_manager.connect_with_key(
            host=request.form['host'],
            username=request.form['ssh_username'],
            key_path=key_path,
            key_password=request.form.get('key_password'),
            port=int(request.form.get('port', 22))
        )
        return jsonify({
            'success': True,
            'connection_id': connection_id
        })
    except Exception as e:
        # 清理密钥文件
        os.remove(key_path)
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/disconnect', methods=['POST'])
def disconnect_remote():
    """断开FTP连接"""
    data = request.json
    try:
        # 使用 server_manager 而不是 ssh_manager
        server_manager.disconnect(data['connection_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/files', methods=['POST'])
def get_remote_files():
    data = request.json
    try:
        print(f"获取远程文件列表，参数: {data}")  # 添加日志
        
        # 使用FTP客户端获取文件列表
        files = server_manager.list_files(
            data['connection_id'],
            data.get('path', '/')
        )
        
        print(f"获取到文件列表: {files}")  # 添加日志
        
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        print(f"获取文件列表出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/upload', methods=['POST'])
def upload_remote_file():
    """准备文件上传"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '无效的请求数据'})
            
        print(f"准备上传文件，参数: {data}")  # 添加日志
        
        # 发送UPLOAD命令到FTP服务器
        command = {
            'command': 'UPLOAD',
            'args': {
                'filename': data['filename'],
                'size': data['size']
            }
        }
        
        # 获取FTP服务器响应
        sock = server_manager.get_connection(data['connection_id'])
        if not sock:
            return jsonify({'status': 'error', 'message': '未找到连接'})
            
        sock.send(json.dumps(command).encode())
        response = json.loads(sock.recv(1024).decode())
        
        print(f"FTP服务器响应: {response}")  # 添加日志
        return jsonify(response)
        
    except Exception as e:
        print(f"准备上传失败: {e}")  # 添加日志
        return jsonify({
            'status': 'error',
            'message': f'准备上传失败: {str(e)}'
        })

@app.route('/remote/download', methods=['POST'])
def download_remote_file():
    data = request.json
    try:
        # 创建临时目录
        temp_dir = Path('./temp_downloads')
        temp_dir.mkdir(exist_ok=True)
        local_path = temp_dir / f"download_{os.path.basename(data['file_path'])}"
        
        # 使用FTP下载
        transfer_id = server_manager.download_file(
            data['connection_id'],
            data['file_path'],
            str(local_path)
        )
        
        # 等待下载完成
        while True:
            status = server_manager.get_transfer_status(data['connection_id'], transfer_id)
            if status['status'] == 'completed':
                break
            elif status['status'] == 'error':
                raise Exception(status['message'])
            time.sleep(0.5)
        
        # 发送文件
        response = send_file(
            local_path,
            as_attachment=True,
            download_name=os.path.basename(data['file_path'])
        )
        
        # 清理临时文件
        os.remove(local_path)
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/transfer/status/<transfer_id>')
def get_transfer_status(transfer_id):
    """获取传输状态"""
    try:
        status = server_manager.get_transfer_status(transfer_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/servers')
def list_servers():
    """获取所有已连接的服务器列表"""
    servers = {
        'local': server_manager.local_server,
        **server_manager.remote_servers
    }
    return jsonify({'servers': servers})

@app.route('/transfer', methods=['POST'])
def transfer_file():
    """在两个服务器之间传输文件"""
    data = request.json
    try:
        transfer_id = server_manager.start_transfer(
            data['source_id'],
            data['target_id'],
            data['file_path']
        )
        return jsonify({
            'success': True,
            'transfer_id': transfer_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/servers/<server_id>/files', methods=['GET'])
def list_server_files(server_id):
    """列出服务器上的文件"""
    path = request.args.get('path', '/')
    
    try:
        # 使用FTP方式获取文件列表
        files = server_manager.list_files(server_id, path)
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/transfer', methods=['POST'])
def transfer_files():
    """在服务器之间传输文件"""
    data = request.json
    try:
        success = server_manager.transfer_file(
            data['source_id'],
            data['target_id'],
            data['source_path'],
            data['target_path']
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/connect/ftp', methods=['POST'])
def connect_ftp():
    """连接FTP服务器"""
    data = request.json
    try:
        print(f"尝试连接FTP服务器: {data}")
        connection_id = server_manager.connect_remote(
            host=data['host'],
            username=data['username'],
            password=data.get('password', ''),
            port=data.get('ftp_port', 21)
        )
        
        # 获取连接信息
        connection = server_manager.ftp_client.connections[connection_id]
        
        return jsonify({
            'success': True,
            'connection_id': connection_id,
            'permissions': connection['permissions']
        })
    except Exception as e:
        print(f"FTP连接失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/upload_data', methods=['POST'])
def upload_data():
    """处理文件数据上传"""
    if 'file' not in request.files:
        return jsonify({'error': '未提供文件'})
        
    file = request.files['file']
    connection_id = request.form['connection_id']
    transfer_id = request.form['transfer_id']
    port = int(request.form['port'])
    
    try:
        # 接到FTP服务器的数据端口
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.settimeout(30)  # 设置30秒超时
        
        # 从connection_id中获取主机地址
        host = connection_id.split(':')[0]
        print(f"正在连接数据端口: {host}:{port}")  # 添加日志
        
        # 尝试连接
        for i in range(3):  # 最多重试3次
            try:
                data_sock.connect((host, port))
                print(f"数据连接成功")
                break
            except Exception as e:
                print(f"连接尝试 {i+1} 失败: {e}")
                if i == 2:  # 最后一次尝试也失败
                    raise
                time.sleep(1)  # 等待1秒后重试
        
        # 发送文件数据
        total_sent = 0
        while True:
            data = file.read(8192)
            if not data:
                break
            data_sock.send(data)
            total_sent += len(data)
            print(f"\r已发送: {total_sent} bytes", end='')
            
        print(f"\n文件发送完成")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"上传文件失败: {e}")
        return jsonify({
            'success': False,
            'error': f'上传文件失败: {str(e)}'
        })
    finally:
        data_sock.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 