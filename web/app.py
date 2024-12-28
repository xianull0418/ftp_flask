from flask import Flask, render_template, request, jsonify, session, send_file
from pathlib import Path
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.auth import authenticate_user, get_user_permissions
from server.ssh_manager import ssh_manager
from server.config import SSH_CONFIG

# 获取当前文件所在目录
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)
app.secret_key = 'your-secret-key'  # 在生产环境中使用安全的密钥

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('dashboard.html', 
                         username=session['username'],
                         permissions=get_user_permissions(session['username']))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    if authenticate_user(username, password):
        session['username'] = username
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/files')
def list_files():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
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
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
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
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    # 处理上传的密钥文件
    if 'key_file' not in request.files:
        return jsonify({'error': '未提供密钥文件'})
        
    key_file = request.files['key_file']
    key_path = os.path.join(SSH_CONFIG['key_folder'], f"{session['username']}_{key_file.filename}")
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

@app.route('/remote/execute', methods=['POST'])
def execute_remote_command():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    data = request.json
    try:
        result = ssh_manager.execute_command(
            data['connection_id'],
            data['command']
        )
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/disconnect', methods=['POST'])
def disconnect_remote():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    data = request.json
    try:
        ssh_manager.close_connection(data['connection_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/files', methods=['POST'])
def get_remote_files():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    data = request.json
    try:
        # 执行ls命令获取文件列表
        result = ssh_manager.execute_command(
            data['connection_id'],
            f"ls -la --time-style=long-iso {data['path']}"  # 使用标准化的时间格式
        )
        
        if result['stderr']:
            return jsonify({
                'success': False,
                'error': result['stderr']
            })
        
        # 解析ls命令输出
        files = []
        for line in result['stdout'].splitlines():
            try:
                if line.startswith('total ') or not line.strip():
                    continue
                    
                parts = line.split(maxsplit=8)  # 最多分割8次，保持文件名完整
                if len(parts) >= 8:
                    permissions = parts[0]
                    size = parts[4]
                    date = f"{parts[5]} {parts[6]}"  # 合并日期和时间
                    name = parts[-1]  # 最后一部分是文件名
                    
                    if name not in ['.', '..']:
                        files.append({
                            'name': name,
                            'type': 'directory' if permissions.startswith('d') else 'file',
                            'size': int(size),
                            'modified': date,
                            'permissions': permissions
                        })
            except Exception as e:
                print(f"解析行出错: {line}, 错误: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        print(f"获取文件列表出错: {str(e)}")  # 添加服务器��日志
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/remote/download', methods=['POST'])
def download_remote_file():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    data = request.json
    try:
        # 创建临时目录存储下载的文件
        temp_dir = Path('./temp_downloads')
        temp_dir.mkdir(exist_ok=True)
        
        # 生成临时文件路径
        local_path = temp_dir / f"{session['username']}_{os.path.basename(data['file_path'])}"
        
        # 下载文件
        ssh_manager.download_file(
            data['connection_id'],
            data['file_path'],
            str(local_path)
        )
        
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

@app.route('/remote/upload', methods=['POST'])
def upload_remote_file():
    if 'username' not in session:
        return jsonify({'error': '未登录'})
        
    if 'file' not in request.files:
        return jsonify({'error': '未提供文件'})
        
    file = request.files['file']
    connection_id = request.form['connection_id']
    remote_path = request.form['remote_path']
    
    try:
        # 创建临时目录存储上传的文件
        temp_dir = Path('./temp_uploads')
        temp_dir.mkdir(exist_ok=True)
        
        # 保存文件到临时目录
        temp_path = temp_dir / f"{session['username']}_{file.filename}"
        file.save(temp_path)
        
        # 构建远程路径（确保路径正确）
        remote_file_path = os.path.join(remote_path, file.filename).replace('\\', '/')
        if not remote_file_path.startswith('/'):
            remote_file_path = '/' + remote_file_path
            
        print(f"上传文件到远程路径: {remote_file_path}")  # 添加调试日志
        
        try:
            # 上传文件到远程服务器
            ssh_manager.upload_file(
                connection_id,
                str(temp_path),
                remote_file_path
            )
            
            # 验证文件是否上传成功
            result = ssh_manager.execute_command(
                connection_id,
                f"ls -l '{remote_file_path}'"
            )
            
            if result['stderr']:
                raise Exception(f"文件验证失败: {result['stderr']}")
                
            return jsonify({
                'success': True,
                'message': f'文件 {file.filename} 上传成功'
            })
            
        except Exception as e:
            raise Exception(f"文件上传失败: {str(e)}")
            
    except Exception as e:
        print(f"上传错误: {str(e)}")  # 添加错误日志
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 