import importlib
import logging

logger = logging.getLogger(__name__)

def load_language(lang_code):
    """加载语言配置"""
    try:
        lang_module = importlib.import_module(f'languages.{lang_code}')
        return lang_module.LANG
    except ImportError:
        # 如果找不到语言文件，返回默认语言（中文）
        logger.warning(f"Language {lang_code} not found, falling back to zh_CN")
        lang_module = importlib.import_module('languages.zh_CN')
        return lang_module.LANG
    except Exception as e:
        logger.error(f"Error loading language {lang_code}: {e}")
        # 如果出现其他错误，返回一个基本的语言配置
        return {
            'title': 'WanziTools',
            'version': 'Version',
            'navigation': {
                'home': 'Home'
            }
        }

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '中文',
    'en_US': 'English'
} 