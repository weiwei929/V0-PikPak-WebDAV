from flask import Flask, request, jsonify, Response, session, redirect
from flask_cors import CORS
import requests
from lxml import etree
import base64
import os
from urllib.parse import unquote
import json
from functools import wraps
import time
import re
import pickle

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Add a decorator for authentication check
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'webdav_credentials' not in session:
            return jsonify({'success': False, 'message': 'Authentication required', 'code': 'AUTH_REQUIRED'})
        return f(*args, **kwargs)
    return decorated

# Add a file path cache for successful file path matches
file_path_cache = {}

# Add a global configuration variable for stream request retries
STREAM_REQUEST_RETRIES = 3  # Number of retries for video stream requests

# Use global variables for directory and file mapping
directory_cache = {}  # Use global variables instead of session storage
file_mapping = {}
next_dir_id = 1
next_file_id = 1

# 引入时间模块，用于控制保存频率
import time

# 添加一个保存控制变量
last_save_time = 0
save_interval = 60  # 每分钟最多保存一次
save_counter = 0
save_threshold = 20  # 累积20个新ID后触发保存检查

# 修复映射保存和加载函数
def save_mappings(force=False):
    """Save ID mappings to a local file with rate limiting"""
    global directory_cache, file_mapping, next_dir_id, next_file_id
    global last_save_time, save_counter
    
    current_time = time.time()
    
    # 如果不是强制保存，应用节流逻辑
    if not force:
        # 累积计数器不足或时间间隔太短则不保存
        save_counter += 1
        if save_counter < save_threshold:
            return
            
        # 检查时间间隔
        if current_time - last_save_time < save_interval:
            return
    
    # 执行保存操作
    try:
        data = {
            'directory_cache': directory_cache,
            'file_mapping': file_mapping,
            'next_dir_id': next_dir_id,
            'next_file_id': next_file_id
        }
        # 使用绝对路径确保写入正确位置
        mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'id_mappings.pkl')
        with open(mapping_file, 'wb') as f:
            pickle.dump(data, f)
        # 更新计时器和计数器
        last_save_time = current_time
        save_counter = 0
        print(f"ID mappings saved: {len(directory_cache)} directories, {len(file_mapping)} files")
    except Exception as e:
        print(f"Error saving ID mappings: {e}")

# 修复映射加载和重定义函数的问题
def load_mappings():
    """Load ID mappings from a local file"""
    global directory_cache, file_mapping, next_dir_id, next_file_id
    try:
        # 使用绝对路径确保读取正确位置
        mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'id_mappings.pkl')
        if not os.path.exists(mapping_file):
            print("No mapping file found, starting with empty mappings")
            return False
            
        with open(mapping_file, 'rb') as f:
            data = pickle.load(f)
            # 确保所有必要的键都存在
            if not all(k in data for k in ['directory_cache', 'file_mapping', 'next_dir_id', 'next_file_id']):
                print("Corrupted mapping file, missing required keys")
                return False
                
            # 使用全局变量，正确赋值
            global directory_cache, file_mapping, next_dir_id, next_file_id
            directory_cache.clear()  # 清空当前字典
            directory_cache.update(data['directory_cache'])  # 更新而不是替换
            
            file_mapping.clear()  # 清空当前字典
            file_mapping.update(data['file_mapping'])  # 更新而不是替换
            
            next_dir_id = data['next_dir_id']
            next_file_id = data['next_file_id']
            
        print(f"ID mappings loaded from file - {len(directory_cache)} dirs, {len(file_mapping)} files")
        return True
    except FileNotFoundError:
        print("No saved mappings found")
        return False
    except Exception as e:
        print(f"Error loading ID mappings: {e}")
        return False

# 修改初始化过程，确保全局变量的正确赋值
def initialize_mappings():
    """Initialize mappings, either from file or from scratch"""
    # 全局变量已在模块顶层定义，不需要在此重新声明
    
    # 尝试从文件加载
    if not load_mappings():  # 如果加载失败
        # 全局变量保持初始状态
        print("Initialized with empty mappings")

# 修复 Helper 函数，确保正确访问全局变量
def get_real_path_from_id(dir_id):
    """根据ID查找实际目录路径"""
    global directory_cache
    for path, id_val in directory_cache.items():
        if id_val == dir_id:
            return path
    return None

def get_real_file_from_id(file_id):
    """根据ID查找实际文件路径"""
    global file_mapping
    for path, id_val in file_mapping.items():
        if id_val == file_id:
            return path
    return None

# 启动时初始化映射
initialize_mappings()

# 修改get_dir_id和get_file_id函数，使用节流后的保存函数
def get_dir_id(path):
    global directory_cache, next_dir_id
    if path not in directory_cache:
        directory_cache[path] = f"dir_{next_dir_id}"
        next_dir_id += 1
        save_mappings()  # 现在这个函数会自己处理节流逻辑
    return directory_cache[path]

def get_file_id(path):
    global file_mapping, next_file_id
    if path not in file_mapping:
        file_mapping[path] = f"file_{next_file_id}"
        next_file_id += 1
        save_mappings()  # 现在这个函数会自己处理节流逻辑
    return file_mapping[path]

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/connect', methods=['POST'])
def connect():
    data = request.json
    url = data.get('url', '').rstrip('/')
    username = data.get('username', '')
    password = data.get('password', '')
    
    # Store credentials in session
    session['webdav_credentials'] = {
        'url': url,
        'username': username,
        'password': password,
        'auth': (username, password)
    }
    
    # Test connection with a PROPFIND request to root
    try:
        response = requests.request(
            method='PROPFIND',
            url=f"{url}/",
            auth=(username, password),
            headers={
                'Depth': '1',
                'Content-Type': 'application/xml'
            },
            data='''<?xml version="1.0" encoding="utf-8" ?>
                <d:propfind xmlns:d="DAV:">
                    <d:prop>
                        <d:displayname/>
                        <d:resourcetype/>
                        <d:getcontenttype/>
                        <d:getcontentlength/>
                    </d:prop>
                </d:propfind>''',
            timeout=10
        )
        
        if response.status_code in [207, 200]:
            return jsonify({
                'success': True, 
                'message': 'Connected successfully',
                'username': username
            })
        else:
            session.pop('webdav_credentials', None)
            return jsonify({
                'success': False, 
                'message': f'Connection failed: {response.status_code}',
                'code': 'CONNECTION_FAILED'
            })
    
    except requests.exceptions.Timeout:
        session.pop('webdav_credentials', None)
        return jsonify({
            'success': False, 
            'message': 'Connection timed out',
            'code': 'TIMEOUT'
        })
    except requests.exceptions.ConnectionError:
        session.pop('webdav_credentials', None)
        return jsonify({
            'success': False, 
            'message': 'Could not connect to server',
            'code': 'CONNECTION_ERROR'
        })
    except Exception as e:
        session.pop('webdav_credentials', None)
        return jsonify({
            'success': False, 
            'message': f'Connection error: {str(e)}',
            'code': 'UNKNOWN_ERROR'
        })

