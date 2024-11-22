from flask import Blueprint, render_template, request, jsonify, send_file, Response, session
import requests
from datetime import datetime, timezone
import socket
import socks
from urllib.parse import urlparse
import time
import docker
import logging
import os
import tempfile
import subprocess
import json
import threading
from languages import load_language, SUPPORTED_LANGUAGES

# 版本号常量
__version__ = '1.2.0'

# 创建蓝图
image_bp = Blueprint('image', __name__)

# Go服务的地址
DOCKER_SERVICE_URL = 'http://localhost:5526'

# 创建日志记录器
logger = logging.getLogger(__name__)

# 添加全局变量来存储导出进度
export_progress = {
    'percent': 0,
    'exported_size': 0,
    'current_image': None
}
export_lock = threading.Lock()

# 配置文件路径
REGISTRY_CONFIG_FILE = 'registry_config.json'

def get_docker_images():
    """获取Docker镜像信息"""
    try:
        response = requests.get(f'{DOCKER_SERVICE_URL}/images')
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting Docker images: {response.text}")
            return []
    except Exception as e:
        print(f"Error getting Docker images: {e}")
        return []

@image_bp.route('/images')
def image_list():
    """显示Docker镜像列表"""
    # 获取当前语言，默认中文
    current_lang = session.get('language', 'zh_CN')
    lang = load_language(current_lang)
    
    images = get_docker_images()
    return render_template('docker_images.html', 
                         images=images,
                         version=__version__,
                         lang=lang,
                         current_lang=current_lang,
                         supported_languages=SUPPORTED_LANGUAGES)

