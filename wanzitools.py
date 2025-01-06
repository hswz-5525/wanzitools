from flask import Flask, render_template, redirect, url_for, request, session
from image_manager import image_bp
from permission_manager import perm_bp
from compose_manager import compose_bp
import yaml
from datetime import datetime
import importlib
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 用于session

# 注册蓝图
app.register_blueprint(image_bp)
app.register_blueprint(perm_bp, url_prefix='/permissions')
app.register_blueprint(compose_bp, url_prefix='/compose')

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '中文',
    'en_US': 'English'
}

def load_language(lang_code):
    """加载语言配置"""
    try:
        print(f"Attempting to load language: {lang_code}")  # 添加调试信息
        print(f"Current working directory: {os.getcwd()}")  # 添加调试信息
        print(f"Files in languages directory: {os.listdir('languages')}")  # 添加调试信息
        
        lang_module = importlib.import_module(f'languages.{lang_code}')
        lang_config = lang_module.LANG
        
        # 验证必要的键是否存在
        required_keys = ['modules', 'compose']
        for key in required_keys:
            if key not in lang_config.get('modules', {}):
                print(f"Warning: Missing key '{key}' in language config")  # 添加调试信息
        
        return lang_config
    except ImportError as e:
        print(f"ImportError loading language {lang_code}: {e}")  # 添加调试信息
        # 如果找不到语言文件，返回默认语言（中文）
        lang_module = importlib.import_module('languages.zh_CN')
        return lang_module.LANG
    except Exception as e:
        print(f"Error loading language {lang_code}: {e}")  # 添加调试信息
        return {
            'title': 'WanziTools',
            'version': 'Version',
            'modules': {
                'permission': {
                    'name': 'File Permission Manager',
                    'description': 'Manage file permissions'
                },
                'docker': {
                    'name': 'Docker Image Manager',
                    'description': 'Manage Docker images'
                },
                'compose': {
                    'name': 'Compose Project Manager',
                    'description': 'Manage Docker Compose projects'
                }
            },
            'navigation': {
                'home': 'Home'
            }
        }

@app.template_filter('datetime')
def format_datetime(timestamp):
    """将时间戳转换为可读的日期时间格式"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return str(timestamp)

def get_version():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config.get('version', '未知版本')
    except Exception as e:
        print(f"Error reading version: {e}")
        return '未知版本'

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/language/<lang_code>')
def change_language(lang_code):
    """切换语言"""
    if lang_code in SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    """主页面，显示功能导航"""
    # 获取当前语言，默认中文
    current_lang = session.get('language', 'zh_CN')
    lang = load_language(current_lang)
    
    version = get_version()
    modules = [
        {
            'name': lang['modules']['permission']['name'],
            'route': '/permission',
            'icon': 'fas fa-key',
            'description': lang['modules']['permission']['description']
        },
        {
            'name': lang['modules']['docker']['name'],
            'route': '/images',
            'icon': 'fab fa-docker',
            'description': lang['modules']['docker']['description']
        },
        {
            'name': lang['modules']['compose']['name'],
            'route': '/compose',
            'icon': 'fas fa-layer-group',
            'description': lang['modules']['compose']['description']
        }
    ]
    return render_template('home.html', 
                         version=version, 
                         modules=modules,
                         lang=lang,
                         current_lang=current_lang,
                         supported_languages=SUPPORTED_LANGUAGES)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5525, debug=True) 