"""
🎨 Phigros 插件图像输出设计系统

提供统一的设计语言、可重用组件和模板系统，用于生成各种类型的图像输出。
"""

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime
import logging

# 配置标准日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 尝试导入 astrbot 日志
try:
    from astrbot.api import logger
except ImportError:
    # 如果导入失败，使用标准日志
    logger = logging.getLogger(__name__)

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


class PhigrosDesignSystem:
    """
    🎨 Phigros 插件设计系统
    
    提供统一的设计语言、可重用组件和模板系统
    """
    
    # 设计语言 - 颜色定义
    DESIGN_LANGUAGE = {
        # 难度级别颜色
        'difficulty': {
            'EZ': '#92d050',  # 绿色
            'HD': '#00b0f0',  # 蓝色
            'IN': '#ff0000',  # 红色
            'AT': '#6e6e6e',  # 灰色
        },
        # 主题颜色
        'theme': {
            'bg': '#1a1a2e',        # 深色背景
            'card_bg': 'rgba(0, 0, 0, 0.6)',  # 卡片背景
            'text_white': '#ffffff',  # 白色文本
            'text_gray': '#aaaaaa',   # 灰色文本
            'accent': '#00b0f0',      # 强调色
            'gold': '#ffd700',        # 金色
        },
        # 功能颜色
        'function': {
            'success': '#00ff00',     # 成功
            'warning': '#ffff00',     # 警告
            'error': '#ff0000',       # 错误
            'info': '#66ccff',        # 信息
        }
    }
    
    # 布局常量
    LAYOUT = {
        # 基础尺寸
        'width': 1200,
        'header_height': 180,
        'footer_height': 60,
        'card_width': 350,
        'card_height': 90,
        'card_margin': 8,
        'overflow_header_height': 120,
        
        # 响应式断点
        'breakpoints': {
            'desktop': 1200,
            'tablet': 768,
            'mobile': 480
        }
    }
    
    # 字体配置
    FONT_CONFIG = {
        'base_size': 16,
        'sizes': {
            'xs': 9,
            'sm': 12,
            'md': 16,
            'lg': 24,
            'xl': 28,
            'xxl': 36
        },
        'weights': {
            'regular': False,
            'bold': True
        }
    }
    
    def __init__(self, 
                 plugin_dir: Path, 
                 cache_dir: Path, 
                 illustration_path: Path, 
                 image_quality: int = 95, 
                 avatar_path: Optional[Path] = None):
        """
        初始化设计系统
        
        Args:
            plugin_dir: 插件目录
            cache_dir: 缓存目录
            illustration_path: 曲绘目录
            image_quality: 图片质量
            avatar_path: 头像目录
        """
        self.plugin_dir = plugin_dir
        self.cache_dir = cache_dir
        self.illustration_path = illustration_path
        self.image_quality = image_quality
        self.avatar_path = avatar_path or (plugin_dir / "AVATAR")
        
        # 缓存
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._illustration_cache: Dict[str, Image.Image] = {}
        self._avatar_cache: Dict[str, Image.Image] = {}
        self._rating_cache: Dict[str, Image.Image] = {}
        self._bg_cache: Optional[Image.Image] = None
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 曲绘预加载缓存
        self._processed_illust_cache: Dict[str, Image.Image] = {}
        self._illustration_usage: Dict[str, List[str]] = {}
        self._all_illustrations: Dict[str, List[Path]] = {}
        
        # 评级图片路径
        self.rating_path = plugin_dir / "resources" / "img" / "rating"
        
        # 初始化
        self._initialize_illustrations_map()
        logger.info("🎨 Phigros 设计系统初始化完成")
    
    def _initialize_illustrations_map(self):
        """初始化可用曲绘映射"""
        try:
            # 获取所有图片文件
            all_image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
                all_image_files.extend(self.illustration_path.glob(ext))
                # 大小写敏感处理
                all_image_files.extend(self.illustration_path.glob(ext.upper()))
            
            # 构建曲绘映射
            for file in all_image_files:
                file_stem_lower = file.stem.lower()
                # 提取歌曲名称
                import re
                song_name = re.sub(r'\s*\(\d+\)$|\s*_\d+$', '', file_stem_lower)
                if song_name not in self._all_illustrations:
                    self._all_illustrations[song_name] = []
                self._all_illustrations[song_name].append(file)
            
            logger.info(f"✅ 初始化曲绘映射完成，找到 {len(self._all_illustrations)} 首歌曲的曲绘")
        except Exception as e:
            logger.warning(f"初始化曲绘映射失败: {e}")
    
    async def initialize(self):
        """初始化资源"""
        await self._preload_resources()
    
    async def _preload_resources(self):
        """预加载常用资源"""
        logger.info("🚀 预加载渲染资源...")
        
        # 预加载评级图片
        ratings = ['φ', 'V', 'S', 'A', 'B', 'C', 'F', 'FC']
        for rating in ratings:
            self._get_rating_image(rating)
        
        # 预加载常用字体
        for size_name, size in self.FONT_CONFIG['sizes'].items():
            for weight_name, weight in self.FONT_CONFIG['weights'].items():
                self._get_font(size, weight)
        
        logger.info("✅ 资源预加载完成")
    
    async def terminate(self):
        """清理资源"""
        self._illustration_cache.clear()
        self._font_cache.clear()
        self._avatar_cache.clear()
        self._rating_cache.clear()
        self._bg_cache = None
        self._processed_illust_cache.clear()
        self._executor.shutdown(wait=False)
        logger.info("🧹 PhigrosDesignSystem 资源已清理")
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """获取字体"""
        cache_key = f"{size}_{bold}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # 字体列表按优先级排序
        font_paths = []
        
        # 优先使用插件自带的字体
        plugin_font_dir = self.plugin_dir / "resources" / "font"
        if plugin_font_dir.exists():
            if bold:
                font_paths.extend([
                    str(plugin_font_dir / "SourceHanSansCN_&_SairaCondensed_Hybrid_Medium.ttf"),
                    str(plugin_font_dir / "taptap-sdk-bold.ttf"),
                    str(plugin_font_dir / "Aldrich-Regular.ttf"),
                ])
            else:
                font_paths.extend([
                    str(plugin_font_dir / "Source Han Sans & Saira Hybrid-Regular.ttf"),
                    str(plugin_font_dir / "taptap-sdk.ttf"),
                    str(plugin_font_dir / "NotoSans-Regular.ttf"),
                    str(plugin_font_dir / "Aldrich-Regular.ttf"),
                ])
        
        # 系统字体（作为回退）
        if bold:
            font_paths.extend([
                "C:/Windows/Fonts/msyhbd.ttc",
                "C:/Windows/Fonts/simsunb.ttf",
                "C:/Windows/Fonts/msgothic.ttc",
                "C:/Windows/Fonts/malgunbd.ttf",
            ])
        else:
            font_paths.extend([
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/msyhl.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msgothic.ttc",
                "C:/Windows/Fonts/malgun.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ])
        
        # Linux 字体
        font_paths.extend([
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ])
        
        # macOS 字体
        font_paths.extend([
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ])
        
        # 尝试加载字体
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, size)
                    self._font_cache[cache_key] = font
                    logger.debug(f"✅ 加载字体成功: {font_path}")
                    return font
                except Exception as e:
                    logger.debug(f"❌ 加载字体失败 {font_path}: {e}")
                    continue
        
        # 如果所有字体都失败，使用默认字体
        logger.warning(f"⚠️ 未找到合适的字体，使用默认字体")
        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font
    
    def _get_background_image(self, height: int, style: str = "default") -> Image.Image:
        """获取背景图片"""
        # 如果缓存的背景图高度不够，重新生成
        if self._bg_cache is None or self._bg_cache.height < height:
            # 根据风格选择背景
            bg_paths = {
                "default": self.plugin_dir / "resources" / "img" / "background" / "c774204e373ad3ab3a4137c7e5a930da.jpg",
                "history": self.plugin_dir / "resources" / "img" / "history" / "80aa4928e0cef4729d5c70336b5d892d.jpg"
            }
            
            bg_path = bg_paths.get(style, bg_paths["default"])
            
            if bg_path.exists():
                try:
                    # 使用更小的半径进行模糊，提升性能
                    bg_img = Image.open(bg_path).convert("RGBA")
                    # 先缩小再模糊，提升性能
                    scale_factor = 0.5
                    small_size = (int(self.LAYOUT['width'] * scale_factor), int(height * scale_factor))
                    bg_img = bg_img.resize(small_size, Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=3))
                    # 恢复到目标大小
                    bg_img = bg_img.resize((self.LAYOUT['width'], height), Image.Resampling.LANCZOS)
                    # 降低亮度
                    enhancer = ImageEnhance.Brightness(bg_img)
                    bg_img = enhancer.enhance(0.4)
                    self._bg_cache = bg_img
                    return bg_img.copy()
                except Exception as e:
                    logger.warning(f"加载背景图片失败: {e}")
            
            # 使用默认深色背景
            default_bg = Image.new('RGBA', (self.LAYOUT['width'], height), 
                                  self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            return default_bg
        else:
            # 使用缓存的背景图，裁剪到目标高度
            cached_bg = self._bg_cache.crop((0, 0, self.LAYOUT['width'], height))
            return cached_bg
    
    def _get_avatar(self, avatar_name: Optional[str] = None) -> Optional[Image.Image]:
        """获取头像"""
        # 如果指定了头像名，尝试加载
        if avatar_name:
            cache_key = avatar_name.lower()
            if cache_key in self._avatar_cache:
                return self._avatar_cache[cache_key].copy()
            
            # 查找头像文件
            for ext in ['.png', '.jpg', '.jpeg', '.gif']:
                avatar_file = self.avatar_path / f"{avatar_name}{ext}"
                if avatar_file.exists():
                    try:
                        img = Image.open(avatar_file).convert("RGBA")
                        self._avatar_cache[cache_key] = img.copy()
                        return img
                    except Exception as e:
                        logger.warning(f"加载头像失败 {avatar_name}: {e}")
            return None
        
        # 如果没有指定头像名，随机选择一个
        try:
            if self.avatar_path.exists():
                avatar_files = list(self.avatar_path.glob("*.png")) + \
                              list(self.avatar_path.glob("*.jpg")) + \
                              list(self.avatar_path.glob("*.jpeg")) + \
                              list(self.avatar_path.glob("*.gif"))
                if avatar_files:
                    import random
                    random_avatar = random.choice(avatar_files)
                    img = Image.open(random_avatar).convert("RGBA")
                    return img
        except Exception as e:
            logger.warning(f"随机选择头像失败: {e}")
        
        return None
    
    def _get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取曲绘"""
        # 提取原始歌曲名称
        import re
        match = re.match(r'^(.+?)_\d+$', song_key)
        if match:
            original_song_key = match.group(1)
        else:
            original_song_key = song_key
        
        song_key_lower = original_song_key.lower()
        
        # 检查缓存
        if song_key in self._illustration_cache:
            return self._illustration_cache[song_key].copy()
        
        # 查找可用曲绘
        matched_files = self._find_available_illustrations(song_key_lower)
        
        if not matched_files:
            # 如果没有找到可用曲绘，尝试传统匹配方式
            return self._find_illustration_fallback(original_song_key)
        
        # 选择一个未使用的曲绘
        selected_file = self._select_unused_illustration(song_key_lower, matched_files)
        
        if selected_file:
            try:
                img = Image.open(selected_file).convert("RGBA")
                self._illustration_cache[song_key] = img.copy()
                # 记录使用情况
                if song_key_lower not in self._illustration_usage:
                    self._illustration_usage[song_key_lower] = []
                self._illustration_usage[song_key_lower].append(str(selected_file))
                logger.info(f"✅ 找到曲绘: {original_song_key} -> {selected_file.name}")
                return img
            except Exception as e:
                logger.warning(f"加载曲绘失败 {original_song_key}: {e}")
        else:
            # 所有曲绘都已使用，返回第一个
            try:
                fallback_file = matched_files[0]
                img = Image.open(fallback_file).convert("RGBA")
                self._illustration_cache[song_key] = img.copy()
                logger.info(f"⚠️ 所有曲绘已使用，使用 fallback: {original_song_key} -> {fallback_file.name}")
                return img
            except Exception as e:
                logger.warning(f"加载 fallback 曲绘失败 {original_song_key}: {e}")
        
        return None
    
    def _find_available_illustrations(self, song_key_lower: str) -> List[Path]:
        """查找歌曲的所有可用曲绘"""
        available_files = []
        
        # 尝试精确匹配
        if song_key_lower in self._all_illustrations:
            available_files.extend(self._all_illustrations[song_key_lower])
        
        # 尝试包含匹配
        if not available_files:
            for song_name, files in self._all_illustrations.items():
                if song_key_lower in song_name or song_name in song_key_lower:
                    available_files.extend(files)
        
        # 尝试模糊匹配
        if not available_files:
            import re
            song_key_normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', song_key_lower)
            if song_key_normalized:
                for song_name, files in self._all_illustrations.items():
                    file_stem_normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', song_name)
                    if song_key_normalized in file_stem_normalized or file_stem_normalized in song_key_normalized:
                        available_files.extend(files)
        
        return available_files
    
    def _select_unused_illustration(self, song_key_lower: str, available_files: List[Path]) -> Optional[Path]:
        """选择一个未使用的曲绘"""
        used_files = self._illustration_usage.get(song_key_lower, [])
        
        for file in available_files:
            file_str = str(file)
            if file_str not in used_files:
                return file
        
        return None
    
    def _find_illustration_fallback(self, song_key: str) -> Optional[Image.Image]:
        """传统的曲绘查找方式"""
        song_key_lower = song_key.lower()
        matched_file = None

        # 获取所有图片文件
        all_image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
            all_image_files.extend(self.illustration_path.glob(ext))
            # 大小写敏感处理
            all_image_files.extend(self.illustration_path.glob(ext.upper()))

        # 首先尝试精确匹配
        for file in all_image_files:
            file_stem_lower = file.stem.lower()
            if song_key_lower == file_stem_lower:
                matched_file = file
                break

        # 如果没有精确匹配，尝试包含匹配
        if not matched_file:
            for file in all_image_files:
                file_stem_lower = file.stem.lower()
                if song_key_lower in file_stem_lower:
                    matched_file = file
                    break

        # 如果仍然没有匹配，尝试模糊匹配
        if not matched_file:
            import re
            # 去除空格和特殊字符
            song_key_normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', song_key_lower)
            if song_key_normalized:
                for file in all_image_files:
                    file_stem_normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', file.stem.lower())
                    if song_key_normalized in file_stem_normalized or file_stem_normalized in song_key_normalized:
                        matched_file = file
                        break

        if matched_file:
            try:
                img = Image.open(matched_file).convert("RGBA")
                self._illustration_cache[song_key] = img.copy()
                logger.info(f"✅ 找到曲绘 (fallback): {song_key} -> {matched_file.name}")
                return img
            except Exception as e:
                logger.warning(f"加载曲绘失败 {song_key}: {e}")
        else:
            logger.warning(f"未找到曲绘: {song_key}")

        return None
    
    def _get_rating_image(self, rating: str) -> Optional[Image.Image]:
        """获取评级图片"""
        if rating in self._rating_cache:
            return self._rating_cache[rating].copy()
        
        # 评级图片文件名映射
        rating_files = {
            'φ': 'φ.png',
            'V': 'V.png',
            'S': 'S.png',
            'A': 'A.png',
            'B': 'B.png',
            'C': 'C.png',
            'F': 'F.png',
            'FC': 'FC.png',
        }
        
        filename = rating_files.get(rating)
        if not filename:
            return None
        
        img_path = self.rating_path / filename
        if img_path.exists():
            try:
                img = Image.open(img_path).convert("RGBA")
                self._rating_cache[rating] = img.copy()
                return img
            except Exception as e:
                logger.warning(f"加载评级图片失败 {rating}: {e}")
        
        return None
    
    def _calculate_rating(self, score: int, acc: float, fc: bool) -> str:
        """根据分数和ACC计算评级"""
        if score == 1000000:
            return 'φ'
        elif fc:
            return 'V'
        elif acc >= 99.00:
            return 'S'
        elif acc >= 95.00:
            return 'A'
        elif acc >= 90.00:
            return 'B'
        elif acc >= 80.00:
            return 'C'
        else:
            return 'F'
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int, int]:
        """十六进制颜色转 RGBA"""
        # 处理 rgba 格式
        if hex_color.startswith('rgba'):
            import re
            match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\)', hex_color)
            if match:
                r, g, b, a = match.groups()
                return (int(r), int(g), int(b), int(float(a) * 255))
        
        # 处理十六进制格式
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, 255)
        elif len(hex_color) == 8:
            r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
        return (0, 0, 0, 255)
    
    def _draw_rounded_rect(self, draw: ImageDraw.Draw, xy: Tuple[int, int, int, int], 
                          radius: int, fill: Tuple[int, int, int, int]):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = xy
        # 主体矩形
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        # 四个圆角
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    def _draw_text_safe(self, draw: ImageDraw.Draw, xy, text: str, fill, font: ImageFont.FreeTypeFont, anchor=None):
        """安全绘制文本"""
        try:
            # 尝试直接绘制
            if anchor:
                draw.text(xy, text, fill=fill, font=font, anchor=anchor)
            else:
                draw.text(xy, text, fill=fill, font=font)
        except UnicodeEncodeError:
            # 如果有编码错误，尝试过滤掉无法显示的字符
            logger.warning(f"文本包含无法显示的字符: {text}")
            # 只保留基本字符
            safe_text = ''.join(c for c in text if ord(c) < 65536)
            if not safe_text:
                safe_text = "?"
            try:
                if anchor:
                    draw.text(xy, safe_text, fill=fill, font=font, anchor=anchor)
                else:
                    draw.text(xy, safe_text, fill=fill, font=font)
            except:
                pass
        except Exception as e:
            logger.warning(f"绘制文本失败 '{text}': {e}")
    
    def _create_rounded_rectangle(self, size: Tuple[int, int], radius: int, 
                                   color: Tuple[int, ...]) -> Image.Image:
        """创建圆角矩形"""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=color)
        return img
    
    def _draw_text_with_glow(self, img: Image.Image, x: int, y: int, text: str, 
                              text_color: str, font: ImageFont.FreeTypeFont, 
                              glow_color: Tuple[int, int, int] = (255, 255, 255),
                              glow_radius: int = 4, anchor: str = None):
        """绘制带发光效果的文字"""
        draw = ImageDraw.Draw(img)
        
        # 计算文本边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 确定发光层的大小和位置
        padding = glow_radius * 2
        layer_width = text_width + padding * 2
        layer_height = text_height + padding * 2
        
        # 计算发光层的粘贴位置
        if anchor == 'mm':
            layer_x = x - layer_width // 2
            layer_y = y - layer_height // 2
        else:
            layer_x = x - padding
            layer_y = y - padding
        
        # 绘制发光效果
        for offset in range(glow_radius, 0, -1):
            alpha = int(40 - offset * 8)
            if alpha <= 0:
                continue
            # 创建一个只包含文本区域的图层
            glow_layer = Image.new('RGBA', (layer_width, layer_height), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            
            # 调整文本在发光层中的位置
            text_x = padding
            text_y = padding
            
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset),
                          (-offset, -offset), (offset, -offset), (-offset, offset), (offset, offset)]:
                glow_draw.text((text_x + dx, text_y + dy), text, fill=(*glow_color, alpha), font=font)
            
            # 模糊发光层
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=offset))
            
            # 粘贴到目标位置
            img.paste(glow_layer, (int(layer_x), int(layer_y)), glow_layer)
        
        if anchor:
            draw.text((x, y), text, fill=text_color, font=font, anchor=anchor)
        else:
            draw.text((x, y), text, fill=text_color, font=font)
    
    # ========== 可重用组件 ==========
    
    def draw_header(self, img: Image.Image, draw: ImageDraw.Draw, gameuser: Dict):
        """绘制头部（玩家信息）"""
        # 头像区域（圆形）
        avatar_size = 100
        avatar_x = 60
        avatar_y = (self.LAYOUT['header_height'] - avatar_size) // 2
        
        # 尝试加载头像
        api_avatar = gameuser.get('avatar', '')
        avatar_img = None
        if api_avatar:
            avatar_img = self._get_avatar(api_avatar)
        if not avatar_img:
            # 如果 API 头像加载失败，随机选择一个
            avatar_img = self._get_avatar()
        if avatar_img:
            # 缩放头像
            avatar_resized = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            # 创建圆形遮罩
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            # 应用遮罩
            avatar_resized.putalpha(mask)
            # 粘贴头像
            img.paste(avatar_resized, (avatar_x, avatar_y), avatar_resized)
            # 绘制边框
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
                        outline='white', width=3)
        else:
            # 头像背景圆（默认）
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
                        fill='#333333', outline='white', width=3)
        
        # 玩家信息
        info_x = avatar_x + avatar_size + 25
        
        # 课题模式段位
        challenge_rank = gameuser.get('challengeModeRank', 0)
        rank_badge_width = 0
        rank_img_resized = None
        
        # 处理课题模式段位
        if challenge_rank:
            # 根据难度总和确定段位颜色
            if challenge_rank >= 450:
                rank_name = "彩色"
            elif challenge_rank >= 420:
                rank_name = "金色"
            elif challenge_rank >= 390:
                rank_name = "红色"  # 橙
            elif challenge_rank >= 360:
                rank_name = "蓝色"
            elif challenge_rank >= 330:
                rank_name = "绿色"
            else:
                rank_name = "白色"
            
            # 加载段位颜色图片
            rank_img_path = self.plugin_dir / "resources" / "img" / "other" / f"{rank_name}.png"
            if rank_img_path.exists():
                try:
                    rank_img = Image.open(rank_img_path).convert("RGBA")
                    # 调整大小
                    badge_height = 36
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 15  # 徽章宽度 + 间距
                except Exception as e:
                    logger.warning(f"加载段位图片失败: {e}")
            else:
                # 尝试使用默认段位图片
                try:
                    default_rank_path = self.plugin_dir / "resources" / "img" / "other" / "白色.png"
                    if default_rank_path.exists():
                        rank_img = Image.open(default_rank_path).convert("RGBA")
                        badge_height = 36
                        badge_width = int(badge_height * rank_img.width / rank_img.height)
                        rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                        rank_badge_width = badge_width + 15
                except Exception as e:
                    logger.warning(f"加载默认段位图片失败: {e}")
        else:
            # 尝试使用默认段位图片
            try:
                default_rank_path = self.plugin_dir / "resources" / "img" / "other" / "白色.png"
                if default_rank_path.exists():
                    rank_img = Image.open(default_rank_path).convert("RGBA")
                    badge_height = 36
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 15
            except Exception as e:
                logger.warning(f"加载默认段位图片失败: {e}")
        
        # 在昵称左侧显示段位徽章
        if rank_img_resized:
            badge_x = info_x
            badge_y = avatar_y + 10  # 与昵称垂直居中对齐
            img.paste(rank_img_resized, (badge_x, badge_y), rank_img_resized)
            # 在段位图片上绘制段位数字
            font_rank = self._get_font(22, bold=True)
            # 显示段位等级的前两位数字
            rank_text = str(challenge_rank)[:2] if challenge_rank else "1"
            # 计算文本位置
            text_bbox = draw.textbbox((0, 0), rank_text, font=font_rank)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            # 确保数字在段位框内居中显示
            text_x = badge_x + (rank_img_resized.width - text_width) // 2
            text_y = badge_y + (rank_img_resized.height - text_height) // 2
            # 绘制文本阴影
            draw.text((text_x + 1, text_y + 1), rank_text, fill=(0, 0, 0, 200), font=font_rank)
            # 绘制文本
            draw.text((text_x, text_y), rank_text, fill=(255, 255, 255, 255), font=font_rank)
        
        # 昵称
        font_name = self._get_font(self.FONT_CONFIG['sizes']['md'] + 4, bold=True)
        nickname = gameuser.get('nickname', '')
        if not nickname or nickname == 'Unknown':
            nickname = gameuser.get('name', '') or gameuser.get('alias', '') or 'Phigros Player'
        if len(nickname) > 20:
            nickname = nickname[:18] + '...'
        
        # 昵称位置
        nickname_x = info_x + rank_badge_width
        nickname_y = avatar_y + 15
        self._draw_text_safe(draw, (nickname_x, nickname_y), nickname, 
                           fill=(255, 255, 255, 255), font=font_name)
        
        # ID
        font_id = self._get_font(self.FONT_CONFIG['sizes']['md'])
        player_id = gameuser.get('PlayerId', '')
        if not player_id or player_id == 'N/A':
            player_id = gameuser.get('playerId', '') or gameuser.get('id', '') or gameuser.get('uid', '')
        if not player_id or player_id == 'N/A':
            player_id = "TapTap User"
        if len(player_id) > 30:
            player_id = player_id[:27] + '...'
        self._draw_text_safe(draw, (info_x, avatar_y + 45), f"ID: {player_id}", 
                           fill=(200, 200, 200, 255), font=font_id)
        
        # RKS 显示
        rks_width = 200
        rks_height = 40
        rks_x = info_x
        rks_y = avatar_y + 70
        
        # RKS 文字
        font_rks_label = self._get_font(self.FONT_CONFIG['sizes']['md'], bold=True)
        font_rks_value = self._get_font(self.FONT_CONFIG['sizes']['md'] + 6, bold=True)
        rks = gameuser.get('rks', 0)
        
        # 计算文本位置
        label_width = draw.textlength("RKS", font=font_rks_label)
        value_width = draw.textlength(f"{rks:.4f}", font=font_rks_value)
        
        # 居中对齐
        start_x = rks_x
        
        # 使用白色文字
        draw.text((start_x, rks_y + rks_height // 2), "RKS", 
                 fill=(255, 255, 255, 255), font=font_rks_label, anchor='lm')
        draw.text((start_x + label_width + 15, rks_y + rks_height // 2), f"{rks:.4f}", 
                 fill=(255, 255, 255, 255), font=font_rks_value, anchor='lm')
        
        # 添加logo到头部右侧
        logo_path = self.plugin_dir / "resources" / "img" / "logo" / "phi.png"
        if logo_path.exists():
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                # 调整logo大小
                logo_size = 100
                logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                # 计算位置
                logo_x = self.LAYOUT['width'] - logo_size - 140
                logo_y = (self.LAYOUT['header_height'] - logo_size) // 2
                # 粘贴logo
                img.paste(logo_img, (logo_x, logo_y), logo_img)
                
                # 在logo下方添加文字
                logo_text = "xtower.site提供支持"
                font_logo_text = self._get_font(self.FONT_CONFIG['sizes']['sm'])
                # 计算文字位置
                text_x = logo_x + logo_size // 2
                text_y = logo_y + logo_size + 12
                # 使用发光效果
                self._draw_text_with_glow(img, text_x, text_y, logo_text, '#aaaaaa', font_logo_text,
                                         glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
            except Exception as e:
                logger.warning(f"加载logo失败: {e}")
    
    def draw_song_card(self, img: Image.Image, draw: ImageDraw.Draw, rank: Optional[int], 
                       record: Dict, x: int, y: int):
        """绘制歌曲卡片"""
        card_width = self.LAYOUT['card_width']
        card_height = self.LAYOUT['card_height']
        illust_width = card_width // 2
        illust_height = card_height
        
        # 尝试加载曲绘
        song = record.get('song', '')
        index = record.get('__index__', 0)
        cache_key = f"{song.lower()}_{index}"
        illust = self._processed_illust_cache.get(cache_key)
        
        if illust:
            # 确保曲绘是RGBA模式
            if illust.mode != 'RGBA':
                illust = illust.convert('RGBA')
            # 创建一个半透明的曲绘副本
            illust_with_alpha = Image.new('RGBA', illust.size, (255, 255, 255, 200))
            illust_with_alpha.paste(illust, (0, 0), illust)
            img.paste(illust_with_alpha, (x, y), illust_with_alpha)
        else:
            # 回退：绘制渐变占位符
            for i in range(illust_height):
                brightness = int(60 + (20 * i / illust_height))
                draw.line([(x, y + i), (x + illust_width, y + i)], 
                         fill=(brightness, brightness, brightness + 20, 150))
            # 添加难度对应的边框
            diff = record.get('difficulty', 'IN')
            diff_color = self.DESIGN_LANGUAGE['difficulty'].get(diff, self.DESIGN_LANGUAGE['difficulty']['IN'])
            draw.rectangle([x, y, x + 3, y + illust_height], fill=self._hex_to_rgb(diff_color))
            draw.rectangle([x + illust_width - 3, y, x + illust_width, y + illust_height], fill=self._hex_to_rgb(diff_color))
        
        # 排名徽章（仅在有排名时绘制）
        if rank is not None:
            rank_colors = {1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32'}
            rank_bg = rank_colors.get(rank, '#ffffff')
            draw.rectangle([x - 5, y - 5, x + 45, y + 13], fill=self._hex_to_rgb(rank_bg))
            font_rank = self._get_font(self.FONT_CONFIG['sizes']['xs'], bold=True)
            draw.text((x + 20, y + 4), str(rank), fill='black', font=font_rank, anchor='mm')
        
        # 难度标签
        diff = record.get('difficulty', 'IN')
        diff_color = self.DESIGN_LANGUAGE['difficulty'].get(diff, self.DESIGN_LANGUAGE['difficulty']['IN'])
        draw.rectangle([x + 5, y + illust_height - 27, x + 50, y + illust_height - 5],
                      fill=self._hex_to_rgb(diff_color))
        font_diff = self._get_font(self.FONT_CONFIG['sizes']['sm'], bold=True)
        draw.text((x + 27, y + illust_height - 16), diff, fill='white', font=font_diff, anchor='mm')
        
        # 信息卡片
        info_x = x + illust_width - 15
        info_width = card_width - illust_width + 15
        info_height = card_height - 10
        info_y = y + 5
        
        # 绘制背景和边框
        bg_color = (40, 40, 55, 60)
        # 绘制信息卡背景
        self._draw_rounded_rect(draw,
                               (info_x, info_y, info_x + info_width, info_y + info_height),
                               5, bg_color)
        
        # 绘制左侧边框
        draw.rectangle([info_x, info_y, info_x + 4, info_y + info_height],
                      fill=self._hex_to_rgb(diff_color))
        # 添加边框高亮
        draw.rectangle([info_x + 1, info_y + 1, info_x + 2, info_y + info_height - 1],
                      fill=(255, 255, 255, 100))
        
        # 文字信息
        font_song = self._get_font(self.FONT_CONFIG['sizes']['sm'], bold=True)
        song_name = record.get('song', 'Unknown')
        if len(song_name) > 14:
            song_name = song_name[:12] + '...'
        # 增强发光效果
        self._draw_text_with_glow(img, info_x + 10, info_y + 6, song_name, 'white', font_song,
                                  glow_color=(50, 150, 255), glow_radius=2)
        
        font_score = self._get_font(self.FONT_CONFIG['sizes']['md'], bold=True)
        score = record.get('score', 0)
        # 分数发光效果增强
        self._draw_text_with_glow(img, info_x + 10, info_y + 28, f"{score:,}", '#ffd700', font_score,
                                  glow_color=(255, 215, 0), glow_radius=2)
        
        # 增强 Acc 和 RKS 文字
        font_acc = self._get_font(self.FONT_CONFIG['sizes']['xs'], bold=False)
        acc = record.get('acc', 0)
        rks = record.get('rks', 0)
        # Acc 颜色根据值变化
        acc_color = '#00ff00' if acc >= 95 else '#ffff00' if acc >= 90 else '#ff8c00' if acc >= 80 else '#ff0000'
        draw.text((info_x + 10, info_y + 50), f"Acc: {acc:.2f}%", fill=acc_color, font=font_acc)
        # RKS 使用浅蓝色
        draw.text((info_x + 10, info_y + 63), f"RKS: {rks:.2f}", fill='#66ccff', font=font_acc)
        
        # 评级图片
        rating = self._calculate_rating(score, acc, record.get('fc', False))
        rating_img = self._get_rating_image(rating)
        if rating_img:
            rating_height = 40
            rating_width = int(rating_height * rating_img.width / rating_img.height)
            rating_resized = rating_img.resize((rating_width, rating_height), Image.Resampling.LANCZOS)
            rating_x = info_x + info_width - rating_width - 10
            rating_y = info_y + (info_height - rating_height) // 2
            # 直接粘贴评级图片
            img.paste(rating_resized, (rating_x, rating_y), rating_resized)
        
        # FC/AP 标识
        if record.get('fc'):
            score_val = record.get('score', 0)
            fc_text = 'AP' if score_val == 1000000 else 'FC'
            fc_color = '#ffd700' if score_val == 1000000 else '#00b0f0'
            # 绘制标识
            draw.rectangle([x + illust_width - 33, y + 5, x + illust_width - 5, y + 23],
                          fill=self._hex_to_rgb(fc_color))
            font_fc = self._get_font(self.FONT_CONFIG['sizes']['xs'], bold=True)
            draw.text((x + illust_width - 19, y + 14), fc_text,
                     fill='black' if score_val == 1000000 else 'white',
                     font=font_fc, anchor='mm')
    
    def draw_overflow_section(self, img: Image.Image, draw: ImageDraw.Draw, 
                             records: List[Dict], start_y: int, col_x_positions: List[int]):
        """绘制 Overflow 区域"""
        # 绘制 Overflow 标题栏
        title_height = self.LAYOUT['overflow_header_height']
        title_y = start_y
        
        center_x = self.LAYOUT['width'] // 2
        
        # 装饰性线条
        line_width = 280
        line_gap = 60
        
        # 左线条
        draw.rectangle([center_x - line_width - line_gap - 60, title_y + title_height // 2 - 2,
                       center_x - line_gap - 60, title_y + title_height // 2 + 2],
                      fill=(255, 255, 255, 200))
        
        # 右线条
        draw.rectangle([center_x + line_gap + 60, title_y + title_height // 2 - 2,
                       center_x + line_width + line_gap + 60, title_y + title_height // 2 + 2],
                      fill=(255, 255, 255, 200))
        
        # Overflow 文字
        font_title = self._get_font(self.FONT_CONFIG['sizes']['lg'], bold=True)
        self._draw_text_with_glow(img, center_x, title_y + title_height // 2, 
                                  "OVER FLOW", '#ffffff', font_title,
                                  glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
        
        # 绘制 Overflow 记录卡片
        card_start_y = title_y + title_height + 10
        overflow_records = records[:3]  # 严格限制只显示3首歌曲
        
        # 使用固定列位置
        for i, record in enumerate(overflow_records):
            x = col_x_positions[i] if i < len(col_x_positions) else 20 + i * (self.LAYOUT['card_width'] + self.LAYOUT['card_margin'])
            y = card_start_y
            # Overflow 卡片不显示排名
            self.draw_song_card(img, draw, None, record, x, y)
    
    def draw_footer(self, img: Image.Image, draw: ImageDraw.Draw, y: int):
        """绘制底部"""
        text = "phigros插件——飞翔的死猪提供技术支持"
        font = self._get_font(self.FONT_CONFIG['sizes']['sm'], bold=False)
        self._draw_text_with_glow(img, self.LAYOUT['width'] // 2, y, text, '#aaaaaa', font,
                                  glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
    
    # ========== 模板系统 ==========
    
    async def render_b30(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染 Best30 成绩图"""
        logger.info(f"🎨 开始渲染 Best30，玩家: {data.get('gameuser', {}).get('nickname', 'Unknown')}")
        
        try:
            gameuser = data.get('gameuser', {})
            all_records = data.get('records', [])
            main_records = all_records[:26]
            overflow_records = all_records[26:50] if len(all_records) > 26 else []
            
            if not main_records:
                logger.error("❌ 没有成绩记录可渲染")
                return False
            
            # 为每个记录添加索引信息
            for i, record in enumerate(all_records):
                record['__index__'] = i
            
            num_cols = 3
            num_rows = (len(main_records) + num_cols - 1) // num_cols
            main_content_height = num_rows * (self.LAYOUT['card_height'] + self.LAYOUT['card_margin'])
            
            overflow_height = 0
            if overflow_records:
                overflow_height = (self.LAYOUT['card_height'] + self.LAYOUT['card_margin']) + self.LAYOUT['overflow_header_height']
            
            total_height = self.LAYOUT['header_height'] + main_content_height + overflow_height + 80
            
            # 预加载曲绘
            await self._preload_illustrations(all_records)
            
            # 创建图片
            img = Image.new('RGBA', (self.LAYOUT['width'], total_height), 
                          self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(total_height)
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制头部
            self.draw_header(img, draw, gameuser)
            
            # 绘制主内容区
            start_y = self.LAYOUT['header_height'] + 20
            col_x_positions = [20, 390, 760]
            
            for i, record in enumerate(main_records):
                col = i % num_cols
                row = i // num_cols
                x = col_x_positions[col]
                y = start_y + row * (self.LAYOUT['card_height'] + self.LAYOUT['card_margin'])
                self.draw_song_card(img, draw, i + 1, record, x, y)
            
            # 绘制 Overflow 区域
            overflow_start_y = start_y + main_content_height + 10
            if overflow_records:
                self.draw_overflow_section(img, draw, overflow_records, overflow_start_y, col_x_positions)
            
            # 绘制底部
            footer_y = overflow_start_y + overflow_height + 20 if overflow_records else start_y + main_content_height + 20
            self.draw_footer(img, draw, footer_y)
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        logger.info(f"🎨 开始渲染单曲成绩")
        
        try:
            # 提取数据
            gameuser = data.get('gameuser', {})
            record = data.get('record', {})
            
            if not record:
                logger.error("❌ 没有成绩记录可渲染")
                return False
            
            # 为记录添加索引信息
            record['__index__'] = 0
            
            # 计算高度
            total_height = 400
            
            # 预加载曲绘
            await self._preload_illustrations([record])
            
            # 创建图片
            img = Image.new('RGBA', (self.LAYOUT['width'], total_height), 
                          self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(total_height)
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制头部
            self.draw_header(img, draw, gameuser)
            
            # 绘制单曲卡片
            card_x = (self.LAYOUT['width'] - self.LAYOUT['card_width']) // 2
            card_y = self.LAYOUT['header_height'] + 30
            self.draw_song_card(img, draw, None, record, card_x, card_y)
            
            # 绘制底部
            footer_y = card_y + self.LAYOUT['card_height'] + 40
            self.draw_footer(img, draw, footer_y)
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 单曲成绩渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def render_leaderboard(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染排行榜"""
        try:
            logger.info("🎨 开始渲染排行榜")
            
            # 提取数据
            items = data.get('items', [])
            
            if not items:
                logger.warning("无排行榜数据")
                return False
            
            # 计算高度
            total_height = 200 + len(items) * 70
            
            # 创建图片
            img = Image.new('RGBA', (self.LAYOUT['width'], total_height), 
                          self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(total_height)
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制标题
            title_font = self._get_font(self.FONT_CONFIG['sizes']['xl'], bold=True)
            self._draw_text_with_glow(img, self.LAYOUT['width'] // 2, 60, 
                                      "🏆 Phigros RKS 排行榜", '#ffffff', title_font,
                                      glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
            
            # 绘制排行榜项
            y_offset = 120
            for i, item in enumerate(items[:15]):
                rank = item.get('rank', 0)
                alias = item.get('alias', '未知')
                score = item.get('score', 0)
                
                # 排名颜色
                rank_colors = {
                    1: (255, 215, 0, 200),    # 金牌
                    2: (192, 192, 192, 200),  # 银牌
                    3: (205, 127, 50, 200)    # 铜牌
                }
                rank_color = rank_colors.get(rank, (100, 100, 100, 150))
                
                # 排名标签
                rank_bg = self._create_rounded_rectangle((60, 50), 12, rank_color)
                img.paste(rank_bg, (60, y_offset), rank_bg)
                font_rank = self._get_font(self.FONT_CONFIG['sizes']['md'], bold=True)
                self._draw_text_safe(draw, (75, y_offset + 8), str(rank), 
                                   fill=(0, 0, 0, 255), font=font_rank)
                
                # 玩家卡片
                card = self._create_rounded_rectangle((900, 55), 15, (0, 0, 0, 130))
                img.paste(card, (140, y_offset - 2), card)
                
                # 玩家信息
                font_alias = self._get_font(self.FONT_CONFIG['sizes']['md'], bold=True)
                self._draw_text_with_glow(img, 160, y_offset + 8, alias, '#ffffff', font_alias,
                                          glow_color=(100, 200, 255), glow_radius=2)
                
                font_rks = self._get_font(self.FONT_CONFIG['sizes']['sm'], bold=True)
                self._draw_text_with_glow(img, 700, y_offset + 12, f"RKS: {score:.4f}", '#ffd700', font_rks,
                                          glow_color=(255, 215, 0), glow_radius=2)
                
                y_offset += 70
            
            # 绘制底部
            footer_y = y_offset + 40
            self.draw_footer(img, draw, footer_y)
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 排行榜渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def render_rks_history(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染 RKS 历史趋势图"""
        try:
            logger.info(f"🎨 开始渲染 RKS 历史趋势图")
            
            # 提取数据
            items = data.get('items', [])
            current_rks = data.get('currentRks', 0)
            peak_rks = data.get('peakRks', 0)
            total = data.get('total', 0)
            gameuser = data.get('gameuser', {})
            
            if not items:
                logger.warning("无 RKS 历史数据")
                return False
            
            # 准备数据点
            dates = []
            rks_values = []
            for item in items:
                date_str = item.get('createdAt', '')[:10]
                rks = item.get('rks', 0)
                dates.append(date_str)
                rks_values.append(rks)
            
            # 反转数据，使时间从左到右递增
            dates.reverse()
            rks_values.reverse()
            
            # 计算图表尺寸
            width = self.LAYOUT['width']
            height = 600
            padding = 80
            chart_width = width - 2 * padding
            chart_height = height - 2 * padding
            
            # 创建图片
            img = Image.new('RGBA', (width, height), 
                          self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(height, "history")
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制头部信息
            if gameuser:
                # 简化版头部
                pass
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ RKS 历史趋势图渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def render_save_data(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染存档数据"""
        try:
            logger.info(f"🎨 开始渲染存档数据")
            
            # 提取数据
            save = data.get("save", {})
            game_record = save.get("game_record", {})
            summary = data.get("summary", {})
            gameuser = data.get("gameuser", {})
            
            rks = summary.get("rks", 0)
            peak_rks = summary.get("peakRks", 0)
            
            # 构建游戏用户信息
            if not gameuser:
                gameuser = {
                    "nickname": "Phigros Player",
                    "rks": rks,
                    "peakRks": peak_rks
                }
            
            # 为记录添加索引和格式化信息
            records = []
            for song_key, song_records in list(game_record.items())[:24]:
                if song_records:
                    record = song_records[0]
                    records.append({
                        "song": song_key.split(".")[0] if "." in song_key else song_key,
                        "difficulty": record.get("difficulty", "?").upper(),
                        "score": record.get("score", 0),
                        "acc": record.get("accuracy", 0),
                        "rks": record.get("rks", 0),
                        "fc": record.get("fc", False),
                        "__index__": len(records)
                    })
            
            # 计算高度
            num_cols = 3
            num_rows = (len(records) + num_cols - 1) // num_cols
            main_content_height = num_rows * (self.LAYOUT['card_height'] + self.LAYOUT['card_margin'])
            total_height = self.LAYOUT['header_height'] + main_content_height + 80
            
            # 预加载曲绘
            await self._preload_illustrations(records)
            
            # 创建图片
            img = Image.new('RGBA', (self.LAYOUT['width'], total_height), 
                          self._hex_to_rgb(self.DESIGN_LANGUAGE['theme']['bg']))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(total_height)
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制头部
            self.draw_header(img, draw, gameuser)
            
            # 绘制主内容区
            start_y = self.LAYOUT['header_height'] + 20
            col_x_positions = [20, 390, 760]
            
            for i, record in enumerate(records):
                col = i % num_cols
                row = i // num_cols
                x = col_x_positions[col]
                y = start_y + row * (self.LAYOUT['card_height'] + self.LAYOUT['card_margin'])
                self.draw_song_card(img, draw, i + 1, record, x, y)
            
            # 绘制底部
            footer_y = start_y + main_content_height + 20
            self.draw_footer(img, draw, footer_y)
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 存档数据渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    async def _preload_illustrations(self, records: List[Dict]):
        """并行预加载曲绘"""
        # 重置曲绘使用记录
        self._illustration_usage = {}
        
        # 统计每首歌曲出现的次数
        song_counts = {}
        for record in records:
            song_name = record.get('song', '')
            if song_name:
                song_key = song_name.lower()
                song_counts[song_key] = song_counts.get(song_key, 0) + 1
        
        async def load_single(record: Dict, index: int) -> Tuple[str, Optional[Image.Image]]:
            song_name = record.get('song', '')
            if not song_name:
                return '', None

            # 在线程池中加载图片
            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(
                self._executor,
                self._load_and_process_illustration,
                song_name,
                index
            )
            return song_name.lower(), img
        
        # 并行加载所有曲绘
        tasks = [load_single(record, i) for i, record in enumerate(records)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 存储到缓存
        for i, result in enumerate(results):
            if isinstance(result, tuple) and result[1] is not None:
                song_key = result[0]
                # 使用带索引的缓存键，确保相同歌曲的不同实例使用不同的曲绘
                cache_key = f"{song_key}_{i}"
                self._processed_illust_cache[cache_key] = result[1]

        logger.info(f"✅ 预加载完成: {len(self._processed_illust_cache)} 张曲绘")
    
    def _load_and_process_illustration(self, song_name: str, index: int = 0) -> Optional[Image.Image]:
        """在线程中加载和处理曲绘"""
        try:
            # 尝试多种方式查找曲绘
            song_key = f"{song_name}_{index}"
            illust = self._get_illustration(song_key)
            if illust:
                # 确保曲绘是RGBA模式
                if illust.mode != 'RGBA':
                    illust = illust.convert('RGBA')
                # 预先调整大小
                target_height = self.LAYOUT['card_height']
                aspect_ratio = illust.width / illust.height
                target_width = int(target_height * aspect_ratio)
                return illust.resize((target_width, target_height), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.debug(f"预加载曲绘失败 {song_name}: {e}")
        return None
    
    def create_template(self, template_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建模板数据结构
        
        Args:
            template_type: 模板类型 (b30, score, rks_history)
            data: 原始数据
            
        Returns:
            格式化后的模板数据
        """
        templates = {
            'b30': {
                'gameuser': data.get('gameuser', {}),
                'records': data.get('records', []),
                'timestamp': datetime.now().isoformat()
            },
            'score': {
                'gameuser': data.get('gameuser', {}),
                'record': data.get('record', {}),
                'timestamp': datetime.now().isoformat()
            },
            'rks_history': {
                'gameuser': data.get('gameuser', {}),
                'items': data.get('items', []),
                'currentRks': data.get('currentRks', 0),
                'peakRks': data.get('peakRks', 0),
                'total': data.get('total', 0),
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return templates.get(template_type, {})
    
    async def render_from_template(self, template_type: str, data: Dict[str, Any], output_path: Path) -> bool:
        """从模板渲染图片
        
        Args:
            template_type: 模板类型 (b30, score, rks_history)
            data: 模板数据
            output_path: 输出路径
            
        Returns:
            是否渲染成功
        """
        render_functions = {
            'b30': self.render_b30,
            'score': self.render_score,
            'rks_history': self.render_rks_history
        }
        
        render_func = render_functions.get(template_type)
        if not render_func:
            logger.error(f"未知的模板类型: {template_type}")
            return False
        
        return await render_func(data, output_path)
    
    def get_difficulty_color(self, difficulty: str) -> str:
        """获取难度对应的颜色
        
        Args:
            difficulty: 难度级别 (EZ, HD, IN, AT)
            
        Returns:
            颜色的十六进制表示
        """
        return self.DESIGN_LANGUAGE['difficulty'].get(difficulty, self.DESIGN_LANGUAGE['difficulty']['IN'])
    
    def get_theme_color(self, color_name: str) -> str:
        """获取主题颜色
        
        Args:
            color_name: 颜色名称
            
        Returns:
            颜色的十六进制表示
        """
        return self.DESIGN_LANGUAGE['theme'].get(color_name, self.DESIGN_LANGUAGE['theme']['bg'])
    
    def get_function_color(self, color_name: str) -> str:
        """获取功能颜色
        
        Args:
            color_name: 颜色名称
            
        Returns:
            颜色的十六进制表示
        """
        return self.DESIGN_LANGUAGE['function'].get(color_name, self.DESIGN_LANGUAGE['function']['info'])