@image_bp.route('/images/delete', methods=['POST'])
def delete_docker_images():
    """删除选中的Docker镜像"""
    image_ids = request.form.getlist('image_ids')
    
    if not image_ids:
        return jsonify({
            'status': 'error',
            'message': 'No images selected'
        })
    
    try:
        client = docker.from_env()
        deleted = []
        errors = []
        deleted_size = 0
        total_size = 0

        # 计算总大小
        for image_id in image_ids:
            try:
                image = client.images.get(image_id)
                total_size += image.attrs['Size']
            except Exception as e:
                logger.error(f"Error getting image size for {image_id}: {e}")
                errors.append({
                    'operation': 'GET_SIZE',
                    'image_id': image_id,
                    'message': str(e)
                })

        # 删除镜像
        for image_id in image_ids:
            try:
                image = client.images.get(image_id)
                size = image.attrs['Size']
                client.images.remove(image_id, force=True)
                deleted.append(image_id)
                deleted_size += size
                logger.info(f"Successfully deleted image: {image_id}")
            except Exception as e:
                logger.error(f"Error deleting image {image_id}: {e}")
                errors.append({
                    'operation': 'DELETE',
                    'image_id': image_id,
                    'message': str(e)
                })

        status = 'success'
        if errors:
            status = 'partial' if deleted else 'error'

        return jsonify({
            'status': status,
            'deleted': deleted,
            'errors': errors,
            'total_count': len(image_ids),
            'deleted_size': deleted_size,
            'total_size': total_size
        })

    except Exception as e:
        logger.error(f"Unexpected error during image deletion: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@image_bp.route('/images/push', methods=['POST'])
def push_docker_images():
    """推送Docker镜像"""
    try:
        data = request.json
        registry_type = data.get('registry_type', 'dockerhub')
        credentials = data.get('credentials', {})
        tag_format = data.get('tag_format')
        image_ids = data.get('image_ids', [])
        
        if not image_ids or not tag_format or not credentials:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            })
            
        client = docker.from_env()
        
        # 设置代理（如果有）
        proxy_type = data.get('proxy_type')
        proxy_server = data.get('proxy_server')
        original_env = {}
        
        try:
            if proxy_type and proxy_server:
                # 保存原始环境变量
                for env_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']:
                    if env_var in os.environ:
                        original_env[env_var] = os.environ[env_var]
                
                # 设置代理环境变量
                if proxy_type == 'socks5':
                    # 对于SOCKS5代理，使用 ALL_PROXY
                    proxy_url = f'socks5h://{proxy_server}'  # 使用 socks5h 而不是 socks5
                    os.environ['ALL_PROXY'] = proxy_url
                    os.environ['all_proxy'] = proxy_url
                else:
                    # 对于HTTP代理
                    proxy_url = proxy_server if proxy_server.startswith(('http://', 'https://')) else f'http://{proxy_server}'
                    os.environ['HTTP_PROXY'] = proxy_url
                    os.environ['HTTPS_PROXY'] = proxy_url
                    os.environ['http_proxy'] = proxy_url
                    os.environ['https_proxy'] = proxy_url
                
                # 测试代理连接 - 使用实际的 Docker Registry 地址进行测试
                try:
                    if registry_type == 'dockerhub':
                        test_urls = [
                            'https://registry-1.docker.io/v2/',  # Docker Hub 实际的 registry 地址
                            'https://index.docker.io/v1/',       # Docker Hub 认证地址
                            'https://auth.docker.io'             # Docker Hub 认证服务地址
                        ]
                    else:
                        test_urls = [f'https://{credentials.get("region")}']
                    
                    # 配置 requests 会话
                    session = requests.Session()
                    if proxy_type == 'socks5':
                        parsed = urlparse(proxy_server)
                        proxy_host = parsed.hostname
                        proxy_port = parsed.port or 1080
                        session.proxies = {
                            'http': f'socks5h://{proxy_host}:{proxy_port}',
                            'https': f'socks5h://{proxy_host}:{proxy_port}'
                        }
                    else:
                        session.proxies = {
                            'http': proxy_url,
                            'https': proxy_url
                        }
                    
                    # 测试所有相关 URL
                    success = False
                    for test_url in test_urls:
                        try:
                            response = session.get(test_url, timeout=10, verify=False)
                            if response.status_code in [200, 301, 302, 401]:  # 401 是正常的，因为需要认证
                                success = True
                                break
                        except Exception:
                            continue
                    
                    if not success:
                        raise Exception('无法连接到 Docker Registry')
                        
                except Exception as e:
                    raise Exception(f'代理服务器连接失败: {str(e)}')
            
            # 处理阿里云器服务
            if registry_type == 'aliyun':
                region = credentials.get('region')
                namespace = credentials.get('namespace')
                username = credentials.get('username')
                password = credentials.get('password')
                
                # 登录阿里云容器镜像服务
                login_cmd = f'docker login {region} -u {username} -p {password}'
                result = subprocess.run(login_cmd.split(), 
                                     capture_output=True, 
                                     text=True, 
                                     env=os.environ)  # 使用当前环境变量（包含代理设置）
                if result.returncode != 0:
                    raise Exception(f"登录失败: {result.stderr}")
                
                for image_id in image_ids:
                    image = client.images.get(image_id)
                    # 替换标签格式中的变量
                    new_tag = tag_format.format(
                        region=region,
                        namespace=namespace,
                        imagename=image.tags[0].split(':')[0].split('/')[-1] if image.tags else 'unnamed',
                        version='latest'
                    )
                    # 打标签
                    image.tag(new_tag)
                    # 推送镜像
                    for line in client.images.push(new_tag, stream=True):
                        print(line.decode())
                        
            # 处理DockerHub
            else:
                username = credentials.get('username')
                password = credentials.get('password')
                
                # 使用 echo 和管道来安全地传递密码
                login_cmd = ['docker', '--debug', 'login', '-u', username, '--password-stdin']
                login_process = subprocess.Popen(
                    login_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=os.environ
                )
                
                # 通过标准输入传递密码
                stdout, stderr = login_process.communicate(input=password + '\n')
                
                if login_process.returncode != 0:
                    raise Exception(f"登录失败: {stderr}")
                
                for image_id in image_ids:
                    image = client.images.get(image_id)
                    # 替换标签格式中的变量
                    new_tag = tag_format.format(
                        username=username,
                        imagename=image.tags[0].split(':')[0].split('/')[-1] if image.tags else 'unnamed',
                        version='latest'
                    )
                    # 打标签
                    image.tag(new_tag)
                    # 推送镜像
                    push_cmd = ['docker', '--debug', 'push', new_tag]
                    push_result = subprocess.run(push_cmd, 
                                              capture_output=True, 
                                              text=True, 
                                              env=os.environ)
                    
                    if push_result.returncode != 0:
                        raise Exception(f"推送失败: {push_result.stderr}")
            
            return jsonify({
                'status': 'success',
                'message': '镜像推送成功'
            })
            
        finally:
            # 恢复原始环境变量
            for env_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                if env_var in original_env:
                    os.environ[env_var] = original_env[env_var]
                else:
                    os.environ.pop(env_var, None)
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def test_proxy_connection(proxy_type, proxy_server):
    """测试代理连接"""
    try:
        # 解析代理服务器地址
        parsed = urlparse(proxy_server)
        proxy_host = parsed.hostname
        proxy_port = parsed.port or (80 if proxy_type == 'http' else 1080)

        # 创建测试连接
        if proxy_type == 'http':
            # 对于HTTP代理，使用requests直接测试
            proxies = {
                'http': proxy_server,
                'https': proxy_server
            }
            # 先测试基本连接
            start_time = time.time()
            response = requests.get('http://www.google.com', 
                                 proxies=proxies, 
                                 timeout=5,
                                 verify=False)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return True, f"代理连接成功！响应时间: {response_time:.2f}秒"
            else:
                return False, f"代理服务器响应异常，状态码: {response.status_code}"

        elif proxy_type == 'socks5':
            # 对于SOCKS5代理，使用socket直接测试
            sock = socks.socksocket()
            sock.set_proxy(
                proxy_type=socks.SOCKS5,
                addr=proxy_host,
                port=proxy_port
            )
            sock.settimeout(5)
            
            # 测试连接到一个常用服务
            start_time = time.time()
            sock.connect(('www.google.com', 80))
            response_time = time.time() - start_time
            
            sock.close()
            return True, f"代理连接成功！响应时间: {response_time:.2f}秒"

    except requests.exceptions.RequestException as e:
        return False, f"HTTP代理连接失败: {str(e)}"
    except socks.ProxyConnectionError as e:
        return False, f"SOCKS5代理连接失败: {str(e)}"
    except socket.timeout:
        return False, "代理连接超时"
    except Exception as e:
        return False, f"测试过程出错: {str(e)}"