# Add a logout route
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('webdav_credentials', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# Add a status check route
@app.route('/api/status', methods=['GET'])
def status():
    if 'webdav_credentials' in session:
        return jsonify({
            'success': True, 
            'authenticated': True,
            'username': session['webdav_credentials'].get('username', '')
        })
    else:
        return jsonify({
            'success': True, 
            'authenticated': False
        })

@app.route('/api/browse', methods=['GET'])
@require_auth
def browse():
    credentials = session['webdav_credentials']
    
    path_param = request.args.get('path', '/')
    search_query = request.args.get('search', '')
    
    # Check if using ID-based navigation
    if path_param.startswith('dir_'):
        real_path = get_real_path_from_id(path_param)
        if real_path is None:
            return jsonify({
                'success': False,
                'message': 'Invalid directory ID',
                'code': 'INVALID_ID'
            })
        path = real_path
    else:
        path = path_param
        if not path.startswith('/'):
            path = '/' + path
    
    try:
        response = requests.request(
            method='PROPFIND',
            url=f"{credentials['url']}{path}",
            auth=(credentials['username'], credentials['password']),
            headers={
                'Depth': '1',
                'Content-Type': 'application/xml'
            },
            data='''<?xml version="1.0" encoding="utf-8" ?>
                <d:propfind xmlns:d="DAV:">
                    <d:prop>
                        <d:displayname/>
                        <d:resourcetype/>
                        <d:getcontenttype/>
                        <d:getcontentlength/>
                        <d:getlastmodified/>
                    </d:prop>
                </d:propfind>''',
            timeout=15
        )
        
        if response.status_code != 207:
            return jsonify({
                'success': False, 
                'message': f'Failed to browse: {response.status_code}',
                'code': 'BROWSE_FAILED'
            })
        
        # Parse XML response
        root = etree.fromstring(response.content)
        
        # Define namespaces
        namespaces = {
            'd': 'DAV:',
        }
        
        items = []
        
        # Process each response element
        for response_elem in root.findall('.//d:response', namespaces):
            href = response_elem.find('./d:href', namespaces)
            if href is None or not href.text:
                continue
                
            href_text = href.text
            
            # Skip the current directory entry
            if href_text == path or href_text.rstrip('/') == path.rstrip('/'):
                continue
            
            # Extract displayname
            displayname_elem = response_elem.find('.//d:displayname', namespaces)
            displayname = displayname_elem.text if displayname_elem is not None and displayname_elem.text else os.path.basename(unquote(href_text.rstrip('/')))
            
            # Skip if search is active and no match
            if search_query and search_query.lower() not in displayname.lower():
                continue
                
            # Determine if it's a directory
            resourcetype = response_elem.find('.//d:resourcetype', namespaces)
            is_dir = resourcetype is not None and resourcetype.find('.//d:collection', namespaces) is not None
            
            # Get content type for files
            content_type = ''
            if not is_dir:
                content_type_elem = response_elem.find('.//d:getcontenttype', namespaces)
                content_type = content_type_elem.text if content_type_elem is not None and content_type_elem.text else ''
            
            # Get content length for files
            content_length = 0
            if not is_dir:
                length_elem = response_elem.find('.//d:getcontentlength', namespaces)
                content_length = int(length_elem.text) if length_elem is not None and length_elem.text else 0
            
            # Get last modified date
            last_modified = ''
            last_modified_elem = response_elem.find('.//d:getlastmodified', namespaces)
            if last_modified_elem is not None and last_modified_elem.text:
                last_modified = last_modified_elem.text
            
            items.append({
                'displayName': displayname,
                'webdavPath': href_text,
                'isDir': is_dir,
                'contentType': content_type,
                'size': content_length,
                'lastModified': last_modified
            })
        
        # Modify results to use ID-based navigation
        numbered_items = []
        
        # Add parent directory entry if not root
        if path != '/':
            parent_path = os.path.dirname(path)
            if parent_path == '':
                parent_path = '/'
            
            parent_id = get_dir_id(parent_path)
            numbered_items.append({
                'displayName': '..',
                'webdavPath': parent_id,
                'isDir': True,
                'contentType': '',
                'size': 0,
                'lastModified': '',
                'id': '001'
            })
        
        # Add other items with IDs
        item_index = 2
        for item in items:
            if item['isDir']:
                dir_id = get_dir_id(item['webdavPath'])
                numbered_items.append({
                    'displayName': item['displayName'],
                    'webdavPath': dir_id,
                    'isDir': True,
                    'contentType': '',
                    'size': 0,
                    'lastModified': item['lastModified'],
                    'id': f"{item_index:03d}"
                })
            else:
                file_id = get_file_id(item['webdavPath'])
                numbered_items.append({
                    'displayName': item['displayName'],
                    'webdavPath': file_id,
                    'isDir': False,
                    'contentType': item['contentType'],
                    'size': item['size'],
                    'lastModified': item['lastModified'],
                    'id': f"{item_index:03d}"
                })
            item_index += 1
        
        return jsonify({'success': True, 'items': numbered_items, 'path': path_param})
    
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False, 
            'message': 'Request timed out',
            'code': 'TIMEOUT'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error browsing: {str(e)}',
            'code': 'BROWSE_ERROR'
        })

