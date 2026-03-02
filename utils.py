"""
🛠️ 工具函数模块

存放各种公共工具函数和类
"""

import re
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from astrbot.api import logger


class SimpleCache:
    """简单的内存缓存，用于缓存 API 响应"""

    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            item = self._cache[key]
            if datetime.now().timestamp() - item['timestamp'] < self._ttl:
                return item['value']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存值"""
        self._cache[key] = {
            'value': value,
            'timestamp': datetime.now().timestamp()
        }

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def clean_expired(self):
        """清理过期缓存"""
        now = datetime.now().timestamp()
        expired_keys = [
            key for key, item in self._cache.items()
            if now - item['timestamp'] >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]


def resolve_illustration_path(base_dir: Path, illustration_path: str) -> Path:
    """解析曲绘路径，处理相对路径和绝对路径

    Args:
        base_dir: 基础目录（插件目录）
        illustration_path: 配置中的路径字符串

    Returns:
        解析后的 Path 对象
    """
    clean_path = illustration_path.lstrip("./").lstrip(".\\")

    if illustration_path.startswith("/") or (len(illustration_path) > 1 and illustration_path[1] == ":"):
        return Path(illustration_path)

    return base_dir / clean_path


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """清理文件名，防止路径穿越攻击

    Args:
        name: 原始文件名
        max_length: 最大长度

    Returns:
        清理后的文件名
    """
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    if not sanitized:
        sanitized = "unnamed"
    return sanitized


def encrypt_token(token: str) -> str:
    """对 token 进行简单混淆（非加密，仅增加读取难度）"""
    encoded = base64.b64encode(token.encode()).decode()
    return f"enc:{encoded}"


def decrypt_token(encrypted: str) -> str:
    """解密 token"""
    if encrypted.startswith("enc:"):
        encoded = encrypted[4:]
        return base64.b64decode(encoded.encode()).decode()
    return encrypted


async def send_image_with_fallback(event, image_path: Path, plain_text: str = None):
    """发送图片，带错误回退处理

    Args:
        event: AstrMessageEvent
        image_path: 图片路径
        plain_text: 发送失败时的文字提示

    Yields:
        发送结果消息
    """
    from astrbot.api.message_components import Image, Plain

    if not image_path.exists():
        logger.error(f"图片文件不存在: {image_path}")
        if plain_text:
            yield event.plain_result(f"❌ {plain_text}\n图片文件未找到")
        return

    try:
        # 方法1: 直接发送文件路径
        yield event.chain_result([Image(file=str(image_path))])
    except Exception as e1:
        logger.warning(f"方法1发送图片失败: {e1}")

        try:
            # 方法2: 使用 base64
            with open(image_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode()
            yield event.chain_result([Image.fromBase64(img_base64)])
        except Exception as e2:
            logger.error(f"方法2发送图片也失败: {e2}")
            if plain_text:
                yield event.plain_result(f"❌ {plain_text}\n图片发送失败，请检查日志")


def format_score(score: int) -> str:
    """格式化分数显示"""
    return f"{score:,}"


def format_acc(acc: float) -> str:
    """格式化准确率显示"""
    return f"{acc:.2f}%"


def format_rks(rks: float) -> str:
    """格式化 RKS 显示"""
    return f"{rks:.4f}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) > max_length:
        return text[:max_length - len(suffix)] + suffix
    return text
