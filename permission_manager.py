from flask import Blueprint, render_template, request, redirect, url_for, abort, send_from_directory, session
import os
import stat
import fnmatch
from image_manager import image_bp
from languages import load_language, SUPPORTED_LANGUAGES
from languages.zh_CN import LANG as zh_CN_LANG
from languages.en_US import LANG as en_US_LANG

# 创建蓝图
perm_bp = Blueprint('permission', __name__)

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '中文',
    'en_US': 'English'
}

# NAS挂载点
NAS_MOUNT_POINT = os.getenv('NAS_MOUNT_POINT', 'Z://')

def get_permission_string(mode):
    """将数字权限转换为可读字符串 (例如: rwxr-xr--)"""
    perms = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']
    result = ''
    # 所有者权限
    result += perms[(mode >> 6) & 0o7]
    # 组权限
    result += perms[(mode >> 3) & 0o7]
    # 其他用户权限
    result += perms[mode & 0o7]
    return result

def get_files_and_dirs(path):
    try:
        items = os.listdir(path)
        files_and_dirs = []
        for item in items:
            item_path = os.path.join(path, item)
            try:
                # 获取文件状态
                stat_info = os.stat(item_path)
                # 获取权限模式
                mode = stat_info.st_mode
                # 转换为八进制字符串 (去掉'0o'前缀)
                oct_mode = oct(mode & 0o777)[2:]
                # 获取可读的权限字符串
                perm_string = get_permission_string(mode & 0o777)
                
                files_and_dirs.append({
                    'name': item,
                    'is_dir': os.path.isdir(item_path),
                    'mode_oct': oct_mode,
                    'mode_str': perm_string
                })
            except Exception as e:
                print(f"Error getting file info for {item}: {e}")
                continue
        return sorted(files_and_dirs, key=lambda x: (not x['is_dir'], x['name']))
    except Exception as e:
        print(f"Error reading directory: {e}")
        return []

def search_files(start_path, search_pattern):
    """递归搜索文件"""
    results = []
    try:
        for root, dirs, files in os.walk(start_path):
            # 获取相对于起始路径的相对路径
            rel_path = os.path.relpath(root, start_path)
            if rel_path == '.':
                rel_path = ''
                
            # 搜索匹配的文件和目录
            for item in dirs + files:
                if fnmatch.fnmatch(item.lower(), search_pattern.lower()):
                    full_path = os.path.join(root, item)
                    try:
                        # 获取文件状态
                        stat_info = os.stat(full_path)
                        mode = stat_info.st_mode
                        oct_mode = oct(mode & 0o777)[2:]
                        perm_string = get_permission_string(mode & 0o777)
                        
                        # 获取父目录路径
                        parent_path = rel_path if rel_path else ''
                        
                        results.append({
                            'name': item,
                            'is_dir': os.path.isdir(full_path),
                            'mode_oct': oct_mode,
                            'mode_str': perm_string,
                            'rel_path': os.path.join(rel_path, item) if rel_path else item,
                            'parent_path': parent_path
                        })
                    except Exception as e:
                        print(f"Error getting file info for {item}: {e}")
                        continue
    except Exception as e:
        print(f"Error during search: {e}")
    return results

@perm_bp.route('/')
@perm_bp.route('/<path:current_dir>')
def index(current_dir=''):
    # 获取当前语言，默认中文
    current_lang = session.get('language', 'zh_CN')
    lang = load_language(current_lang)
    
    # 忽略favicon.ico请求
    if current_dir == 'favicon.ico':
        return '', 204

    full_path = os.path.join(NAS_MOUNT_POINT, current_dir)

    # 防止路径遍历攻击
    if not full_path.startswith(NAS_MOUNT_POINT):
        abort(403)

    # 检查路径是否存在
    if not os.path.exists(full_path):
        abort(404)

    # 获取搜索参数
    search_pattern = request.args.get('search', '').strip()
    search_results = []

    if search_pattern:
        # 如果有搜索词，执行搜索
        search_results = search_files(full_path, f'*{search_pattern}*')
        files_and_dirs = search_results
    else:
        # 否则显示当前目录内容
        files_and_dirs = get_files_and_dirs(full_path)

    # 获取当前目录的相对路径
    relative_path = os.path.relpath(full_path, NAS_MOUNT_POINT)
    if relative_path == '.':
        relative_path = ''

    return render_template('permission_manager.html', 
                         files_and_dirs=files_and_dirs, 
                         current_dir=relative_path,
                         search_pattern=search_pattern,
                         is_search_result=bool(search_pattern),
                         lang=lang,
                         current_lang=current_lang,
                         supported_languages=SUPPORTED_LANGUAGES)

@perm_bp.route('/change', methods=['POST'])
@perm_bp.route('/permission/change', methods=['POST'])
def change_permissions():
    if request.method != 'POST':
        abort(405)  # Method Not Allowed
        
    filenames = request.form.getlist('filenames')
    mode_str = request.form.get('mode')
    current_dir = request.form.get('current_dir', '')

    # 输入验证
    if not filenames or not mode_str:
        abort(400)  # Bad Request

    try:
        # 验证权限格式
        if not mode_str.startswith('0') or len(mode_str) != 4:
            raise ValueError("Invalid permission format")
        mode = int(mode_str, 8)  # 八进制模式
        if mode < 0 or mode > 0o777:
            raise ValueError("Permission value out of range")
            
        for filename in filenames:
            path = os.path.join(NAS_MOUNT_POINT, current_dir, filename)
            
            # 安全检查
            if not os.path.abspath(path).startswith(os.path.abspath(NAS_MOUNT_POINT)):
                abort(403)  # Forbidden
                
            if not os.path.exists(path):
                continue  # 跳过不存在的文件
                
            os.chmod(path, mode)
            
        return redirect(url_for('permission.index', current_dir=current_dir))
        
    except ValueError as e:
        print(f"Invalid permission value: {e}")
        abort(400)  # Bad Request
    except Exception as e:
        print(f"Error: {e}")
        abort(500)  # Internal Server Error

# 添加favicon路由处理
@perm_bp.route('/favicon.ico')
def favicon():
    return '', 204  # 返回无内容响应