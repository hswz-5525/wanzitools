from flask import Blueprint, render_template, request, jsonify, abort, session
import os
import yaml
import logging
import subprocess
import json
from languages import load_language, SUPPORTED_LANGUAGES
import requests
import time
from datetime import datetime
import re
import shlex

# 创建蓝图
compose_bp = Blueprint('compose', __name__)

# 创建日志目录
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 配置日志记录器
def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器，按日期记录日志
    log_file = os.path.join(LOG_DIR, f'compose_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化日志记录器
logger = setup_logger('compose_manager')

def log_operation(operation, project_name, status, message=''):
    """记录操作日志"""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'operation': operation,
        'project': project_name,
        'status': status,
        'message': message
    }
    
    if status == 'success':
        logger.info(f"{operation} - {project_name} - {message}")
    else:
        logger.error(f"{operation} - {project_name} - {message}")
    
    # 保存到操作历史文件
    history_file = os.path.join(LOG_DIR, 'operation_history.json')
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append(log_entry)
        
        # 只保留最近1000条记录
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving operation history: {e}")

def load_config():
    """加载配置文件"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return {}

# 从配置文件获取 Docker Compose 项目目录
config = load_config()
COMPOSE_ROOT = config.get('compose_root', '/mnt/nas/docker')

# 添加配置文件路径
REGISTRY_CONFIG_FILE = 'compose_registry_config.json'

def load_registry_config():
    """加载镜像源配置"""
    try:
        if os.path.exists(REGISTRY_CONFIG_FILE):
            with open(REGISTRY_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {'registries': []}
    except Exception as e:
        logger.error(f"Error loading registry config: {e}")
        return {'registries': []}

def save_registry_config_file(config):
    """保存镜像源配置到文件"""
    try:
        with open(REGISTRY_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        logger.error(f"Error saving registry config: {e}")
        return False

def get_compose_projects():
    """扫描并获取所有 Docker Compose 项目"""
    projects = []
    try:
        logger.info(f"Scanning compose projects in {COMPOSE_ROOT}")
        # 遍第一层目录
        for item in os.listdir(COMPOSE_ROOT):
            project_path = os.path.join(COMPOSE_ROOT, item)
            if os.path.isdir(project_path):
                # 查找 docker-compose.yml 或 docker-compose.yaml
                compose_file = None
                env_file = None
                for filename in os.listdir(project_path):
                    if filename in ['docker-compose.yml', 'docker-compose.yaml']:
                        compose_file = os.path.join(project_path, filename)
                    elif filename == '.env':
                        env_file = os.path.join(project_path, filename)
                
                if compose_file:
                    # 读取 compose 文件内容
                    try:
                        with open(compose_file, 'r', encoding='utf-8') as f:
                            compose_content = f.read()
                            # 验证 YAML 格式并获取服务数量
                            compose_data = yaml.safe_load(compose_content)
                            container_count = len(compose_data.get('services', {}))
                    except Exception as e:
                        logger.error(f"Error reading compose file {compose_file}: {e}")
                        compose_content = f"Error: {str(e)}"
                        container_count = 0
                    
                    # 读取 .env 文件内容
                    env_content = None
                    if env_file and os.path.exists(env_file):
                        try:
                            with open(env_file, 'r', encoding='utf-8') as f:
                                env_content = f.read()
                        except Exception as e:
                            logger.error(f"Error reading .env file {env_file}: {e}")
                            env_content = f"Error: {str(e)}"
                    
                    # 获取项目状态和容器数量
                    status, running_containers = check_project_status(item)
                    
                    # 获取创建时间（使用目录的创建时间）
                    created_time = os.path.getctime(project_path)
                    
                    projects.append({
                        'name': item,
                        'path': project_path,
                        'compose_file': compose_file,
                        'compose_content': compose_content,
                        'env_file': env_file,
                        'env_content': env_content,
                        'status': status,
                        'container_count': container_count,
                        'running_containers': running_containers,
                        'created_time': created_time,
                        'relative_path': os.path.relpath(project_path, COMPOSE_ROOT)
                    })
    except Exception as e:
        error_msg = f"Error scanning compose projects: {e}"
        logger.error(error_msg)
        log_operation('scan_projects', 'all', 'error', error_msg)
    
    return sorted(projects, key=lambda x: x['name'])

def check_project_status(project_name):
    """检查项目运行状态和容器数量"""
    try:
        result = subprocess.run(
            ['docker', 'compose', 'ps', '--format', 'json'],
            cwd=os.path.join(COMPOSE_ROOT, project_name),
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            stdout_fixed = result.stdout.strip().replace('}\n{', '},{')
            containers = json.loads(f"[{stdout_fixed}]")
            running_count = sum(1 for c in containers if c.get('State') == 'running')
            return 'running' if running_count > 0 else 'stopped', running_count
        return 'stopped', 0
    except Exception as e:
        logger.error(f"Error checking project status: {e}")
        return 'unknown', 0

@compose_bp.route('/')
def index():
    """显示项目列表"""
    # 获取当前语言，默认中文
    current_lang = session.get('language', 'zh_CN')
    lang = load_language(current_lang)
    
    projects = get_compose_projects()
    return render_template('compose_manager.html', 
                         projects=projects,
                         lang=lang,
                         current_lang=current_lang,
                         supported_languages=SUPPORTED_LANGUAGES)

@compose_bp.route('/save', methods=['POST'])
def save_file():
    """保存文件内容"""
    try:
        data = request.json
        project_name = data.get('project')
        file_type = data.get('type')  # 'compose' 或 'env'
        content = data.get('content')
        
        if not all([project_name, file_type, content]):
            return jsonify({'status': 'error', 'message': '缺少必要参数'})
        
        project_path = os.path.join(COMPOSE_ROOT, project_name)
        if not os.path.exists(project_path):
            return jsonify({'status': 'error', 'message': '项目不存在'})
        
        # 确定要保存的文件路径
        if file_type == 'compose':
            file_path = os.path.join(project_path, 'docker-compose.yml')
            # 验证 YAML 格式
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                return jsonify({'status': 'error', 'message': f'YAML格式错误: {str(e)}'})
        else:
            file_path = os.path.join(project_path, '.env')
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'status': 'success', 'message': '保存成功'})
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@compose_bp.route('/deploy', methods=['POST'])
def deploy_projects():
    """部署选中的项目"""
    try:
        data = request.json
        projects = data.get('projects', [])
        action = data.get('action')  # 'up' 或 'down'
        
        if not projects or not action:
            return jsonify({'status': 'error', 'message': '缺少必要参数'})
        
        results = []
        for project in projects:
            project_path = os.path.join(COMPOSE_ROOT, project)
            if not os.path.exists(project_path):
                error_msg = '项目不存在'
                log_operation(f'deploy_{action}', project, 'error', error_msg)
                results.append({
                    'project': project,
                    'status': 'error',
                    'message': error_msg,
                    'logs': []
                })
                continue
            
            try:
                cmd = ['docker', 'compose']
                if action == 'up':
                    cmd.extend(['up', '-d'])
                else:
                    cmd.extend(['down'])
                
                logger.info(f"Executing command for {project}: {' '.join(cmd)}")
                
                # 执行命令并实时捕获输出
                process = subprocess.Popen(
                    cmd,
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 收集日志
                logs = []
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        log_line = output.strip()
                        logs.append(log_line)
                        logger.info(f"{project} - {log_line}")
                
                # 获取任剩余输出
                stdout, stderr = process.communicate()
                if stdout:
                    for line in stdout.strip().split('\n'):
                        if line:
                            logs.append(line)
                            logger.info(f"{project} - {line}")
                if stderr:
                    for line in stderr.strip().split('\n'):
                        if line:
                            logs.append(line)
                            logger.error(f"{project} - {line}")
                
                if process.returncode == 0:
                    success_msg = f'项目{action}成功'
                    log_operation(f'deploy_{action}', project, 'success', success_msg)
                    results.append({
                        'project': project,
                        'status': 'success',
                        'message': success_msg,
                        'logs': logs
                    })
                else:
                    error_msg = f'项目{action}失败'
                    log_operation(f'deploy_{action}', project, 'error', error_msg)
                    results.append({
                        'project': project,
                        'status': 'error',
                        'message': error_msg,
                        'logs': logs
                    })
                    
            except Exception as e:
                error_msg = str(e)
                log_operation(f'deploy_{action}', project, 'error', error_msg)
                results.append({
                    'project': project,
                    'status': 'error',
                    'message': error_msg,
                    'logs': []
                })
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in deploy_projects: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        })

@compose_bp.route('/registry/config', methods=['GET'])
def get_registry_config():
    """获取当前镜像源配置"""
    config = load_registry_config()
    docker_mirrors = get_current_docker_registry()
    return jsonify({
        'status': 'success',
        'registries': config.get('registries', []),
        'docker_mirrors': docker_mirrors
    })

@compose_bp.route('/registry/save_config', methods=['POST'])
def save_registry_config():
    """保存镜像源配置"""
    try:
        data = request.json
        registries = data.get('registries', [])
        
        # 验证每个镜像源地址
        for registry in registries:
            if not registry.startswith(('http://', 'https://')):
                return jsonify({
                    'status': 'error',
                    'message': f'镜像源地址必须以 http:// 或 https:// 开头: {registry}'
                })
        
        if save_registry_config_file({'registries': registries}):
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

@compose_bp.route('/registry/test', methods=['POST'])
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
            
        # 测
        try:
            test_url = f"{registry.rstrip('/')}/v2/"
            session = requests.Session()
            session.verify = False
            session.headers.update({
                'User-Agent': 'Docker-Client/24.0.7 (linux)'
            })
            
            start_time = time.time()
            response = session.get(test_url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code in [200, 401]:
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
                    'error': f'服务器返回状态码: {response.status_code}'
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

@compose_bp.route('/projects/status')
def get_projects_status():
    """获取所有项目的状态"""
    try:
        projects = get_compose_projects()
        status_info = [{
            'name': project['name'],
            'status': project['status'],
            'running_containers': project['running_containers'],
            'container_count': project['container_count']
        } for project in projects]
        
        return jsonify({
            'status': 'success',
            'projects': status_info
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }) 

@compose_bp.route('/root_path', methods=['POST'])
def save_root_path():
    """保存目录路径"""
    try:
        data = request.json
        new_path = data.get('path', '').strip()
        
        if not new_path:
            return jsonify({
                'status': 'error',
                'message': '路径不能为空'
            })
        
        # 验证路径是否存在且可访问
        if not os.path.exists(new_path):
            return jsonify({
                'status': 'error',
                'message': '路径不存在'
            })
        
        if not os.path.isdir(new_path):
            return jsonify({
                'status': 'error',
                'message': '路径必须是目录'
            })
        
        # 更新配置文件
        config = load_config()
        config['compose_root'] = new_path
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)
        
        # 更新全局变量
        global COMPOSE_ROOT
        COMPOSE_ROOT = new_path
        
        return jsonify({
            'status': 'success',
            'message': '根目录更新成功',
            'new_path': new_path
        })
        
    except Exception as e:
        logger.error(f"Error saving root path: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@compose_bp.route('/delete', methods=['POST'])
def delete_projects():
    """删除选中的项目"""
    try:
        data = request.json
        projects = data.get('projects', [])
        
        if not projects:
            return jsonify({
                'status': 'error',
                'message': '未选择要删除的项目'
            })
        
        results = []
        for project in projects:
            project_path = os.path.join(COMPOSE_ROOT, project)
            try:
                if os.path.exists(project_path):
                    # 1. 先停止项目
                    try:
                        stop_cmd = ['docker', 'compose', 'down']
                        stop_result = subprocess.run(
                            stop_cmd,
                            cwd=project_path,
                            capture_output=True,
                            text=True
                        )
                        if stop_result.returncode != 0:
                            raise Exception(f"停止项目失败: {stop_result.stderr}")
                    except Exception as e:
                        logger.error(f"Error stopping project {project}: {e}")
                        # 继续执行，因为项目可能本来就没在运行
                    
                    # 2. 清理相关镜像
                    try:
                        # 获取项目使用的镜像
                        with open(os.path.join(project_path, 'docker-compose.yml'), 'r') as f:
                            compose_config = yaml.safe_load(f)
                        
                        # 收集所有服务使用的镜像
                        images = []
                        for service in compose_config.get('services', {}).values():
                            if 'image' in service:
                                images.append(service['image'])
                        
                        # 尝试删除镜像
                        for image in images:
                            try:
                                remove_cmd = ['docker', 'rmi', image]
                                subprocess.run(
                                    remove_cmd,
                                    capture_output=True,
                                    text=True
                                )
                            except Exception as e:
                                logger.error(f"Error removing image {image}: {e}")
                                # 继续执行，因为有些镜像可能被其他项目使用
                    except Exception as e:
                        logger.error(f"Error cleaning up images for project {project}: {e}")
                        # 继续执行删除项目
                    
                    # 3. 删除项目目录
                    import shutil
                    shutil.rmtree(project_path)
                    results.append({
                        'project': project,
                        'status': 'success'
                    })
                else:
                    results.append({
                        'project': project,
                        'status': 'error',
                        'message': '项目不存在'
                    })
            except Exception as e:
                results.append({
                    'project': project,
                    'status': 'error',
                    'message': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error deleting projects: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }) 

@compose_bp.route('/logs')
def view_logs():
    """查看操作日志"""
    try:
        # 读取操作历史
        history_file = os.path.join(LOG_DIR, 'operation_history.json')
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # 获取日志文件列表
        log_files = []
        for file in os.listdir(LOG_DIR):
            if file.startswith('compose_') and file.endswith('.log'):
                log_files.append(file)
        
        # 获取当前语言
        current_lang = session.get('language', 'zh_CN')
        lang = load_language(current_lang)
        
        return render_template(
            'compose_logs.html',
            history=history,
            log_files=sorted(log_files, reverse=True),
            lang=lang,
            current_lang=current_lang,
            supported_languages=SUPPORTED_LANGUAGES
        )
        
    except Exception as e:
        logger.error(f"Error viewing logs: {e}")
        return str(e), 500

@compose_bp.route('/logs/file/<filename>')
def get_log_file(filename):
    """获取日志文件内容"""
    try:
        log_path = os.path.join(LOG_DIR, filename)
        if not os.path.exists(log_path):
            return '日志文件不存在', 404
            
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
        
    except Exception as e:
        logger.error(f"Error reading log file {filename}: {e}")
        return str(e), 500

@compose_bp.route('/cleanup', methods=['POST'])
def cleanup_project():
    """停止项目并清理相关镜像"""
    try:
        data = request.json
        project_name = data.get('project')
        
        if not project_name:
            return jsonify({
                'status': 'error',
                'message': '未指定项目名称'
            })
        
        project_path = os.path.join(COMPOSE_ROOT, project_name)
        if not os.path.exists(project_path):
            return jsonify({
                'status': 'error',
                'message': '项目不存在'
            })
            
        logs = []
        
        try:
            # 1. 停止项目
            logs.append(f"正在停止项目 {project_name}...")
            stop_cmd = ['docker', 'compose', 'down']
            stop_result = subprocess.run(
                stop_cmd,
                cwd=project_path,
                capture_output=True,
                text=True
            )
            logs.extend(stop_result.stdout.splitlines())
            if stop_result.stderr:
                logs.extend(stop_result.stderr.splitlines())
            
            if stop_result.returncode != 0:
                raise Exception("停止项目失败")
            
            # 2. 获取项目使用的镜像
            logs.append("\n正在获取项目镜像...")
            with open(os.path.join(project_path, 'docker-compose.yml'), 'r') as f:
                compose_config = yaml.safe_load(f)
            
            # 收集所有服务使用的镜像
            images = []
            for service in compose_config.get('services', {}).values():
                if 'image' in service:
                    images.append(service['image'])
            
            # 3. 删除相关镜像
            logs.append("\n正在清理镜像...")
            for image in images:
                try:
                    remove_cmd = ['docker', 'rmi', image]
                    remove_result = subprocess.run(
                        remove_cmd,
                        capture_output=True,
                        text=True
                    )
                    logs.extend(remove_result.stdout.splitlines())
                    if remove_result.stderr:
                        logs.extend(remove_result.stderr.splitlines())
                except Exception as e:
                    logs.append(f"清理镜像 {image} 时出错: {str(e)}")
            
            logs.append("\n清理完成！")
            
            return jsonify({
                'status': 'success',
                'message': '项目清理成功',
                'logs': logs
            })
            
        except Exception as e:
            error_msg = str(e)
            logs.append(f"\n操作失败: {error_msg}")
            return jsonify({
                'status': 'error',
                'message': error_msg,
                'logs': logs
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@compose_bp.route('/create', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.json
        project_name = data.get('project_name', '').strip()
        compose_content = data.get('compose_content', '').strip()
        env_content = data.get('env_content', '').strip()
        run_after_create = data.get('run_after_create', False)
        
        # 验证项目名称
        if not project_name:
            return jsonify({
                'status': 'error',
                'message': '项目名称不能为空'
            })
        
        # 验证项目名称格式
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', project_name):
            return jsonify({
                'status': 'error',
                'message': '项目名称格式不正确'
            })
        
        # 验证项目是否已存在
        project_path = os.path.join(COMPOSE_ROOT, project_name)
        if os.path.exists(project_path):
            return jsonify({
                'status': 'error',
                'message': '项目已存在'
            })
        
        # 验证 compose 配置
        if not compose_content:
            return jsonify({
                'status': 'error',
                'message': 'docker-compose.yml 配置不能为空'
            })
        
        try:
            # 验证 YAML 格式
            compose_config = yaml.safe_load(compose_content)
            
            # 验证服务配置
            if not isinstance(compose_config, dict) or 'services' not in compose_config:
                raise ValueError('缺少 services 配置')
                
            # 验证服务名称格式
            for service_name in compose_config['services'].keys():
                if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', service_name):
                    raise ValueError(f'服务名称 {service_name} 格式不正确')
                    
        except yaml.YAMLError as e:
            return jsonify({
                'status': 'error',
                'message': f'docker-compose.yml 格式错误: {str(e)}'
            })
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            })
        
        # 创建项目目录
        os.makedirs(project_path)
        
        # 保存 docker-compose.yml
        compose_file = os.path.join(project_path, 'docker-compose.yml')
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(compose_content)
        
        # 如果有 .env 配置，保存它
        if env_content:
            env_file = os.path.join(project_path, '.env')
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
        
        # 记录操作日志
        log_operation('create_project', project_name, 'success', '项目创建成功')

        # 如果选择了创建后运行，部署项目
        logs = []
        if run_after_create:
            try:
                logs.append(f"正在启动项目 {project_name}...")
                # 使用最新保存的配置文件部署项目
                cmd = ['docker', 'compose', 'up', '-d']
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True
                )
                logs.extend(result.stdout.splitlines())
                if result.stderr:
                    logs.extend(result.stderr.splitlines())
                
                if result.returncode == 0:
                    logs.append("\n项目启动成功！")
                else:
                    logs.append("\n项目启动失败！")
            except Exception as e:
                logs.append(f"\n启动出错: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'message': '项目创建成功',
            'logs': logs
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error creating project: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        })

# 添加新的函数来获取当前 Docker 镜像源配置
def get_current_docker_registry():
    """获取当前 Docker 镜像源配置"""
    try:
        # 读取 Docker daemon 配置文件
        docker_config_path = '/etc/docker/daemon.json'
        if os.path.exists(docker_config_path):
            with open(docker_config_path, 'r') as f:
                config = json.load(f)
                return config.get('registry-mirrors', [])
        return []
    except Exception as e:
        logger.error(f"Error reading Docker registry config: {e}")
        return []

@compose_bp.route('/registry/current', methods=['GET'])
def get_current_registry():
    """获取当前镜像源配置，括 Docker 当前配置"""
    try:
        # 获取保存的配置
        saved_config = load_registry_config()
        # 获取 Docker 当前配置
        docker_mirrors = get_current_docker_registry()
        
        return jsonify({
            'status': 'success',
            'registries': saved_config.get('registries', []),
            'docker_mirrors': docker_mirrors
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@compose_bp.route('/convert/run-to-compose', methods=['POST'])
def convert_run_to_compose():
    """将 docker run 命令转换为 docker-compose.yml"""
    try:
        data = request.json
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({
                'status': 'error',
                'message': '命令不能为空'
            })
        
        # 解析命令
        try:
            args = shlex.split(command)
            if args[0] != 'docker' or args[1] != 'run':
                raise ValueError("不是有效的 docker run 命令")
            
            args = args[2:]  # 移除 'docker run'
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'命令解析失败: {str(e)}'
            })
        
        # 初始化 compose 配置
        compose_config = {
            'services': {
                'app': {}  # 默认服务名
            }
        }
        
        service = compose_config['services']['app']
        i = 0
        while i < len(args):
            arg = args[i]
            
            # 处理不同的参数
            if arg == '-d' or arg == '--detach':
                # compose 默认就是后台运行的
                i += 1
            elif arg == '--name':
                # 使用容器名作为服务名
                service_name = args[i + 1]
                compose_config['services'] = {
                    service_name: service
                }
                i += 2
            elif arg == '-p' or arg == '--publish':
                # 端口映射
                if 'ports' not in service:
                    service['ports'] = []
                service['ports'].append(args[i + 1])
                i += 2
            elif arg == '-v' or arg == '--volume':
                # 卷挂载
                if 'volumes' not in service:
                    service['volumes'] = []
                service['volumes'].append(args[i + 1])
                i += 2
            elif arg == '-e' or arg == '--env':
                # 环境变量
                if 'environment' not in service:
                    service['environment'] = []
                service['environment'].append(args[i + 1])
                i += 2
            elif arg == '--network':
                # 网络设置
                service['network_mode'] = args[i + 1]
                i += 2
            elif arg == '--restart':
                # 重启策略
                service['restart'] = args[i + 1]
                i += 2
            elif arg.startswith('--'):
                # 其他长参数
                key = arg[2:].replace('-', '_')
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    service[key] = args[i + 1]
                    i += 2
                else:
                    service[key] = True
                    i += 1
            elif arg.startswith('-'):
                # 其他短参数
                i += 2
            else:
                # 镜像名称
                service['image'] = arg
                i += 1
        
        # 自定义 YAML 转储函数，处理特殊缩进
        def custom_yaml_dump(data, indent=2):
            lines = []
            
            def dump_value(value, level=0):
                base_indent = ' ' * (level * indent)
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, (list, dict)):
                            lines.append(f"{base_indent}{k}:")
                            dump_value(v, level + 1)
                        else:
                            lines.append(f"{base_indent}{k}: {v}")
                elif isinstance(value, list):
                    for item in value:
                        lines.append(f"{base_indent}- {item}")
                else:
                    lines.append(f"{base_indent}{value}")
            
            dump_value(data)
            return '\n'.join(lines)
        
        # 使用自定义函数生成 YAML
        compose_yaml = custom_yaml_dump(compose_config)
        
        return jsonify({
            'status': 'success',
            'compose_yaml': compose_yaml
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@compose_bp.route('/convert/compose-to-run', methods=['POST'])
def convert_compose_to_run():
    """将 docker-compose.yml 转换为 docker run 命令"""
    try:
        data = request.json
        compose_yaml = data.get('compose_yaml', '').strip()
        
        if not compose_yaml:
            return jsonify({
                'status': 'error',
                'message': 'YAML 内容不能为空'
            })
        
        # 解析 YAML
        try:
            compose_config = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            return jsonify({
                'status': 'error',
                'message': f'YAML 格式错误: {str(e)}'
            })
        
        # 检查是否有 services 配置
        if not isinstance(compose_config, dict):
            return jsonify({
                'status': 'error',
                'message': '无效的 compose 文件格式'
            })
            
        # 如果没有 services 键，可能整个文件就是一个服务的配置
        if 'services' not in compose_config:
            services = {'app': compose_config}  # 使用默认服务名
        else:
            services = compose_config['services']
            
        if not services:  # 检查 services 是否为空
            return jsonify({
                'status': 'error',
                'message': '未找到任何服务配置'
            })
        
        commands = []
        for service_name, service in services.items():
            if not isinstance(service, dict):  # 检查服务配置是否为字典
                continue
                
            cmd_parts = ['docker run -d']
            
            # 添加容器名
            cmd_parts.append(f'--name {service_name}')
            
            # 添加端口映射
            if 'ports' in service:
                ports = service['ports']
                if isinstance(ports, list):
                    for port in ports:
                        if isinstance(port, str):
                            cmd_parts.append(f'-p {port}')
                        elif isinstance(port, dict):
                            # 处理详细的端口配置
                            target = port.get('target')
                            published = port.get('published')
                            if target and published:
                                cmd_parts.append(f'-p {published}:{target}')
            
            # 添加卷挂载
            if 'volumes' in service:
                volumes = service['volumes']
                if isinstance(volumes, list):
                    for volume in volumes:
                        if isinstance(volume, str):
                            cmd_parts.append(f'-v {volume}')
                        elif isinstance(volume, dict):
                            # 处理详细的卷配置
                            source = volume.get('source')
                            target = volume.get('target')
                            if source and target:
                                cmd_parts.append(f'-v {source}:{target}')
            
            # 添加环境变量
            if 'environment' in service:
                env = service['environment']
                if isinstance(env, list):
                    for item in env:
                        cmd_parts.append(f'-e {item}')
                elif isinstance(env, dict):
                    for key, value in env.items():
                        if value is not None:
                            cmd_parts.append(f'-e {key}={value}')
                        else:
                            cmd_parts.append(f'-e {key}')
            
            # 添加网络设置
            if 'network_mode' in service:
                cmd_parts.append(f'--network {service["network_mode"]}')
            elif 'networks' in service:
                networks = service['networks']
                if isinstance(networks, list) and networks:
                    cmd_parts.append(f'--network {networks[0]}')
                elif isinstance(networks, dict) and networks:
                    cmd_parts.append(f'--network {list(networks.keys())[0]}')
            
            # 添加重启策略
            if 'restart' in service:
                cmd_parts.append(f'--restart {service["restart"]}')
            
            # 添加依赖项提示
            if 'depends_on' in service:
                cmd_parts.append(f'# 注意：此服务依赖于 {", ".join(service["depends_on"])}')
            
            # 添加工作目录
            if 'working_dir' in service:
                cmd_parts.append(f'--workdir {service["working_dir"]}')
            
            # 添加用户设置
            if 'user' in service:
                cmd_parts.append(f'--user {service["user"]}')
            
            # 添加主机名
            if 'hostname' in service:
                cmd_parts.append(f'--hostname {service["hostname"]}')
            
            # 添加DNS设置
            if 'dns' in service:
                dns = service['dns']
                if isinstance(dns, list):
                    for dns_server in dns:
                        cmd_parts.append(f'--dns {dns_server}')
                elif isinstance(dns, str):
                    cmd_parts.append(f'--dns {dns}')
            
            # 添加容器特权模式
            if 'privileged' in service and service['privileged']:
                cmd_parts.append('--privileged')
            
            # 添加其他选项
            for key, value in service.items():
                if key not in ['image', 'ports', 'volumes', 'environment', 
                             'network_mode', 'networks', 'restart', 'depends_on',
                             'working_dir', 'user', 'hostname', 'dns', 'privileged',
                             'version', 'services']:  # 忽略 version 和 services 键
                    if isinstance(value, bool):
                        if value:
                            cmd_parts.append(f'--{key.replace("_", "-")}')
                    elif isinstance(value, (str, int)):
                        cmd_parts.append(f'--{key.replace("_", "-")} {value}')
            
            # 添加镜像名称（必须放在最后）
            if 'image' in service:
                cmd_parts.append(service['image'])
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'服务 {service_name} 缺少镜像配置'
                })
            
            commands.append(' '.join(cmd_parts))
        
        if not commands:  # 检查是否生成了任何命令
            return jsonify({
                'status': 'error',
                'message': '无法生成 docker run 命令'
            })
        
        return jsonify({
            'status': 'success',
            'commands': commands
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@compose_bp.route('/directories')
def list_directories():
    """列出目录"""
    try:
        path = request.args.get('path', '/')
        
        # 规范化路径
        path = os.path.normpath(path)
        if not path.startswith('/'):
            path = '/'
            
        # 获取父目录路径
        parent_path = os.path.dirname(path)
        if parent_path == path:
            parent_path = '/'
            
        # 获取目录列表
        directories = []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    directories.append(item)
        except PermissionError:
            return jsonify({
                'status': 'error',
                'message': '没有权限访问该目录'
            })
            
        return jsonify({
            'status': 'success',
            'current_path': path,
            'parent_path': parent_path,
            'directories': sorted(directories)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })