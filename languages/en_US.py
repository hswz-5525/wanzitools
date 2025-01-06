# English language configuration
LANG = {
    'title': 'Wanzi Tools',
    'version': 'Version',
    'navigation': {
        'home': 'Home',
        'back': 'Back',
        'root': 'Root'
    },
    'buttons': {
        'select_all': 'Select All',
        'deselect_all': 'Deselect All',
        'select_unused': 'Select Unused',
        'select_stopped': 'Select Stopped',
        'add': 'Add',
        'push': 'Push',
        'export': 'Export',
        'delete': 'Delete',
        'config': 'Configure Registry',
        'save': 'Save',
        'start': 'Start',
        'stop': 'Stop',
        'edit': 'Edit',
        'cancel': 'Cancel',
        'confirm': 'Confirm',
        'test': 'Test Connection',
        'add_project': 'New Project',
        'convert_code': 'Convert Code',
        'convert': 'Convert'
    },
    'modules': {
        'permission': {
            'name': 'File Permission Manager',
            'description': 'Manage file and directory permissions'
        },
        'docker': {
            'name': 'Docker Image Manager',
            'description': 'Manage local Docker images'
        },
        'compose': {
            'name': 'Compose Project Manager',
            'description': 'Manage Docker Compose projects'
        }
    },
    'dialogs': {
        'delete': {
            'title': 'Confirm Delete',
            'message': 'Are you sure you want to delete the selected items? This action cannot be undone.',
            'selected': 'Selected',
            'total_size': 'Total Size'
        },
        'tag': {
            'title': 'Edit Tags',
            'current': 'Current Tags',
            'new': 'New Tag',
            'placeholder': 'e.g., myimage:latest',
            'help': 'Format: name:tag, defaults to latest if tag not specified'
        },
        'deploy': {
            'title': 'Deployment Logs',
            'success': 'Operation Successful',
            'failed': 'Operation Failed'
        },
        'cleanup_title': 'Confirm Cleanup',
        'cleanup_confirm': 'Are you sure you want to stop the project and cleanup related images? This will remove all images used by the project.',
        'add_project': {
            'title': 'New Project',
            'name': 'Project Name',
            'name_placeholder': 'Enter project name',
            'name_help': 'Can only contain letters, numbers, underscores, dots and hyphens, and must start with a letter or number',
            'editor': 'Editor',
            'upload': 'Upload File',
            'optional': '(Optional)',
            'compose_placeholder': 'Enter docker-compose.yml configuration...',
            'env_placeholder': 'Enter environment variables...',
            'run_after_create': 'Run after creation'
        },
        'registry_addresses': 'Registry Addresses',
        'registry_placeholder': 'e.g., https://registry.example.com',
        'registry_help': 'You can add multiple registry addresses, one per line',
        'add_registry': 'Add Registry',
        'convert_title': 'Code Conversion',
        'docker_run_command': 'Docker Run Command',
        'compose_result': 'Compose Result'
    },
    'contact': {
        'wechat': 'WeChat: HongShuWanZi',
        'blog': 'Blog',
        'gitee': 'Gitee'
    },
    'docker': {
        'title': 'Docker Image Manager',
        'buttons': {
            'select_all': 'Select All',
            'deselect_all': 'Deselect All',
            'select_unused': 'Select Unused',
            'add': 'Add Image',
            'push': 'Push Image',
            'export': 'Export Image',
            'delete': 'Delete Image',
            'config': 'Configure Registry'
        },
        'table': {
            'select': 'Select',
            'info': 'Image Info',
            'tags': 'Tags',
            'size': 'Size',
            'created': 'Created',
            'status': 'Status'
        },
        'status': {
            'in_use': 'In Use',
            'unused': 'Unused'
        },
        'dialogs': {
            'delete': {
                'title': 'Confirm Delete',
                'message': 'Are you sure you want to delete the selected Docker images? This action cannot be undone.',
                'selected': 'Selected',
                'total_size': 'Total Size',
                'cancel': 'Cancel',
                'confirm': 'Confirm Delete'
            },
            'push': {
                'title': 'Push Image',
                'target': 'Select Push Target',
                'dockerhub': {
                    'username': 'DockerHub Username',
                    'password': 'DockerHub Password'
                },
                'aliyun': {
                    'region': 'Aliyun Container Registry Instance',
                    'namespace': 'Namespace',
                    'username': 'Access Credential',
                    'password': 'Password'
                }
            }
        }
    },
    'compose': {
        'title': 'Compose Project Manager',
        'buttons': {
            'select_all': 'Select All',
            'deselect_all': 'Deselect All',
            'select_stopped': 'Select Stopped',
            'start': 'Start Selected',
            'stop': 'Stop Selected',
            'config': 'Configure Registry',
            'select_not_running': 'Select Not Running',
            'delete': 'Delete',
            'start': 'Start',
            'stop': 'Stop',
            'cleanup': 'Stop & Cleanup',
            'convert_code': 'Convert Code',
            'convert': 'Convert',
            'add_project': 'New Project'
        },
        'project': {
            'containers': 'Containers',
            'created': 'Created',
            'status': {
                'running': 'Running',
                'stopped': 'Stopped',
                'unknown': 'Unknown'
            }
        },
        'dialogs': {
            'delete': {
                'title': 'Confirm Delete',
                'message': 'Are you sure you want to delete the selected projects? This action cannot be undone.',
                'selected': 'Selected',
                'total_size': 'Total Size'
            },
            'deploy_logs': 'Deployment Logs',
            'config_title': 'Configure Registry',
            'preset_registry': 'Select Preset Registry',
            'custom': 'Custom',
            'registry_address': 'Registry Address',
            'registry_placeholder': 'e.g., https://registry.example.com',
            'add_project': {
                'title': 'New Project',
                'name': 'Project Name',
                'name_placeholder': 'Enter project name',
                'name_help': 'Can only contain letters, numbers, underscores, dots and hyphens, and must start with a letter or number',
                'editor': 'Editor',
                'upload': 'Upload File',
                'optional': '(Optional)',
                'compose_placeholder': 'Enter docker-compose.yml configuration...',
                'env_placeholder': 'Enter environment variables...',
                'run_after_create': 'Run after creation'
            },
            'cleanup_title': 'Confirm Cleanup',
            'cleanup_confirm': 'Are you sure you want to stop the project and cleanup related images? This will remove all images used by the project.',
            'convert_title': 'Code Conversion',
            'docker_run_command': 'Docker Run Command',
            'compose_result': 'Compose Result',
            'preparing': 'Preparing deployment...',
            'starting': 'Starting {action}...',
            'operation_complete': 'All operations completed.',
            'operation_failed': 'Operation failed: {message}',
            'operation_error': 'Operation error: {message}',
            'current_project': 'Deploying: {project}'
        },
        'root_path': {
            'label': 'Project Root Directory',
            'placeholder': '/mnt/nas/docker',
            'browse': 'Browse',
            'select_title': 'Select Directory',
            'select': 'Select This Directory'
        },
        'logs': {
            'title': 'Operation Logs',
            'refresh': 'Refresh Logs',
            'operation_history': 'Operation History',
            'log_files': 'Log Files',
            'time': 'Time',
            'operation': 'Operation',
            'project': 'Project',
            'status': 'Status',
            'message': 'Message',
            'status_types': {
                'success': 'Success',
                'error': 'Failed'
            },
            'error': {
                'get_content': 'Failed to get log content',
                'get_content_error': 'Error getting log content'
            }
        }
    },
    'permission': {
        'title': 'File Permission Manager',
        'search': {
            'placeholder': 'Search files or folders...',
            'button': 'Search',
            'clear': 'Clear Search',
            'results': 'Search Results'
        },
        'navigation': {
            'root': 'Root Directory',
            'back': 'Back to Parent'
        },
        'buttons': {
            'select_files': 'Select Files Only',
            'select_dirs': 'Select Directories Only',
            'select_images': 'Select Images',
            'select_videos': 'Select Videos',
            'select_docs': 'Select Documents',
            'invert': 'Invert Selection',
            'modify': 'Modify Permissions'
        },
        'permissions': {
            'preview': 'Permission Preview',
            'modify': 'Modify Permissions',
            'owner': 'Owner',
            'group': 'Group',
            'others': 'Others',
            'read': 'Read(r)',
            'write': 'Write(w)',
            'execute': 'Execute(x)'
        },
        'table': {
            'select': 'Select',
            'name': 'Name',
            'location': 'Location',
            'permissions_oct': 'Octal Permissions',
            'permissions_str': 'Permission String'
        },
        'quick_perms': {
            'full': 'Full Permission(rwxrwxrwx)',
            'dir': 'Directory Permission(rwxr-xr-x)',
            'file': 'File Permission(rw-r--r--)',
            'private': 'Private Permission(rw-------)'
        }
    }
} 