@app.route('/api/stream', methods=['GET'])
@require_auth
def stream():
    credentials = session['webdav_credentials']
    
    file_id = request.args.get('path', '')
    
    if not file_id:
        return Response('No path specified', status=400)
    
    # Check if using ID-based navigation
    if file_id.startswith('file_'):
        real_path = get_real_file_from_id(file_id)
        if real_path is None:
            return Response('Invalid file ID', status=400)
            
        print(f"Using ID-based navigation: {file_id} -> {real_path}")
        
        # Use real path to request file
        for retry in range(STREAM_REQUEST_RETRIES):
            try:
                headers = {}
                range_header = request.headers.get('Range')
                if range_header:
                    headers['Range'] = range_header
                
                file_response = requests.get(
                    f"{credentials['url'].rstrip('/')}{real_path}",
                    auth=(credentials['username'], credentials['password']),
                    headers=headers,
                    stream=True,
                    timeout=30
                )
                
                if file_response.status_code < 400:
                    print(f"File request successful: {file_response.status_code} (attempt {retry+1})")
                    
                    resp_headers = {
                        'Content-Type': file_response.headers.get('Content-Type', 'application/octet-stream'),
                        'Accept-Ranges': 'bytes'
                    }
                    
                    if 'Content-Range' in file_response.headers:
                        resp_headers['Content-Range'] = file_response.headers['Content-Range']
                    
                    if 'Content-Length' in file_response.headers:
                        resp_headers['Content-Length'] = file_response.headers['Content-Length']
                    
                    return Response(
                        file_response.iter_content(chunk_size=2*1024*1024),
                        status=file_response.status_code,
                        headers=resp_headers
                    )
                elif retry == STREAM_REQUEST_RETRIES - 1:
                    return Response(f'File access error: {file_response.status_code}', status=file_response.status_code)
            except requests.exceptions.RequestException as e:
                if retry == STREAM_REQUEST_RETRIES - 1:
                    return Response(f'Streaming error: {str(e)}', status=500)
                time.sleep(0.5)
        
        return Response('Failed to stream file after multiple attempts', status=500)
    else:
        # Legacy support - 为了向后兼容，增加对传统路径格式的支持
        path = file_id
        if not path.startswith('/'):
            path = '/' + path
        
        print(f"Using legacy path format: {path}")
        
        # 简化的路径处理
        try:
            # 简单解码路径，避免过度复杂的处理
            decoded_path = unquote(path)
            print(f"Decoded path: {decoded_path}")
            
            # 直接尝试请求文件
            for retry in range(STREAM_REQUEST_RETRIES):
                try:
                    headers = {}
                    range_header = request.headers.get('Range')
                    if range_header:
                        headers['Range'] = range_header
                    
                    # 直接请求文件
                    file_response = requests.get(
                        f"{credentials['url'].rstrip('/')}{decoded_path}",
                        auth=(credentials['username'], credentials['password']),
                        headers=headers,
                        stream=True,
                        timeout=30
                    )
                    
                    if file_response.status_code < 400:
                        print(f"Legacy file request successful: {file_response.status_code}")
                        
                        # 创建响应头
                        resp_headers = {
                            'Content-Type': file_response.headers.get('Content-Type', 'application/octet-stream'),
                            'Accept-Ranges': 'bytes'
                        }
                        
                        if 'Content-Range' in file_response.headers:
                            resp_headers['Content-Range'] = file_response.headers['Content-Range']
                        
                        if 'Content-Length' in file_response.headers:
                            resp_headers['Content-Length'] = file_response.headers['Content-Length']
                        
                        # 尝试生成ID并缓存此路径
                        try:
                            get_file_id(decoded_path)
                        except:
                            pass
                            
                        return Response(
                            file_response.iter_content(chunk_size=2*1024*1024),
                            status=file_response.status_code,
                            headers=resp_headers
                        )
                        
                    elif retry == STREAM_REQUEST_RETRIES - 1:
                        return Response(f'Legacy file access error: {file_response.status_code}', status=file_response.status_code)
                    
                except requests.exceptions.RequestException as e:
                    if retry == STREAM_REQUEST_RETRIES - 1:
                        return Response(f'Legacy streaming error: {str(e)}', status=500)
                    time.sleep(0.5)
                    
            return Response('Failed to stream legacy file after multiple attempts', status=500)
                
        except Exception as e:
            print(f"Legacy path processing error: {str(e)}")
            return Response(f'Legacy path error: {str(e)}', status=400)

