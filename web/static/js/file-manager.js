// 文件上传相关变量
let currentPath = '/';
let uploadQueue = [];
let isUploading = false;
let currentConnectionId = null;
let connectedServers = new Map();  // 存储已连接的服务器信息

// 更新路径导航
function updatePathBreadcrumbs(path) {
    const parts = path.split('/').filter(p => p);
    const breadcrumbs = document.getElementById('pathBreadcrumbs');
    breadcrumbs.innerHTML = '';
    
    let currentPath = '';
    parts.forEach((part, index) => {
        currentPath += '/' + part;
        const separator = document.createElement('span');
        separator.className = 'path-separator';
        separator.textContent = '/';
        breadcrumbs.appendChild(separator);
        
        const link = document.createElement('a');
        link.className = 'path-item';
        link.textContent = part;
        link.onclick = () => showFiles(currentPath);
        breadcrumbs.appendChild(link);
    });
}

// 显示文件列表
async function showFiles(path) {
    currentPath = path;
    updatePathBreadcrumbs(path);
    
    try {
        const response = await fetch('/remote/files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_id: currentConnectionId,
                path: path
            })
        });
        
        const result = await response.json();
        if (result.success) {
            displayFiles(result.files);
        } else {
            alert('获取文件列表失败: ' + result.error);
        }
    } catch (err) {
        console.error('加载文件列表失败:', err);
        alert('加载文件列表失败');
    }
}

// 显示文件列表
function displayFiles(files) {
    const tbody = document.getElementById('fileListBody');
    tbody.innerHTML = '';
    
    const server = connectedServers.get(currentConnectionId);
    const canRead = server?.permissions.includes('read');
    
    files.forEach(file => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="file-item">
                ${file.type === 'directory' 
                    ? '<span class="file-icon">📁</span>' 
                    : '<span class="file-icon">📄</span>'}
                ${file.name}
            </td>
            <td>${formatFileSize(file.size)}</td>
            <td>${new Date(file.modified * 1000).toLocaleString()}</td>
            <td class="file-actions">
                ${file.type === 'directory' 
                    ? `<button class="btn btn-secondary" onclick="showFiles('${currentPath}/${file.name}')">打开</button>`
                    : (canRead 
                        ? `<button class="btn" onclick="downloadFile('${currentConnectionId}', '${currentPath}/${file.name}')">下载</button>`
                        : '')}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 处理文件上传
function handleUpload(files) {
    for (const file of files) {
        uploadQueue.push({
            file,
            path: currentPath + '/' + file.name
        });
    }
    processUploadQueue();
}

// 处理上传队列
async function processUploadQueue() {
    if (isUploading || uploadQueue.length === 0) return;
    
    isUploading = true;
    const upload = uploadQueue[0];
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    document.getElementById('uploadProgress').style.display = 'block';
    
    try {
        console.log('开始上传文件:', upload);  // 添加日志
        
        // 1. 发送上传命令
        const response = await fetch('/remote/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_id: currentConnectionId,
                filename: upload.path,
                size: upload.file.size
            })
        });
        
        const result = await response.json();
        console.log('上传命令响应:', result);  // 添加日志
        
        if (result.status === 'ready') {
            // 2. 建立数据连接
            const formData = new FormData();
            formData.append('file', upload.file);
            formData.append('connection_id', currentConnectionId);
            formData.append('transfer_id', result.transfer_id);
            formData.append('port', result.port);
            
            const uploadResponse = await fetch('/remote/upload_data', {
                method: 'POST',
                body: formData
            });
            
            if (uploadResponse.ok) {
                const uploadResult = await uploadResponse.json();
                if (uploadResult.success) {
                    showFiles(currentPath);
                } else {
                    throw new Error(uploadResult.error || '上传数据失败');
                }
            } else {
                throw new Error('上传数据失败');
            }
        } else {
            throw new Error(result.message || '准备上传失败');
        }
    } catch (err) {
        console.error('上传出错:', err);
        alert('上传失败: ' + err.message);
    } finally {
        uploadQueue.shift();
        isUploading = false;
        document.getElementById('uploadProgress').style.display = 'none';
        processUploadQueue();
    }
}

// 初始化上传区域
function initializeUploadZone() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    uploadZone.onclick = () => fileInput.click();
    fileInput.onchange = () => handleUpload(fileInput.files);

    uploadZone.ondragover = (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    };

    uploadZone.ondragleave = () => {
        uploadZone.classList.remove('drag-over');
    };

    uploadZone.ondrop = (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        handleUpload(e.dataTransfer.files);
    };
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeUploadZone();
});

