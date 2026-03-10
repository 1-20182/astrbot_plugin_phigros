"""
⚙️ 配置常量模块

存放所有配置相关的常量，支持四层配置优先级：
1. 环境变量（最高优先级）
2. 插件配置（从WebUI获取）
3. YAML配置文件（从config.yaml获取）
4. 默认值（最低优先级）
"""

import os
import yaml
from typing import Optional, Dict, Any, List

class ConfigManager:
    """配置管理器，支持四层配置优先级"""
    
    _yaml_config = None
    
    @staticmethod
    def load_yaml_config(config_path: str = "config.yaml") -> Dict[str, Any]:
        """加载YAML配置文件"""
        if ConfigManager._yaml_config is None:
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        ConfigManager._yaml_config = yaml.safe_load(f)
                    import logging
                    logging.info(f"成功加载YAML配置文件: {config_path}")
                else:
                    ConfigManager._yaml_config = {}
            except Exception as e:
                import logging
                logging.error(f"加载YAML配置文件失败: {e}")
                ConfigManager._yaml_config = {}
        return ConfigManager._yaml_config
    
    @staticmethod
    def get_env_var(key: str, default: str = "") -> str:
        """获取环境变量，支持前缀"""
        # 尝试多种环境变量命名方式
        env_vars = [
            f"PHIGROS_{key}",
            f"PHIGROS_{key.upper()}",
            key,
            key.upper()
        ]
        
        for env_var in env_vars:
            value = os.getenv(env_var)
            if value is not None:
                return value
        return default
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(ConfigManager.get_env_var(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = ConfigManager.get_env_var(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'y', 'on')
    
    @staticmethod
    def get_config(config: Dict[str, Any], key: str, default: Any, config_key: Optional[str] = None) -> Any:
        """获取配置，支持四层优先级
        
        Args:
            config: 插件配置字典
            key: 环境变量键名
            default: 默认值
            config_key: 插件配置中的键名（如果与环境变量键名不同）
        
        Returns:
            配置值
        """
        # 1. 首先尝试从环境变量获取
        if isinstance(default, bool):
            env_value = ConfigManager.get_bool(key, default)
        elif isinstance(default, int):
            env_value = ConfigManager.get_int(key, default)
        else:
            env_value = ConfigManager.get_env_var(key, str(default) if default is not None else "")
            # 如果默认值不是字符串，尝试转换
            if default is not None and not isinstance(default, str):
                try:
                    if isinstance(default, (int, float)):
                        env_value = type(default)(env_value)
                except (ValueError, TypeError):
                    pass
        
        # 如果环境变量有值且与默认值类型相同，返回环境变量值
        if (isinstance(env_value, type(default)) or 
            (isinstance(default, (int, float)) and isinstance(env_value, (int, float)))):
            if env_value != default:
                import logging
                logging.info(f"从环境变量获取配置: {key} = {env_value}")
            return env_value
        
        # 2. 尝试从插件配置获取
        config_key = config_key or key
        if config and config_key in config:
            config_value = config[config_key]
            if (isinstance(config_value, type(default)) or 
                (isinstance(default, (int, float)) and isinstance(config_value, (int, float)))):
                import logging
                logging.info(f"从插件配置获取配置: {config_key} = {config_value}")
            return config_value
        
        # 3. 尝试从YAML配置文件获取
        yaml_config = ConfigManager.load_yaml_config()
        if yaml_config:
            # 支持嵌套配置，如 phigros.api.base_url
            keys = key.lower().split('.')
            current = yaml_config
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    break
            else:
                # 找到了完整路径
                if (isinstance(current, type(default)) or 
                    (isinstance(default, (int, float)) and isinstance(current, (int, float)))):
                    import logging
                    logging.info(f"从YAML配置文件获取配置: {key} = {current}")
                return current
        
        # 4. 返回默认值
        return default

# API 配置
BASE_URL = ConfigManager.get_env_var("BASE_URL", "https://r0semi.xtower.site/api/v1/open")
DEFAULT_API_TOKEN = ConfigManager.get_env_var("API_TOKEN", "")

# HTTP 配置
HTTP_TIMEOUT = 30
HTTP_CONNECT_TIMEOUT = 10
HTTP_SOCK_READ_TIMEOUT = 20
HTTP_POOL_SIZE = 50
HTTP_POOL_PER_HOST = 20

# 缓存配置
CACHE_TTL = 300  # 5 分钟
CACHE_CLEAN_INTERVAL = 600  # 10 分钟

# 图片配置
DEFAULT_IMAGE_QUALITY = 95
DEFAULT_IMAGE_FORMAT = "PNG"
PNG_COMPRESS_LEVEL = 1  # 1-9, 1 为最快

# 路径配置
DEFAULT_ILLUSTRATION_PATH = "./ILLUSTRATION"
DEFAULT_AVATAR_PATH = "./AVATAR"
DEFAULT_TAPTAP_VERSION = "cn"

# 搜索配置
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_HISTORY_LIMIT = 10

# 渲染配置
RENDERER_WIDTH = 1200
RENDERER_HEADER_HEIGHT = 180
RENDERER_CARD_WIDTH = 360
RENDERER_CARD_HEIGHT = 100
RENDERER_CARD_MARGIN = 15

# 字体配置
FONT_CACHE_SIZE = 50

# 登录配置
QR_LOGIN_TIMEOUT = 120  # 二维码有效期 2 分钟
QR_POLL_INTERVAL = 2  # 轮询间隔 2 秒

# 更新配置
ILLUSTRATION_UPDATE_INTERVAL = 7  # 7 天检查一次更新
ILLUSTRATION_UPDATE_TIMEOUT = 300  # 5 分钟下载超时