# Update metadata API to use ID-based navigation
@app.route('/api/metadata', methods=['GET'])
@require_auth
def get_metadata():
    credentials = session['webdav_credentials']
    file_id = request.args.get('path', '')
    
    if not file_id:
        return jsonify({'success': False, 'message': 'No file ID specified'})
    
    # Check if using ID-based navigation
    if file_id.startswith('file_'):
        real_path = get_real_file_from_id(file_id)
        if real_path is None:
            return jsonify({'success': False, 'message': 'Invalid file ID'})
            
        path = real_path
    else:
        # Legacy support
        path = file_id
        if not path.startswith('/'):
            path = '/' + path
    
    try:
        response = requests.request(
            method='PROPFIND',
            url=f"{credentials['url']}{path}",
            auth=(credentials['username'], credentials['password']),
            headers={
                'Depth': '0',
                'Content-Type': 'application/xml'
            },
            data='''<?xml version="1.0" encoding="utf-8" ?>
                <d:propfind xmlns:d="DAV:">
                    <d:prop>
                        <d:displayname/>
                        <d:getcontenttype/>
                        <d:getcontentlength/>
                        <d:getlastmodified/>
                    </d:prop>
                </d:propfind>''',
            timeout=10
        )
        
        if response.status_code != 207:
            return jsonify({'success': False, 'message': f'Failed to get metadata: {response.status_code}'})
        
        # Parse XML response
        root = etree.fromstring(response.content)
        
        # Define namespaces
        namespaces = {
            'd': 'DAV:',
        }
        
        # Get the response element
        response_elem = root.find('.//d:response', namespaces)
        if response_elem is None:
            return jsonify({'success': False, 'message': 'No metadata found'})
        
        # Extract displayname
        displayname_elem = response_elem.find('.//d:displayname', namespaces)
        displayname = displayname_elem.text if displayname_elem is not None and displayname_elem.text else os.path.basename(unquote(path.rstrip('/')))
        
        # Get content type
        content_type = ''
        content_type_elem = response_elem.find('.//d:getcontenttype', namespaces)
        content_type = content_type_elem.text if content_type_elem is not None and content_type_elem.text else ''
        
        # Get content length
        content_length = 0
        length_elem = response_elem.find('.//d:getcontentlength', namespaces)
        content_length = int(length_elem.text) if length_elem is not None and length_elem.text else 0
        
        # Get last modified date
        last_modified = ''
        last_modified_elem = response_elem.find('.//d:getlastmodified', namespaces)
        if last_modified_elem is not None and last_modified_elem.text:
            last_modified = last_modified_elem.text
        
        return jsonify({
            'success': True, 
            'metadata': {
                'displayName': displayname,
                'contentType': content_type,
                'size': content_length,
                'lastModified': last_modified,
                'path': file_id  # Return the ID instead of the real path
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error getting metadata: {str(e)}'})

# Update playlist API to use ID-based navigation
@app.route('/api/playlist', methods=['GET'])
@require_auth
def get_playlist():
    credentials = session['webdav_credentials']
    dir_id = request.args.get('path', '/')
    recursive = request.args.get('recursive', 'false').lower() == 'true'
    
    # Handle ID-based navigation
    if dir_id.startswith('dir_'):
        real_path = get_real_path_from_id(dir_id)
        if real_path is None:
            return jsonify({'success': False, 'message': 'Invalid directory ID'})
        path = real_path
    else:
        # Legacy support
        path = dir_id
        if not path.startswith('/'):
            path = '/' + path
    
    # Function to check if a file is a video
    def is_video_file(content_type, filename):
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp']
        return content_type.startswith('video/') or any(filename.lower().endswith(ext) for ext in video_extensions)
    
    # Function to get files from a directory
    def get_files_from_directory(dir_path, depth='1'):
        try:
            response = requests.request(
                method='PROPFIND',
                url=f"{credentials['url']}{dir_path}",
                auth=(credentials['username'], credentials['password']),
                headers={
                    'Depth': depth,
                    'Content-Type': 'application/xml'
                },
                data='''<?xml version="1.0" encoding="utf-8" ?>
                    <d:propfind xmlns:d="DAV:">
                        <d:prop>
                            <d:displayname/>
                            <d:resourcetype/>
                            <d:getcontenttype/>
                            <d:getcontentlength/>
                        </d:prop>
                    </d:propfind>''',
                timeout=20
            )
            
            if response.status_code != 207:
                return []
            
            # Parse XML response
            root = etree.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'd': 'DAV:',
            }
            
            items = []
            subdirs = []
            
            # Process each response element
            for response_elem in root.findall('.//d:response', namespaces):
                href = response_elem.find('./d:href', namespaces)
                if href is None or not href.text:
                    continue
                    
                href_text = href.text
                
                # Skip the current directory entry
                if href_text == dir_path or href_text.rstrip('/') == dir_path.rstrip('/'):
                    continue
                
                # Extract displayname
                displayname_elem = response_elem.find('.//d:displayname', namespaces)
                displayname = displayname_elem.text if displayname_elem is not None and displayname_elem.text else os.path.basename(unquote(href_text.rstrip('/')))
                
                # Determine if it's a directory
                resourcetype = response_elem.find('.//d:resourcetype', namespaces)
                is_dir = resourcetype is not None and resourcetype.find('.//d:collection', namespaces) is not None
                
                if is_dir:
                    if recursive:
                        subdirs.append(href_text)
                else:
                    # Get content type for files
                    content_type = ''
                    content_type_elem = response_elem.find('.//d:getcontenttype', namespaces)
                    content_type = content_type_elem.text if content_type_elem is not None and content_type_elem.text else ''
                    
                    # Get content length for files
                    content_length = 0
                    length_elem = response_elem.find('.//d:getcontentlength', namespaces)
                    content_length = int(length_elem.text) if length_elem is not None and length_elem.text else 0
                    
                    # Check if it's a video file
                    if is_video_file(content_type, displayname):
                        # Generate or get file ID
                        file_id = get_file_id(href_text)
                        
                        items.append({
                            'displayName': displayname,
                            'webdavPath': file_id,  # Use file ID instead of direct path
                            'contentType': content_type,
                            'size': content_length,
                            'id': f"{len(items) + 1:03d}"  # Add sequential ID
                        })
            
            # If recursive, get files from subdirectories
            if recursive:
                for subdir in subdirs:
                    subdir_items = get_files_from_directory(subdir)
                    for i, item in enumerate(subdir_items):
                        item['id'] = f"{len(items) + i + 1:03d}"  # Continue sequential numbering
                    items.extend(subdir_items)
            
            return items
        
        except Exception as e:
            print(f"Error getting files from {dir_path}: {str(e)}")
            return []
    
    # Get files from the specified directory
    files = get_files_from_directory(path, '1' if not recursive else 'infinity')
    
    # Sort files by name
    files.sort(key=lambda x: x['displayName'])
    
    return jsonify({'success': True, 'items': files})

# Function to clear mapping caches (useful for sessions or testing)
@app.route('/api/clear_cache', methods=['POST'])
@require_auth
def clear_cache():
    global directory_cache, file_mapping, next_dir_id, next_file_id
    directory_cache = {}
    file_mapping = {}
    next_dir_id = 1
    next_file_id = 1
    save_mappings(force=True)  # 强制保存
    return jsonify({'success': True, 'message': 'Caches cleared'})

# Save mappings on application exit
import atexit
def force_save_on_exit():
    save_mappings(force=True)
    print("Final mappings saved on exit")
    
atexit.register(force_save_on_exit)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
