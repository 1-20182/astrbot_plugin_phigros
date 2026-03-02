"""
🎨 Phigros 高级渲染器

> "多种渲染方式，总有一种适合你！" ✨

支持三种渲染模式：
1. HTML模板 + Playwright（效果最佳，需要安装浏览器）
2. HTML模板 + Pillow（纯Python，效果较好）
3. 原生Pillow（最轻量，无需额外依赖）

自动选择最优方案，也可手动指定！
"""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from astrbot.api import logger

# 尝试导入可选依赖
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class AdvancedPhigrosRenderer:
    """
    🎨 Phigros 高级渲染器
    
    智能选择渲染方案，支持多种后端
    """
    
    # 渲染模式
    MODE_PHI_STYLE = "phi_style"    # Phi-Plugin 风格（推荐，效果最佳）
    MODE_PLAYWRIGHT = "playwright"  # HTML + Playwright
    MODE_HTML2PIL = "html2pil"      # HTML + Pillow
    MODE_PILLOW = "pillow"          # 原生Pillow（最轻量）
    
    def __init__(self,
                 plugin_dir: Path,
                 cache_dir: Optional[Path] = None,
                 illustration_path: Optional[Path] = None,
                 mode: Optional[str] = None,
                 image_quality: int = 95,
                 avatar_path: Optional[Path] = None):
        """
        初始化渲染器

        Args:
            plugin_dir: 插件目录
            cache_dir: 缓存目录
            illustration_path: 曲绘路径
            mode: 渲染模式（可选，自动选择）
            image_quality: 图片质量
            avatar_path: 头像路径
        """
        self.plugin_dir = Path(plugin_dir)
        self.cache_dir = cache_dir or (self.plugin_dir / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.illustration_path = illustration_path or (self.plugin_dir / "ILLUSTRATION")
        self.avatar_path = avatar_path or (self.plugin_dir / "AVATAR")
        self.image_quality = image_quality

        # 模板路径
        self.template_dir = self.plugin_dir / "resources" / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # 自动选择或指定渲染模式
        self.mode = mode or self._auto_select_mode()

        # 内部渲染器实例
        self._renderer = None

        logger.info(f"🎨 高级渲染器初始化完成，使用模式: {self.mode}")
    
    def _auto_select_mode(self) -> str:
        """自动选择最优渲染模式"""
        # 优先使用 Phi-Plugin 风格渲染器（纯Pillow，效果最好）
        if PILLOW_AVAILABLE:
            logger.info("✅ 使用 Phi-Plugin 风格渲染器（推荐）")
            return self.MODE_PHI_STYLE
        else:
            raise ImportError("没有可用的渲染后端，请安装 Pillow")
    
    async def initialize(self):
        """初始化渲染器"""
        if self.mode == self.MODE_PHI_STYLE:
            from .phi_style_renderer import PhiStyleRenderer
            self._renderer = PhiStyleRenderer(
                self.plugin_dir,
                self.cache_dir,
                self.illustration_path,
                self.image_quality,
                self.avatar_path
            )
        elif self.mode == self.MODE_PLAYWRIGHT:
            from .html_playwright_renderer import HtmlPlaywrightRenderer
            self._renderer = HtmlPlaywrightRenderer(
                self.plugin_dir,
                self.cache_dir,
                self.illustration_path,
                self.image_quality
            )
        elif self.mode == self.MODE_HTML2PIL:
            from .html_pil_renderer import HtmlPilRenderer
            self._renderer = HtmlPilRenderer(
                self.plugin_dir,
                self.cache_dir,
                self.illustration_path,
                self.image_quality
            )
        elif self.mode == self.MODE_PILLOW:
            from .renderer import PhigrosRenderer
            self._renderer = PhigrosRenderer(
                str(self.cache_dir),
                str(self.illustration_path),
                self.image_quality
            )
        
        if hasattr(self._renderer, 'initialize'):
            await self._renderer.initialize()
    
    async def terminate(self):
        """清理资源"""
        if self._renderer and hasattr(self._renderer, 'terminate'):
            await self._renderer.terminate()
    
    async def render_b30(self, data: Dict[str, Any], output_path: Path) -> bool:
        """
        渲染 Best30 成绩图
        
        Args:
            data: 成绩数据
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            return await self._renderer.render_b30(data, output_path)
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            return False
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        try:
            return await self._renderer.render_score(data, output_path)
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            return False
    
    def get_mode(self) -> str:
        """获取当前渲染模式"""
        return self.mode
    
    def is_playwright_available(self) -> bool:
        """检查是否可用 Playwright"""
        return PLAYWRIGHT_AVAILABLE