// 连接服务器
async function connectServer() {
    const host = document.getElementById('host').value;
    const anonymous = document.getElementById('anonymous').checked;
    const username = anonymous ? 'anonymous' : document.getElementById('username').value;
    const password = anonymous ? '' : document.getElementById('password').value;
    const port = document.getElementById('port').value;

    try {
        const response = await fetch('/connect/ftp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                host: host,
                username: username,
                password: password,
                ftp_port: parseInt(port)
            })
        });

        const result = await response.json();
        if (result.success) {
            // 保存连接信息
            connectedServers.set(result.connection_id, {
                host: host,
                username: username,
                permissions: result.permissions
            });
            
            // 显示服务器
            addConnectedServer(result.connection_id, host, username);
            
            // 清空表单
            document.getElementById('host').value = '';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            document.getElementById('port').value = '21';
            document.getElementById('anonymous').checked = false;
        } else {
            alert('连接失败: ' + result.error);
        }
    } catch (err) {
        console.error('连接出错:', err);
        alert('连接出错');
    }
}

// 添加已连接服务器到列表
function addConnectedServer(connectionId, host, username) {
    const serverList = document.getElementById('serverList');
    const serverItem = document.createElement('div');
    serverItem.className = 'server-item';
    serverItem.innerHTML = `
        <div class="server-info">
            <span class="server-name">${host}</span>
            <span class="server-user">(${username})</span>
        </div>
        <div class="server-actions">
            <button class="btn" onclick="selectServer('${connectionId}')">查看文件</button>
            <button class="btn btn-secondary" onclick="disconnectServer('${connectionId}')">断开连接</button>
        </div>
    `;
    serverList.appendChild(serverItem);
}

// 选择服务器
function selectServer(connectionId) {
    currentConnectionId = connectionId;
    document.querySelector('.file-manager').style.display = 'block';
    showFiles('/');
}

// 断开服务器连接
async function disconnectServer(connectionId) {
    try {
        const response = await fetch('/remote/disconnect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_id: connectionId
            })
        });

        const result = await response.json();
        if (result.success) {
            // 移除服务器显示
            const serverItems = document.querySelectorAll('.server-item');
            serverItems.forEach(item => {
                if (item.querySelector('.server-actions').innerHTML.includes(connectionId)) {
                    item.remove();
                }
            });
            
            // 清理连接信息
            connectedServers.delete(connectionId);
            
            // 如果是当前选中的服务器，隐藏文件管理器
            if (connectionId === currentConnectionId) {
                currentConnectionId = null;
                document.querySelector('.file-manager').style.display = 'none';
            }
        } else {
            alert('断开连接失败: ' + result.error);
        }
    } catch (err) {
        console.error('断开连接出错:', err);
        alert('断开连接出错');
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 下载文件
async function downloadFile(connectionId, filePath) {
    try {
        const response = await fetch('/remote/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_id: connectionId,
                file_path: filePath
            })
        });

        if (response.ok) {
            // 获取文件名
            const fileName = filePath.split('/').pop();
            
            // 创建下载链接
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            
            // 清理
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const result = await response.json();
            throw new Error(result.error || '下载失败');
        }
    } catch (err) {
        console.error('下载出错:', err);
        alert('下载失败: ' + err.message);
    }
}

// 添加下载进度显示
function showDownloadProgress(total, current) {
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const percent = Math.round((current / total) * 100);
    
    progressBar.style.width = `${percent}%`;
    progressText.textContent = `${percent}%`;
}

// 清除进度显示
function clearProgress() {
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    
    progressBar.style.width = '0';
    progressText.textContent = '0%';
    document.getElementById('uploadProgress').style.display = 'none';
}

// 根据权限显示/隐藏功能按钮
function updateUIByPermissions(connectionId) {
    const server = connectedServers.get(connectionId);
    if (!server) return;

    const uploadZone = document.getElementById('uploadZone');
    if (uploadZone) {
        uploadZone.style.display = server.permissions.includes('write') ? 'block' : 'none';
    }

    // 更新文件列表中的操作按钮
    const files = document.querySelectorAll('.file-item');
    files.forEach(file => {
        const actions = file.querySelector('.file-actions');
        if (actions) {
            const downloadBtn = actions.querySelector('.btn');
            if (downloadBtn && downloadBtn.textContent === '下载') {
                downloadBtn.style.display = server.permissions.includes('read') ? 'inline-block' : 'none';
            }
        }
    });
} 