@image_bp.route('/test-proxy', methods=['POST'])
def test_proxy():
    """测试代理服务器连接"""
    try:
        data = request.json
        proxy_type = data.get('proxy_type')
        proxy_server = data.get('proxy_server')

        if not proxy_type or not proxy_server:
            return jsonify({
                'status': 'error',
                'error': '代理配置不完整'
            })

        # 测试代理连
        success, message = test_proxy_connection(proxy_type, proxy_server)

        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'error': message
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@image_bp.route('/upload', methods=['POST'])
def upload_docker_image():
    upload_type = request.form.get('upload_type')
    image_name = request.form.get('image_name', '')
    tag = request.form.get('tag', 'latest')
    
    try:
        client = docker.from_env()
        temp_file = None
        
        if upload_type == 'file':
            if 'image' not in request.files:
                return jsonify({'status': 'error', 'message': '没有选择文件'})
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'status': 'error', 'message': '没有选择文件'})
            
            # 保存文件到临时目录
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tar')
            file.save(temp_file.name)
            file_path = temp_file.name
            
            try:
                # 加载镜像
                with open(file_path, 'rb') as f:
                    images = client.images.load(f)
                
                # 获取加载的镜像信息
                loaded_images = []
                for image in images:
                    image_info = {
                        'id': image.id,
                        'tags': image.tags,
                        'size': image.attrs['Size'],
                        'created': image.attrs['Created']
                    }
                    loaded_images.append(image_info)
                    
                    # 如果提供了自定义名称和标签，则添加新标签
                    if image_name:
                        image.tag(image_name, tag)
                
                return jsonify({
                    'status': 'success',
                    'message': f'成功加载 {len(loaded_images)} 个镜像',
                    'images': loaded_images
                })
                
            except Exception as e:
                # 如果加载失败，尝试使用 docker load 命令
                try:
                    result = subprocess.run(['docker', 'load', '-i', file_path], 
                                         capture_output=True, 
                                         text=True)
                    if result.returncode == 0:
                        # 如果提供了自定义名称和标签，找到新加载的镜像并添加标签
                        if image_name:
                            # 获取所有镜像并到最新加载的
                            images = client.images.list()
                            if images:
                                latest_image = images[0]
                                latest_image.tag(image_name, tag)
                        
                        return jsonify({
                            'status': 'success',
                            'message': '镜像加载成功',
                            'command_output': result.stdout
                        })
                    else:
                        raise Exception(f"Docker load failed: {result.stderr}")
                except Exception as load_error:
                    return jsonify({
                        'status': 'error',
                        'message': f'镜像加载失败: {str(load_error)}'
                    })
                    
        elif upload_type == 'url':
            url = request.form.get('image_url')
            if not url:
                return jsonify({'status': 'error', 'message': '未提供URL'})
            
            # 下载文件到临时目录
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tar')
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(temp_file.name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 加载镜像并添加自定义标签
            with open(temp_file.name, 'rb') as f:
                images = client.images.load(f)
                if image_name and images:
                    images[0].tag(image_name, tag)
            
            return jsonify({
                'status': 'success',
                'message': '镜像加载成功'
            })
            
    except requests.exceptions.RequestException as e:
        return jsonify({'status': 'error', 'message': f'下载文件失败: {str(e)}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@image_bp.route('/pull', methods=['POST'])
def pull_docker_image():
    try:
        data = request.json
        
        # 处理远程URL下载
        if 'image_url' in data:
            url = data['image_url']
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar') as temp_file:
                # 下载文件
                response = requests.get(url, stream=True)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                
                # 加载镜像
                client = docker.from_env()
                with open(temp_file.name, 'rb') as f:
                    image = client.images.load(f)[0]
                
                # 清理临时文件
                os.unlink(temp_file.name)
                
                return jsonify({
                    'status': 'success',
                    'message': '镜像拉取成功',
                    'image_id': image.id
                })
        
        # 处理镜像仓库拉取
        else:
            registry_url = data.get('registry_url', '').strip()
            image_name = data.get('image_name')
            tag = data.get('tag', 'latest')
            
            if not image_name:
                return jsonify({
                    'status': 'error',
                    'message': '镜像名称不能为空'
                })
            
            # 如果提供了registry_url，拼接完整的镜像名称
            if registry_url:
                image_name = f"{registry_url}/{image_name}"
            
            # 拉取镜像
            client = docker.from_env()
            image = client.images.pull(image_name, tag=tag)
            
            return jsonify({
                'status': 'success',
                'message': '镜拉取成功',
                'image_id': image.id
            })
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'下载失败: {str(e)}'
        })
    except docker.errors.ImageNotFound:
        return jsonify({
            'status': 'error',
            'message': '镜像未找到'
        })
    except docker.errors.APIError as e:
        return jsonify({
            'status': 'error',
            'message': f'Docker API错误: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }) 

def update_export_progress(percent, exported_size, current_image):
    global export_progress
    with export_lock:
        export_progress['percent'] = percent
        export_progress['exported_size'] = exported_size
        export_progress['current_image'] = current_image

@image_bp.route('/export/progress')
def export_progress():
    def generate():
        while True:
            with export_lock:
                # 发送当前进度
                yield f"data: {json.dumps(export_progress)}\n\n"
            time.sleep(0.5)  # 每500ms更新一次
    
    return Response(generate(), mimetype='text/event-stream')

@image_bp.route('/export', methods=['POST'])
def export_docker_images():
    """导出选中的Docker镜像"""
    image_ids = request.form.getlist('image_ids')
    
    if not image_ids:
        return jsonify({
            'status': 'error',
            'message': '没有选择镜像'
        })
    
    try:
        client = docker.from_env()
        # 获取选中镜像的标签信息
        image_tags = []
        for image_id in image_ids:
            try:
                image = client.images.get(image_id)
                tags = image.tags[0] if image.tags else image_id[:12]
                image_tags.append(tags.replace('/', '_').replace(':', '_'))
            except Exception as e:
                logger.error(f"Error getting image {image_id}: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'获取镜像信息失败: {str(e)}'
                })
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tar')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # 使用 docker save 命令导出镜像
            cmd = ['docker', 'save', '-o', temp_path] + image_ids
            
            # 执行导命令
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 验证导出的文件
            if not os.path.exists(temp_path):
                raise Exception("Export file was not created")
                
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                raise Exception("Export file is empty")
            
            # 使用标签作为文件名
            filename = f"docker_images_{'_'.join(image_tags)}.tar"
            
            # 发文件
            response = send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/x-tar'
            )
            
            # 添加清理回调
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file: {e}")
            
            return response
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker save command failed: {e.stderr}")
            return jsonify({
                'status': 'error',
                'message': f'导出失败: {e.stderr}'
            })
        except Exception as e:
            logger.error(f"Error during export: {e}")
            return jsonify({
                'status': 'error',
                'message': f'导出失败: {str(e)}'
            })
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def load_registry_config():
    """加载镜像源配置"""
    try:
        if os.path.exists(REGISTRY_CONFIG_FILE):
            with open(REGISTRY_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {'registry': None}
    except Exception as e:
        logger.error(f"Error loading registry config: {e}")
        return {'registry': None}

def save_registry_config_file(config):
    """保存镜像源配置到文件"""
    try:
        with open(REGISTRY_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        logger.error(f"Error saving registry config: {e}")
        return False

@image_bp.route('/registry/config', methods=['GET'])
def get_registry_config():
    """获取当前镜像源配置"""
    config = load_registry_config()
    return jsonify({
        'status': 'success',
        'registry': config.get('registry')
    })

@image_bp.route('/registry/save_config', methods=['POST'])
def save_registry_config():
    """保存镜像源配置"""
    try:
        data = request.json
        registry = data.get('registry', '').strip()
        
        if registry:
            # 验证镜像源地址格式
            if not registry.startswith(('http://', 'https://')):
                return jsonify({
                    'status': 'error',
                    'message': '镜像源地址必须以 http:// 或 https:// 开头'
                })
        
        if save_registry_config_file({'registry': registry}):
            return jsonify({
                'status': 'success',
                'message': '配置保存成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '配置保存失败'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@image_bp.route('/registry/test', methods=['POST'])
def test_registry():
    """测试镜像源连接"""
    try:
        data = request.json
        registry = data.get('registry', '').strip()
        
        if not registry:
            return jsonify({
                'status': 'error',
                'error': '镜像源地址不能为空'
            })
            
        # 测试连接
        try:
            # 尝试获取 v2 API
            test_url = f"{registry.rstrip('/')}/v2/"
            
            # 配置请求会话
            session = requests.Session()
            session.verify = False  # 禁用 SSL 验证
            session.headers.update({
                'User-Agent': 'Docker-Client/24.0.7 (linux)'  # 模拟 Docker 客户端
            })
            
            # 首先试基本连接
            start_time = time.time()
            response = session.get(test_url, timeout=10)
            response_time = time.time() - start_time
            
            # 检查响应状态
            if response.status_code in [200, 401]:  # 401 也是正常的，因为需要认证
                # 尝试获取 Docker-Distribution-Api-Version 头
                api_version = response.headers.get('Docker-Distribution-Api-Version', 'unknown')
                registry_version = response.headers.get('Server', 'unknown')
                
                return jsonify({
                    'status': 'success',
                    'message': (
                        f'响应时间: {response_time:.2f}秒\n'
                        f'API版本: {api_version}\n'
                        f'服务器: {registry_version}'
                    )
                })
            else:
                # 尝试其他常见的 Docker Registry 路径
                alternate_paths = ['/v1/_ping', '/v2/_catalog']
                for path in alternate_paths:
                    try:
                        alt_url = f"{registry.rstrip('/')}{path}"
                        alt_response = session.get(alt_url, timeout=5)
                        if alt_response.status_code in [200, 401]:
                            return jsonify({
                                'status': 'success',
                                'message': f'镜像源可用 (通过 {path})\n响应时间: {response_time:.2f}秒'
                            })
                    except Exception:
                        continue
                
                return jsonify({
                    'status': 'error',
                    'error': (
                        f'服务器返回状态码: {response.status_code}\n'
                        f'响应内容: {response.text[:200]}'  # 只显示前200个字符
                    )
                })
                
        except requests.exceptions.SSLError as e:
            return jsonify({
                'status': 'error',
                'error': f'SSL证书验证失败: {str(e)}\n建议使用 HTTPS 或检查证书配置'
            })
        except requests.exceptions.ConnectionError as e:
            return jsonify({
                'status': 'error',
                'error': f'连接失败: {str(e)}\n请检查地址是否正确或网络是否可用'
            })
        except requests.exceptions.Timeout as e:
            return jsonify({
                'status': 'error',
                'error': f'连接超时: {str(e)}\n请检查网络状况或镜像源响应时间'
            })
        except requests.exceptions.RequestException as e:
            return jsonify({
                'status': 'error',
                'error': f'请求失败: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

# 添加修改镜像标签的路由
@image_bp.route('/tag', methods=['POST'])
def tag_image():
    """修改镜像标签"""
    try:
        data = request.json
        image_id = data.get('image_id')
        new_tag = data.get('new_tag')
        
        if not image_id or not new_tag:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            })
        
        client = docker.from_env()
        image = client.images.get(image_id)
        
        # 解析新标签
        repository, tag = new_tag.split(':') if ':' in new_tag else (new_tag, 'latest')
        
        try:
            # 添加新标签
            success = image.tag(repository, tag)
            if not success:
                raise Exception("标签添加失败")
            
            # 获取更新后的镜像信息
            updated_image = client.images.get(image_id)
            
            return jsonify({
                'status': 'success',
                'message': '标签修改成功',
                'new_tag': f"{repository}:{tag}",
                'all_tags': updated_image.tags
            })
            
        except Exception as e:
            logger.error(f"Error tagging image {image_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': f'标签修改失败: {str(e)}'
            })
            
    except docker.errors.ImageNotFound:
        return jsonify({
            'status': 'error',
            'message': '镜像不存在'
        })
    except Exception as e:
        logger.error(f"Unexpected error in tag_image: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@image_bp.route('/tag/delete', methods=['POST'])
def delete_tag():
    """删除镜像标签"""
    try:
        data = request.json
        image_id = data.get('image_id')
        tag = data.get('tag')
        
        if not image_id or not tag:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            })
        
        client = docker.from_env()
        image = client.images.get(image_id)
        
        # 确保镜像至少有两个标签才允许删除
        if len(image.tags) <= 1:
            return jsonify({
                'status': 'error',
                'message': '不能删除镜像的最后一个标签'
            })
        
        try:
            # 删除标签
            client.images.remove(tag, force=False)
            
            # 获取更新后的镜像信息
            updated_image = client.images.get(image_id)
            
            return jsonify({
                'status': 'success',
                'message': '标签删除成功',
                'remaining_tags': updated_image.tags
            })
            
        except Exception as e:
            logger.error(f"Error removing tag {tag} from image {image_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': f'标签删除失败: {str(e)}'
            })
            
    except docker.errors.ImageNotFound:
        return jsonify({
            'status': 'error',
            'message': '镜像不存在'
        })
    except Exception as e:
        logger.error(f"Unexpected error in delete_tag: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }) 