# 中文语言配置
LANG = {
    'title': '丸子工具箱',
    'version': '版本',
    'navigation': {
        'home': '首页',
        'back': '返回',
        'root': '根目录'
    },
    'buttons': {
        'select_all': '全选',
        'deselect_all': '取消全选',
        'select_unused': '选择未使用',
        'select_stopped': '选择未启动',
        'add': '添加',
        'push': '推送',
        'export': '导出',
        'delete': '删除',
        'config': '配置镜像源',
        'save': '保存',
        'start': '启动',
        'stop': '停止',
        'edit': '编辑',
        'cancel': '取消',
        'confirm': '确认',
        'test': '测试连接',
        'add_project': '新建项目',
        'convert_code': '代码转换',
        'convert': '转换'
    },
    'modules': {
        'permission': {
            'name': '文件权限管理',
            'description': '管理文件和目录的访问权限'
        },
        'docker': {
            'name': 'Docker镜像管理',
            'description': '管理本地Docker镜像'
        },
        'compose': {
            'name': 'Compose项目管理',
            'description': '管理Docker Compose项目'
        }
    },
    'dialogs': {
        'delete': {
            'title': '确认删除',
            'message': '确定要删除选中的项目吗？此操作不可恢复',
            'selected': '已选择',
            'total_size': '总计大小'
        },
        'tag': {
            'title': '修改标签',
            'current': '当前标签',
            'new': '新标签',
            'placeholder': '例如: myimage:latest',
            'help': '格式: 名称:标签，如果不指定标签则默认为latest'
        },
        'deploy': {
            'title': '部署日志',
            'success': '操作成功',
            'failed': '操作失败'
        },
        'cleanup_title': '确认清理',
        'cleanup_confirm': '确定要停止项目并清理相关镜像吗？此操作将删除项目使用的所有镜像。',
        'add_project': {
            'title': '新建项目',
            'name': '项目名称',
            'name_placeholder': '输入项目名称',
            'name_help': '只能包含字母、数字、下划线、点和连字符，且必须以字母或数字开头',
            'editor': '编辑器',
            'upload': '上传文件',
            'optional': '(可选)',
            'compose_placeholder': '输入 docker-compose.yml 配置...',
            'env_placeholder': '输入环境变量配置...',
            'run_after_create': '创建后立即运行'
        },
        'current_docker_registry': '当前 Docker 镜像源配置',
        'registry_addresses': '镜像源地址列表',
        'registry_placeholder': '例如: https://registry.example.com',
        'registry_help': '可以添加多个镜像源地址，每行一个',
        'add_registry': '添加镜像源',
        'convert_title': '代码转换',
        'docker_run_command': 'Docker Run 命令',
        'compose_result': 'Compose 转换结果'
    },
    'contact': {
        'wechat': '微信公众号：红薯丸子',
        'blog': '博客',
        'gitee': 'Gitee'
    },
    'docker': {
        'title': 'Docker镜像管理',
        'buttons': {
            'select_all': '全选',
            'deselect_all': '取消全选',
            'select_unused': '选择未使用镜像',
            'add': '添加镜像',
            'push': '推送镜像',
            'export': '导出镜像',
            'delete': '删除镜像',
            'config': '配置镜像源'
        },
        'table': {
            'select': '选择',
            'info': '镜像信息',
            'tags': '标签',
            'size': '大小',
            'created': '创建时间',
            'status': '状态'
        },
        'status': {
            'in_use': '使用中',
            'unused': '未使用'
        },
        'dialogs': {
            'delete': {
                'title': '确认删除',
                'message': '确定要删除选中的Docker镜像吗？此操作不可恢复。',
                'selected': '已选择',
                'total_size': '总计大小',
                'cancel': '取消',
                'confirm': '确认删除'
            },
            'push': {
                'title': '推送镜像',
                'target': '选择推送目标',
                'dockerhub': {
                    'username': 'DockerHub 用户名',
                    'password': 'DockerHub 密码'
                },
                'aliyun': {
                    'region': '阿里云容器镜像实例',
                    'namespace': '命名空间',
                    'username': '访问凭证',
                    'password': '密码'
                }
            }
        }
    },
    'compose': {
        'title': 'Compose项目管理',
        'buttons': {
            'select_all': '全选',
            'deselect_all': '取消全选',
            'select_stopped': '选择未启动',
            'start': '启动选中',
            'stop': '停止选中',
            'config': '配置镜像源',
            'select_not_running': '选择未运行',
            'delete': '删除',
            'start': '启动',
            'stop': '停止',
            'cleanup': '停止并清理',
            'convert_code': '代码转换',
            'convert': '转换',
            'add_project': '新建项目'
        },
        'project': {
            'containers': '容器数量',
            'created': '创建时间',
            'status': {
                'running': '运行中',
                'stopped': '已停止',
                'unknown': '未知'
            }
        },
        'dialogs': {
            'delete': {
                'title': '确认删除',
                'message': '确定要删除选中的项目吗？此操作不可恢复。',
                'selected': '已选择',
                'total_size': '总计大小'
            },
            'deploy_logs': '部署日志',
            'config_title': '配置镜像源',
            'preset_registry': '选择预设镜像源',
            'custom': '自定义',
            'registry_address': '镜像源地址',
            'registry_placeholder': '例如: https://registry.example.com',
            'add_project': {
                'title': '新建项目',
                'name': '项目名称',
                'name_placeholder': '输入项目名称',
                'name_help': '只能包含字母、数字、下划线、点和连字符，且必须以字母或数字开头',
                'editor': '编辑器',
                'upload': '上传文件',
                'optional': '(可选)',
                'compose_placeholder': '输入 docker-compose.yml 配置...',
                'env_placeholder': '输入环境变量配置...',
                'run_after_create': '创建后立即运行'
            },
            'cleanup_title': '确认清理',
            'cleanup_confirm': '确定要停止项目并清理相关镜像吗？此操作将删除项目使用的所有镜像。',
            'convert_title': '代码转换',
            'docker_run_command': 'Docker Run 命令',
            'compose_result': 'Compose 转换结果',
            'preparing': '准备部署...',
            'starting': '开始{action}...',
            'operation_complete': '所有操作已完成。',
            'operation_failed': '操作失败: {message}',
            'operation_error': '操作出错: {message}',
            'current_project': '正在部署: {project}'
        },
        'root_path': {
            'label': '项目根目录',
            'placeholder': '/mnt/nas/docker',
            'browse': '浏览',
            'select_title': '选择目录',
            'select': '选择此目录'
        },
        'logs': {
            'title': '操作日志',
            'refresh': '刷新日志',
            'operation_history': '操作历史',
            'log_files': '日志文件',
            'time': '时间',
            'operation': '操作',
            'project': '项目',
            'status': '状态',
            'message': '消息',
            'status_types': {
                'success': '成功',
                'error': '失败'
            },
            'error': {
                'get_content': '获取日志内容失败',
                'get_content_error': '获取日志内容出错'
            }
        }
    },
    'permission': {
        'title': '文件权限管理',
        'search': {
            'placeholder': '搜索文件或文件夹...',
            'button': '搜索',
            'clear': '清除搜索',
            'results': '搜索结果'
        },
        'navigation': {
            'root': '根目录',
            'back': '返回上级'
        },
        'buttons': {
            'select_files': '仅选择文件',
            'select_dirs': '仅选择目录',
            'select_images': '选择图片',
            'select_videos': '选择视频',
            'select_docs': '选择文档',
            'invert': '反选',
            'modify': '修改权限'
        },
        'permissions': {
            'preview': '权限预览',
            'modify': '修改权限',
            'owner': '所有者',
            'group': '用户组',
            'others': '其他用户',
            'read': '读取(r)',
            'write': '写入(w)',
            'execute': '执行(x)'
        },
        'table': {
            'select': '选择',
            'name': '名称',
            'location': '位置',
            'permissions_oct': '八进制权限',
            'permissions_str': '权限字符串'
        },
        'quick_perms': {
            'full': '完全权限(rwxrwxrwx)',
            'dir': '目录权限(rwxr-xr-x)',
            'file': '文件权限(rw-r--r--)',
            'private': '私有权限(rw-------)'
        }
    }
} 