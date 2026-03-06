"""
🎨 Phi-Plugin 风格渲染器

> "完美还原 phi-plugin 的视觉效果！" ✨

参考 phi-plugin 的 b19.css 设计，精确还原：
- 三列交错布局（L/M/R 三列，M和R有偏移）
- 曲绘+信息卡片的组合设计
- 难度颜色区分（EZ/HD/IN/AT）
- 排名徽章和 FC/AP 标识
- 特殊的边框和阴影效果
"""

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
# 尝试导入 astrbot 日志，如果失败则使用标准日志
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


class PhiStyleRenderer:
    """
    🎨 Phi-Plugin 风格渲染器
    
    精确还原 phi-plugin 的 b30 设计
    """
    
    # 颜色定义（来自 phi-plugin 的 CSS，精确匹配）
    COLORS = {
        'EZ': '#92d050',
        'HD': '#00b0f0', 
        'IN': '#ff0000',
        'AT': '#6e6e6e',
        'bg': '#1a1a2e',
        'card_bg': 'rgba(0, 0, 0, 0.6)',
        'text_white': '#ffffff',
        'text_gray': '#aaaaaa',
    }
    
    # 布局常量（优化紧凑布局）
    WIDTH = 1200
    HEADER_HEIGHT = 180  # 减小头部高度
    CARD_WIDTH = 350  # 减小卡片宽度
    CARD_HEIGHT = 90   # 减小卡片高度
    CARD_MARGIN = 8    # 减小卡片间距
    OVERFLOW_HEADER_HEIGHT = 120  # 减小overflow头部高度
    
    def __init__(self,
                 plugin_dir: Path,
                 cache_dir: Path,
                 illustration_path: Path,
                 image_quality: int = 95,
                 avatar_path: Optional[Path] = None):
        """初始化渲染器"""
        self.plugin_dir = plugin_dir
        self.cache_dir = cache_dir
        self.illustration_path = illustration_path
        self.image_quality = image_quality
        self.avatar_path = avatar_path or (plugin_dir / "AVATAR")

        # 字体缓存
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}

        # 曲绘缓存
        self._illustration_cache: Dict[str, Image.Image] = {}

        # 头像缓存
        self._avatar_cache: Dict[str, Image.Image] = {}

        # 评级图片缓存
        self._rating_cache: Dict[str, Image.Image] = {}

        # 评级图片路径
        self.rating_path = plugin_dir / "resources" / "img" / "rating"

        # 背景图片缓存
        self._bg_cache: Optional[Image.Image] = None

        # 线程池（用于并行加载图片）
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 曲绘预加载缓存（存储处理后的曲绘）
        self._processed_illust_cache: Dict[str, Image.Image] = {}

        logger.info("🎨 Phi-Plugin 风格渲染器初始化")

    async def initialize(self):
        """初始化（异步方法，供外部调用）"""
        # 预加载常用资源
        await self._preload_resources()
    
    async def _preload_resources(self):
        """预加载常用资源到缓存"""
        logger.info("🚀 预加载渲染资源...")
        
        # 预加载评级图片
        ratings = ['φ', 'V', 'S', 'A', 'B', 'C', 'F', 'FC']
        for rating in ratings:
            self._get_rating_image(rating)
        
        # 预加载常用字体
        for size in [10, 12, 13, 14, 16, 18, 28]:
            self._get_font(size, bold=False)
            self._get_font(size, bold=True)
        
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
        logger.info("🧹 PhiStyleRenderer 资源已清理")

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

            # 在线程池中加载图片，传递索引参数
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

        # 存储到缓存（使用带索引的键，避免相同歌曲覆盖）
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
            # 尝试多种方式查找曲绘，使用带索引的键确保不同实例使用不同曲绘
            song_key = f"{song_name}_{index}"
            illust = self._get_illustration(song_key)
            if illust:
                # 确保曲绘是RGBA模式
                if illust.mode != 'RGBA':
                    illust = illust.convert('RGBA')
                # 预先调整大小（避免在渲染时调整）
                target_height = self.CARD_HEIGHT
                aspect_ratio = illust.width / illust.height
                target_width = int(target_height * aspect_ratio)
                return illust.resize((target_width, target_height), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.debug(f"预加载曲绘失败 {song_name}: {e}")
        return None

    def _get_background_image(self, height: int) -> Image.Image:
        """获取背景图片（带缓存）"""
        logger.info("=== _get_background_image 被调用 ===")
        # 如果缓存的背景图高度不够，重新生成
        if self._bg_cache is None or self._bg_cache.height < height:
            bg_path = self.plugin_dir / "resources" / "img" / "background" / "c774204e373ad3ab3a4137c7e5a930da.jpg"
            logger.info(f"背景图片路径: {bg_path}")
            logger.info(f"背景图片是否存在: {bg_path.exists()}")
            if bg_path.exists():
                try:
                    # 使用更小的半径进行模糊，提升性能
                    bg_img = Image.open(bg_path).convert("RGBA")
                    logger.info(f"✅ 背景图片加载成功，原始大小: {bg_img.size}")
                    # 先缩小再模糊，提升性能
                    scale_factor = 0.5
                    small_size = (int(self.WIDTH * scale_factor), int(height * scale_factor))
                    bg_img = bg_img.resize(small_size, Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=3))
                    # 恢复到目标大小
                    bg_img = bg_img.resize((self.WIDTH, height), Image.Resampling.LANCZOS)
                    # 降低亮度
                    enhancer = ImageEnhance.Brightness(bg_img)
                    bg_img = enhancer.enhance(0.4)
                    self._bg_cache = bg_img
                    logger.info(f"✅ 背景图片处理完成")
                    logger.info(f"处理后背景图片信息: 大小={bg_img.size}, 模式={bg_img.mode}")
                    return bg_img.copy()
                except Exception as e:
                    logger.warning(f"加载背景图片失败: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())
            # 使用默认深色背景
            logger.warning("⚠️ 使用默认深色背景")
            default_bg = Image.new('RGBA', (self.WIDTH, height), (26, 26, 46, 255))
            logger.info(f"默认背景图片信息: 大小={default_bg.size}, 模式={default_bg.mode}")
            return default_bg
        else:
            # 使用缓存的背景图，裁剪到目标高度
            logger.info("使用缓存的背景图片")
            cached_bg = self._bg_cache.crop((0, 0, self.WIDTH, height))
            logger.info(f"缓存背景图片信息: 大小={cached_bg.size}, 模式={cached_bg.mode}")
            return cached_bg

    def _get_avatar(self, avatar_name: Optional[str] = None) -> Optional[Image.Image]:
        """获取头像

        Args:
            avatar_name: 头像文件名（不含扩展名），如果为 None 则随机选择一个

        Returns:
            头像图片或 None
        """
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

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """获取字体 - 优先使用插件自带字体，确保跨平台一致性"""
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

    def _draw_text_safe(self, draw: ImageDraw.Draw, xy, text: str, fill, font: ImageFont.FreeTypeFont, anchor=None):
        """安全绘制文本，处理特殊字符和编码问题"""
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

    def __init__(self,
                 plugin_dir: Path,
                 cache_dir: Path,
                 illustration_path: Path,
                 image_quality: int = 95,
                 avatar_path: Optional[Path] = None):
        """初始化渲染器"""
        self.plugin_dir = plugin_dir
        self.cache_dir = cache_dir
        self.illustration_path = illustration_path
        self.image_quality = image_quality
        self.avatar_path = avatar_path or (plugin_dir / "AVATAR")

        # 字体缓存
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}

        # 曲绘缓存
        self._illustration_cache: Dict[str, Image.Image] = {}

        # 头像缓存
        self._avatar_cache: Dict[str, Image.Image] = {}

        # 评级图片缓存
        self._rating_cache: Dict[str, Image.Image] = {}

        # 评级图片路径
        self.rating_path = plugin_dir / "resources" / "img" / "rating"

        # 背景图片缓存
        self._bg_cache: Optional[Image.Image] = None

        # 线程池（用于并行加载图片）
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 曲绘预加载缓存（存储处理后的曲绘）
        self._processed_illust_cache: Dict[str, Image.Image] = {}

        # 曲绘使用记录，用于冲突检测
        self._illustration_usage: Dict[str, List[str]] = {}

        # 所有可用曲绘的映射，键为歌曲名称，值为曲绘文件路径列表
        self._all_illustrations: Dict[str, List[Path]] = {}
        # 初始化可用曲绘映射
        self._initialize_illustrations_map()

        logger.info("🎨 Phi-Plugin 风格渲染器初始化")

    def _initialize_illustrations_map(self):
        """初始化可用曲绘映射"""
        try:
            # 获取所有图片文件（支持 .png, .jpg, .jpeg, .gif 等）
            all_image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
                all_image_files.extend(self.illustration_path.glob(ext))
                # Ubuntu 大小写敏感，同时匹配大写扩展名
                all_image_files.extend(self.illustration_path.glob(ext.upper()))

            # 构建曲绘映射
            for file in all_image_files:
                file_stem_lower = file.stem.lower()
                # 提取歌曲名称（去除可能的后缀，如 " (1)", "_1" 等）
                import re
                song_name = re.sub(r'\s*\(\d+\)$|\s*_\d+$', '', file_stem_lower)
                if song_name not in self._all_illustrations:
                    self._all_illustrations[song_name] = []
                self._all_illustrations[song_name].append(file)

            logger.info(f"✅ 初始化曲绘映射完成，找到 {len(self._all_illustrations)} 首歌曲的曲绘")
        except Exception as e:
            logger.warning(f"初始化曲绘映射失败: {e}")

    def _get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取曲绘（支持大小写不敏感和多种扩展名，支持冲突检测）"""
        # 提取原始歌曲名称（去除索引部分）
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
        """传统的曲绘查找方式（作为 fallback）"""
        song_key_lower = song_key.lower()
        matched_file = None

        # 获取所有图片文件（支持 .png, .jpg, .jpeg, .gif 等）
        all_image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
            all_image_files.extend(self.illustration_path.glob(ext))
            # Ubuntu 大小写敏感，同时匹配大写扩展名
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

        # 如果仍然没有匹配，尝试模糊匹配（去除空格和特殊字符）
        if not matched_file:
            import re
            # 去除空格和特殊字符，只保留字母、数字和中文
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
            # 在 Ubuntu 下添加更详细的调试信息
            logger.warning(f"未找到曲绘: {song_key}")
            logger.debug(f"曲绘目录: {self.illustration_path}")
            logger.debug(f"目录存在: {self.illustration_path.exists()}")
            if self.illustration_path.exists():
                files = list(self.illustration_path.glob("*.png"))[:5]
                logger.debug(f"样本文件: {[f.name for f in files]}")

        return None

    def _get_rating_image(self, rating: str) -> Optional[Image.Image]:
        """获取评级图片（φ, V, S, A, B, C, F, FC等）"""
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
        """根据分数和ACC计算评级

        评级规则：
        - φ (Phi): 分数 = 1000000 (AP)
        - V (Full Combo): FC = True 且分数 < 1000000
        - S: Acc >= 99.00%
        - A: Acc >= 95.00%
        - B: Acc >= 90.00%
        - C: Acc >= 80.00%
        - F: Acc < 80.00%
        """
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

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """十六进制颜色转 RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
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
    
    async def render_b30(self, data: Dict[str, Any], output_path: Path) -> bool:
        """
        渲染 Best30 成绩图（Phi-Plugin 风格）- 优化版本
        """
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
            main_content_height = num_rows * (self.CARD_HEIGHT + self.CARD_MARGIN)
            
            overflow_height = 0
            if overflow_records:
                overflow_height = (self.CARD_HEIGHT + self.CARD_MARGIN) + self.OVERFLOW_HEADER_HEIGHT

            total_height = self.HEADER_HEIGHT + main_content_height + overflow_height + 80

            logger.info(f"计算总高度: {total_height}")

            await self._preload_illustrations(all_records)

            logger.info("开始加载背景图片...")
            # 创建一个新的RGBA图片作为最终输出
            img = Image.new('RGBA', (self.WIDTH, total_height), (26, 26, 46, 255))
            # 加载并绘制背景图片
            bg_img = self._get_background_image(total_height)
            logger.info(f"背景图片加载完成，大小: {bg_img.size}, 模式: {bg_img.mode}")
            # 保存背景图片用于调试
            debug_bg_path = output_path.parent / f"debug_bg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            bg_img.save(debug_bg_path, 'PNG')
            logger.info(f"✅ 调试背景图片已保存: {debug_bg_path}")
            # 确保背景图片是RGBA模式
            if bg_img.mode != 'RGBA':
                bg_img = bg_img.convert('RGBA')
                logger.info("背景图片已转换为RGBA模式")
            # 将背景图片粘贴到输出图片
            img.paste(bg_img, (0, 0))
            logger.info("背景图片已粘贴到输出图片")
            draw = ImageDraw.Draw(img)

            self._draw_header(img, draw, gameuser)

            start_y = self.HEADER_HEIGHT + 20
            col_x_positions = [20, 390, 760]

            for i, record in enumerate(main_records):
                col = i % num_cols
                row = i // num_cols
                x = col_x_positions[col]
                y = start_y + row * (self.CARD_HEIGHT + self.CARD_MARGIN)
                self._draw_song_card_fast(img, draw, i + 1, record, x, y)
            
            overflow_start_y = start_y + main_content_height + 10
            if overflow_records:
                self._draw_overflow_section(img, draw, overflow_records, overflow_start_y, col_x_positions)
            
            footer_y = overflow_start_y + overflow_height + 20 if overflow_records else start_y + main_content_height + 20
            self._draw_footer(img, draw, footer_y)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # 保存前检查图片信息
            logger.info(f"保存前图片信息: 大小={img.size}, 模式={img.mode}, 透明度={img.mode == 'RGBA'}")
            # 保存图片
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            # 保存后检查文件大小
            import os
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ 渲染成功: {output_path}, 文件大小: {file_size} 字节")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _draw_header(self, img: Image.Image, draw: ImageDraw.Draw, gameuser: Dict):
        """绘制头部（玩家信息）- 优化版本，精确匹配示例图"""
        logger.info("=== _draw_header 被调用 ===")
        logger.info(f"gameuser 数据: {gameuser}")
        # 移除黑色背景块，使用完全透明背景
        header_rect = (40, 20, self.WIDTH - 40, self.HEADER_HEIGHT - 20)
        
        # 不绘制任何背景，保持完全透明
        # 移除所有背景绘制代码，让头部区域完全透明

        # 头像区域（圆形）
        avatar_size = 100
        avatar_x = 60
        avatar_y = (self.HEADER_HEIGHT - avatar_size) // 2

        # 尝试加载头像 - 优先使用 API 返回的 avatar 字段
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

        # 课题模式段位 - 优化加载逻辑
        challenge_rank = gameuser.get('challengeModeRank', 0)
        logger.info(f"challenge_rank: {challenge_rank}")
        rank_badge_width = 0
        rank_img_resized = None
        
        # 处理课题模式段位
        if challenge_rank:
            # 课题模式段位处理
            # 数字表示三首谱面难度总和，颜色代表综合实力
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
            
            logger.info(f"rank_name: {rank_name}")

            # 加载段位颜色图片
            rank_img_path = self.plugin_dir / "resources" / "img" / "other" / f"{rank_name}.png"
            logger.info(f"段位图片路径: {rank_img_path}")
            logger.info(f"段位图片是否存在: {rank_img_path.exists()}")
            if rank_img_path.exists():
                try:
                    rank_img = Image.open(rank_img_path).convert("RGBA")
                    logger.info(f"✅ 段位图片加载成功")
                    # 调整大小 - 段位徽章更大一些
                    badge_height = 36
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 15  # 徽章宽度 + 间距
                    logger.info(f"段位图片调整大小后: {rank_img_resized.size}")
                except Exception as e:
                    logger.warning(f"加载段位图片失败: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())
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
                        logger.info(f"使用默认段位图片: 白色.png")
                except Exception as e:
                    logger.warning(f"加载默认段位图片失败: {e}")
        else:
            logger.info("没有段位信息，跳过段位显示")
            # 尝试使用默认段位图片
            try:
                default_rank_path = self.plugin_dir / "resources" / "img" / "other" / "白色.png"
                if default_rank_path.exists():
                    rank_img = Image.open(default_rank_path).convert("RGBA")
                    badge_height = 36
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 15
                    logger.info(f"使用默认段位图片: 白色.png")
            except Exception as e:
                logger.warning(f"加载默认段位图片失败: {e}")

        # 在昵称左侧显示段位徽章
        if rank_img_resized:
            badge_x = info_x
            badge_y = avatar_y + 10  # 与昵称垂直居中对齐
            logger.info(f"准备粘贴段位图片，位置: ({badge_x}, {badge_y})")
            img.paste(rank_img_resized, (badge_x, badge_y), rank_img_resized)
            # 在段位图片上绘制段位数字
            font_rank = self._get_font(22, bold=True)  # 增大字体大小，使其更醒目
            # 显示段位等级的前两位数字
            rank_text = str(challenge_rank)[:2] if challenge_rank else "1"
            # 计算文本位置（段位框内居中）
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
            logger.info(f"✅ 段位图片已粘贴，并添加了段位数字: {rank_text}")

        # 统一字体大小设置
        # 基准字号：16px（清晰可见，适合不同设备）
        base_font_size = 16
        
        # 昵称 - 智能获取，支持特殊字符（统一字体大小）
        font_name = self._get_font(base_font_size + 4, bold=True)  # 昵称稍大，突出显示
        nickname = gameuser.get('nickname', '')
        if not nickname or nickname == 'Unknown':
            nickname = gameuser.get('name', '') or gameuser.get('alias', '') or 'Phigros Player'
        if len(nickname) > 20:
            nickname = nickname[:18] + '...'  # 允许更长的昵称
        
        # 昵称位置（如果有段位徽章，留出空间）
        nickname_x = info_x + rank_badge_width
        # 调整昵称位置，往下移一点，与段位保持齐平
        nickname_y = avatar_y + 15  # 向下移动，与段位保持齐平
        # 使用明亮的白色，提高对比度
        self._draw_text_safe(draw, (nickname_x, nickname_y), nickname, fill=(255, 255, 255, 255), font=font_name)

        # ID - 智能获取，避免显示 N/A（统一字体大小）
        font_id = self._get_font(base_font_size)  # 基准字号，清晰可见
        player_id = gameuser.get('PlayerId', '')
        if not player_id or player_id == 'N/A':
            player_id = gameuser.get('playerId', '') or gameuser.get('id', '') or gameuser.get('uid', '')
        if not player_id or player_id == 'N/A':
            player_id = "TapTap User"
        if len(player_id) > 30:
            player_id = player_id[:27] + '...'  # 允许更长的ID
        # 使用亮灰色，提高对比度
        self._draw_text_safe(draw, (info_x, avatar_y + 45), f"ID: {player_id}", fill=(200, 200, 200, 255), font=font_id)
        
        # RKS 显示（透明设计，横向模式，位于ID下方）
        rks_width = 200  # 横向布局需要更大的宽度
        rks_height = 40   # 横向布局高度更大，适应更大的字体
        # 调整位置，将RKS显示在ID元素的下方
        rks_x = info_x
        rks_y = avatar_y + 70  # 位于ID显示元素的下方
        
        # 不绘制任何背景，保持完全透明
        # 移除所有背景和边框绘制代码
        
        # RKS 文字（横向模式，统一字体大小）
        font_rks_label = self._get_font(base_font_size, bold=True)  # 基准字号，清晰可见
        font_rks_value = self._get_font(base_font_size + 6, bold=True)  # RKS数值稍大，突出显示
        rks = gameuser.get('rks', 0)
        
        # 计算文本位置（横向布局：RKS标签在左，数值在右）
        label_width = draw.textlength("RKS", font=font_rks_label)
        value_width = draw.textlength(f"{rks:.4f}", font=font_rks_value)
        total_width = label_width + value_width + 15  # 15px 间距，适应更大的字体
        
        # 居中对齐
        start_x = rks_x
        
        # 使用白色文字，提高在透明背景上的可读性
        draw.text((start_x, rks_y + rks_height // 2), "RKS", 
                 fill=(255, 255, 255, 255), font=font_rks_label, anchor='lm')
        draw.text((start_x + label_width + 15, rks_y + rks_height // 2), f"{rks:.4f}", 
                 fill=(255, 255, 255, 255), font=font_rks_value, anchor='lm')
        
        # 添加logo到头部右侧
        logo_path = self.plugin_dir / "resources" / "img" / "logo" / "phi.png"
        if logo_path.exists():
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                # 调整logo大小（增大尺寸）
                logo_size = 100  # 增大到100x100像素
                logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                # 计算位置（头部右侧）
                logo_x = self.WIDTH - logo_size - 140  # 减少右侧边距，让logo更靠近边缘
                logo_y = (self.HEADER_HEIGHT - logo_size) // 2
                # 粘贴logo
                img.paste(logo_img, (logo_x, logo_y), logo_img)
                logger.info("✅ Logo 已添加到头部右侧")
                
                # 在logo下方添加文字：xtower.site提供支持
                logo_text = "xtower.site提供支持"
                font_logo_text = self._get_font(16, bold=False)  # 增大字号到16px
                # 计算文字位置（logo下方居中）
                text_x = logo_x + logo_size // 2
                text_y = logo_y + logo_size + 12  # 增大间距到12px，适应更大的字体
                # 使用与底部文字相同的发光效果
                self._draw_text_with_glow(img, text_x, text_y, logo_text, '#aaaaaa', font_logo_text,
                                         glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
                logger.info("✅ Logo下方文字已添加")
            except Exception as e:
                logger.warning(f"加载logo失败: {e}")
    
    def _draw_song_card(self, img: Image.Image, draw: ImageDraw.Draw, rank: int, 
                       record: Dict, x: int, y: int):
        """绘制歌曲卡片（phi-plugin 风格）"""
        card_width = self.CARD_WIDTH
        card_height = self.CARD_HEIGHT
        
        # 曲绘区域（左侧，占 50%）
        illust_width = card_width // 2
        illust_height = card_height
        
        # 尝试加载曲绘
        song = record.get('song', '')
        illust = self._get_illustration(song)
        
        if illust:
            # 缩放曲绘
            illust_resized = illust.resize((illust_width, illust_height), Image.Resampling.LANCZOS)
            # 粘贴曲绘
            img.paste(illust_resized, (x, y))
        else:
            # 回退：绘制渐变占位符，避免黑色遮挡
            # 从深到浅的渐变（不使用透明度，避免透底）
            for i in range(illust_height):
                brightness = int(60 + (20 * i / illust_height))
                draw.line([(x, y + i), (x + illust_width, y + i)], 
                         fill=(brightness, brightness, brightness + 20))
            # 添加难度对应的边框
            diff = record.get('difficulty', 'IN')
            diff_color = self.COLORS.get(diff, self.COLORS['IN'])
            draw.rectangle([x, y, x + 3, y + illust_height], fill=self._hex_to_rgb(diff_color))
            draw.rectangle([x + illust_width - 3, y, x + illust_width, y + illust_height], fill=self._hex_to_rgb(diff_color))
        
        # 排名徽章（左上角，白色小条）
        rank_width = 50
        rank_height = 18
        rank_bg = '#ffffff'
        if rank == 1:
            rank_bg = '#ffd700'  # 金牌
        elif rank == 2:
            rank_bg = '#c0c0c0'  # 银牌
        elif rank == 3:
            rank_bg = '#cd7f32'  # 铜牌
            
        draw.rectangle([x - 5, y - 5, x + rank_width, y + rank_height], 
                      fill=self._hex_to_rgb(rank_bg))
        
        font_rank = self._get_font(11, bold=True)
        rank_text_color = 'black' if rank <= 3 else 'black'
        draw.text((x + rank_width // 2 - 2, y + rank_height // 2 - 2), 
                 str(rank), fill=rank_text_color, font=font_rank, anchor='mm')
        
        # 难度标签（曲绘左下角）
        diff = record.get('difficulty', 'IN')
        diff_color = self.COLORS.get(diff, self.COLORS['IN'])
        diff_width = 45
        diff_height = 22
        diff_x = x + 5
        diff_y = y + illust_height - diff_height - 5
        
        draw.rectangle([diff_x, diff_y, diff_x + diff_width, diff_y + diff_height],
                      fill=self._hex_to_rgb(diff_color))
        
        font_diff = self._get_font(12, bold=True)
        draw.text((diff_x + diff_width // 2, diff_y + diff_height // 2), 
                 diff, fill='white', font=font_diff, anchor='mm')
        
        # 信息卡片（右侧，半透明背景）
        info_x = x + illust_width - 15  # 稍微重叠
        info_width = card_width - illust_width + 15
        info_height = card_height - 10
        info_y = y + 5
        
        # 根据难度选择边框颜色
        border_color = self._hex_to_rgb(diff_color)
        # 使用深色背景，提高可读性（RGB模式）
        bg_color = (40, 40, 55)  # 深蓝灰色背景

        # 绘制信息卡背景
        self._draw_rounded_rect(draw,
                               (info_x, info_y, info_x + info_width, info_y + info_height),
                               5, (*bg_color, 255))
        
        # 绘制左边框
        draw.rectangle([info_x, info_y, info_x + 3, info_y + info_height], fill=border_color)
        
        # 曲名（带发光效果）
        font_song = self._get_font(13, bold=True)
        song_name = record.get('song', 'Unknown')
        if len(song_name) > 12:
            song_name = song_name[:10] + '...'
        self._draw_text_with_glow(img, info_x + 10, info_y + 8, song_name, 'white', font_song, glow_color=(100, 200, 255))

        # 分数（带发光效果）
        font_score = self._get_font(18, bold=True)
        score = record.get('score', 0)
        self._draw_text_with_glow(img, info_x + 10, info_y + 32, f"{score:,}", '#ffd700', font_score, glow_color=(100, 200, 255))

        # ACC 和 RKS（带发光效果）
        font_acc = self._get_font(10)
        acc = record.get('acc', 0)
        rks = record.get('rks', 0)
        self._draw_text_with_glow(img, info_x + 10, info_y + 58, f"Acc: {acc:.2f}%", '#aaaaaa', font_acc, glow_color=(100, 200, 255))
        self._draw_text_with_glow(img, info_x + 10, info_y + 73, f"RKS: {rks:.2f}", '#aaaaaa', font_acc, glow_color=(100, 200, 255))

        # 评级图片（右侧）
        rating = self._calculate_rating(score, acc, record.get('fc', False))
        rating_img = self._get_rating_image(rating)
        if rating_img:
            # 调整评级图片大小
            rating_height = 40
            rating_width = int(rating_height * rating_img.width / rating_img.height)
            rating_resized = rating_img.resize((rating_width, rating_height), Image.Resampling.LANCZOS)
            # 粘贴评级图片（信息卡右侧）
            rating_x = info_x + info_width - rating_width - 10
            rating_y = info_y + (info_height - rating_height) // 2
            # 直接粘贴评级图片
            img.paste(rating_resized, (rating_x, rating_y), rating_resized)

        # FC/AP 标识（曲绘右上角）
        if record.get('fc'):
            score_val = record.get('score', 0)
            fc_text = 'AP' if score_val == 1000000 else 'FC'
            fc_color = '#ffd700' if score_val == 1000000 else '#00b0f0'
            fc_width = 28
            fc_height = 18
            fc_x = x + illust_width - fc_width - 5
            fc_y = y + 5

            draw.rectangle([fc_x, fc_y, fc_x + fc_width, fc_y + fc_height],
                          fill=self._hex_to_rgb(fc_color))
            font_fc = self._get_font(9, bold=True)
            draw.text((fc_x + fc_width // 2, fc_y + fc_height // 2),
                     fc_text, fill='black' if score_val == 1000000 else 'white',
                     font=font_fc, anchor='mm')

    def _draw_song_card_fast(self, img: Image.Image, draw: ImageDraw.Draw, rank: Optional[int],
                              record: Dict, x: int, y: int):
        """快速绘制歌曲卡片（使用预加载的曲绘，支持不显示排名）"""
        logger.info(f"=== _draw_song_card_fast 被调用，歌曲: {record.get('song', 'Unknown')}")
        card_width = self.CARD_WIDTH
        card_height = self.CARD_HEIGHT
        illust_width = card_width // 2
        illust_height = card_height

        # 使用预加载的曲绘，使用带索引的缓存键
        song = record.get('song', '')
        # 从record中获取索引信息，如果没有则使用默认值
        index = record.get('__index__', 0)
        cache_key = f"{song.lower()}_{index}"
        illust = self._processed_illust_cache.get(cache_key)

        if illust:
            # 预加载的曲绘已经调整过大小
            # 确保曲绘是RGBA模式，这样可以正确处理透明度
            if illust.mode != 'RGBA':
                illust = illust.convert('RGBA')
            # 创建一个半透明的曲绘副本
            illust_with_alpha = Image.new('RGBA', illust.size, (255, 255, 255, 200))
            illust_with_alpha.paste(illust, (0, 0), illust)
            img.paste(illust_with_alpha, (x, y), illust_with_alpha)
            logger.info(f"使用预加载的曲绘: {song}")
        else:
            # 回退：绘制渐变占位符，避免黑色遮挡
            # 从深到浅的渐变（使用半透明，避免完全遮挡背景）
            for i in range(illust_height):
                brightness = int(60 + (20 * i / illust_height))
                draw.line([(x, y + i), (x + illust_width, y + i)], 
                         fill=(brightness, brightness, brightness + 20, 150))
            # 添加难度对应的边框
            diff = record.get('difficulty', 'IN')
            diff_color = self.COLORS.get(diff, self.COLORS['IN'])
            draw.rectangle([x, y, x + 3, y + illust_height], fill=self._hex_to_rgb(diff_color))
            draw.rectangle([x + illust_width - 3, y, x + illust_width, y + illust_height], fill=self._hex_to_rgb(diff_color))
            logger.info(f"使用渐变占位符: {song}")

        # 排名徽章（仅在有排名时绘制）
        if rank is not None:
            rank_colors = {1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32'}
            rank_bg = rank_colors.get(rank, '#ffffff')
            draw.rectangle([x - 5, y - 5, x + 45, y + 13], fill=self._hex_to_rgb(rank_bg))
            font_rank = self._get_font(11, bold=True)
            draw.text((x + 20, y + 4), str(rank), fill='black', font=font_rank, anchor='mm')

        # 难度标签
        diff = record.get('difficulty', 'IN')
        diff_color = self.COLORS.get(diff, self.COLORS['IN'])
        draw.rectangle([x + 5, y + illust_height - 27, x + 50, y + illust_height - 5],
                      fill=self._hex_to_rgb(diff_color))
        font_diff = self._get_font(12, bold=True)
        draw.text((x + 27, y + illust_height - 16), diff, fill='white', font=font_diff, anchor='mm')

        # 信息卡片
        info_x = x + illust_width - 15
        info_width = card_width - illust_width + 15
        info_height = card_height - 10
        info_y = y + 5

        # 绘制背景和边框（增强视觉效果）
        bg_color = (40, 40, 55, 60)  # 进一步降低透明度，让背景更明显
        # 绘制信息卡背景
        self._draw_rounded_rect(draw,
                               (info_x, info_y, info_x + info_width, info_y + info_height),
                               5, bg_color)
        
        # 绘制左侧边框（增强难度标识）
        draw.rectangle([info_x, info_y, info_x + 4, info_y + info_height],
                      fill=self._hex_to_rgb(diff_color))
        # 添加边框高亮
        draw.rectangle([info_x + 1, info_y + 1, info_x + 2, info_y + info_height - 1],
                      fill=(255, 255, 255, 100))

        # 文字信息（优化字体样式）
        font_song = self._get_font(12, bold=True)  # 减小字体大小
        song_name = record.get('song', 'Unknown')
        if len(song_name) > 14:
            song_name = song_name[:12] + '...'  # 允许更长的歌曲名
        # 增强发光效果，使用更深的蓝色
        self._draw_text_with_glow(img, info_x + 10, info_y + 6, song_name, 'white', font_song,
                                  glow_color=(50, 150, 255), glow_radius=2)  # 减小发光半径

        font_score = self._get_font(16, bold=True)  # 减小字体大小
        score = record.get('score', 0)
        # 分数发光效果增强
        self._draw_text_with_glow(img, info_x + 10, info_y + 28, f"{score:,}", '#ffd700', font_score,
                                  glow_color=(255, 215, 0), glow_radius=2)  # 减小发光半径

        # 增强 Acc 和 RKS 文字
        font_acc = self._get_font(9, bold=False)  # 减小字体大小
        acc = record.get('acc', 0)
        rks = record.get('rks', 0)
        # Acc 颜色根据值变化
        acc_color = '#00ff00' if acc >= 95 else '#ffff00' if acc >= 90 else '#ff8c00' if acc >= 80 else '#ff0000'
        draw.text((info_x + 10, info_y + 50), f"Acc: {acc:.2f}%", fill=acc_color, font=font_acc)
        # RKS 使用浅蓝色
        draw.text((info_x + 10, info_y + 63), f"RKS: {rks:.2f}", fill='#66ccff', font=font_acc)

        # 评级图片（优化视觉效果）
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

        # FC/AP 标识（优化视觉效果）
        if record.get('fc'):
            score_val = record.get('score', 0)
            fc_text = 'AP' if score_val == 1000000 else 'FC'
            fc_color = '#ffd700' if score_val == 1000000 else '#00b0f0'
            # 移除黑色阴影，直接绘制标识
            draw.rectangle([x + illust_width - 33, y + 5, x + illust_width - 5, y + 23],
                          fill=self._hex_to_rgb(fc_color))
            font_fc = self._get_font(9, bold=True)
            draw.text((x + illust_width - 19, y + 14), fc_text,
                     fill='black' if score_val == 1000000 else 'white',
                     font=font_fc, anchor='mm')

    def _draw_text_with_glow(self, img: Image.Image, x: int, y: int, text: str, 
                              text_color: str, font: ImageFont.FreeTypeFont, 
                              glow_color: Tuple[int, int, int] = (255, 255, 255),
                              glow_radius: int = 4, anchor: str = None):
        """绘制带发光效果的文字
        
        Args:
            img: 目标图片
            x, y: 文字位置
            text: 文字内容
            text_color: 文字颜色（十六进制或颜色名）
            font: 字体
            glow_color: 发光颜色 (R, G, B)
            glow_radius: 发光半径
            anchor: 文字锚点（如 'mm' 表示中心对齐）
        """
        draw = ImageDraw.Draw(img)
        
        # 计算文本边界框，只在文本周围创建发光效果
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

    def _draw_overflow_section(self, img: Image.Image, draw: ImageDraw.Draw, 
                               records: List[Dict], start_y: int, col_x_positions: List[int]):
        """绘制 Overflow 区域（展示额外记录）- 优化版本"""
        # 绘制 Overflow 标题栏
        title_height = self.OVERFLOW_HEADER_HEIGHT
        title_y = start_y
        
        center_x = self.WIDTH // 2
        
        # 装饰性线条（简洁风格）
        line_width = 280
        line_gap = 60
        
        # 左线条（单层白色）
        draw.rectangle([center_x - line_width - line_gap - 60, title_y + title_height // 2 - 2,
                       center_x - line_gap - 60, title_y + title_height // 2 + 2],
                      fill=(255, 255, 255, 200))
        
        # 右线条（单层白色）
        draw.rectangle([center_x + line_gap + 60, title_y + title_height // 2 - 2,
                       center_x + line_width + line_gap + 60, title_y + title_height // 2 + 2],
                      fill=(255, 255, 255, 200))
        
        # Overflow 文字（优化字体样式）
        font_title = self._get_font(24, bold=True)  # 减小字体大小
        self._draw_text_with_glow(img, center_x, title_y + title_height // 2, 
                                  "OVER FLOW", '#ffffff', font_title,
                                  glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
        
        # 绘制 Overflow 记录卡片（3列，严格显示3首）
        card_start_y = title_y + title_height + 10  # 减小间距
        overflow_records = records[:3]  # 严格限制只显示3首歌曲
        
        # 使用固定列位置
        for i, record in enumerate(overflow_records):
            x = col_x_positions[i] if i < len(col_x_positions) else 20 + i * (self.CARD_WIDTH + self.CARD_MARGIN)
            y = card_start_y
            # 移除阴影效果，避免曲绘底部出现黑色方块
            # Overflow 卡片不显示排名
            self._draw_song_card_fast(img, draw, None, record, x, y)

    def _draw_footer(self, img: Image.Image, draw: ImageDraw.Draw, y: int):
        """绘制底部（带发光效果）"""
        text = "phigros插件——飞翔的死猪提供技术支持"
        font = self._get_font(16, bold=False)
        self._draw_text_with_glow(img, self.WIDTH // 2, y, text, '#aaaaaa', font,
                                  glow_color=(100, 200, 255), glow_radius=6, anchor='mm')
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        logger.warning("单曲成绩渲染暂未实现")
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
            width = 1200
            height = 600
            padding = 80
            chart_width = width - 2 * padding
            chart_height = height - 2 * padding
            
            # 加载背景图片
            bg_path = self.plugin_dir / "resources" / "img" / "history" / "80aa4928e0cef4729d5c70336b5d892d.jpg"
            if bg_path.exists():
                try:
                    bg_img = Image.open(bg_path).convert("RGBA")
                    # 调整背景图片大小
                    bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
                except Exception as e:
                    logger.warning(f"加载背景图片失败: {e}")
                    # 使用默认背景
                    bg_img = Image.new('RGBA', (width, height), (26, 26, 46, 255))
            else:
                # 使用默认背景
                bg_img = Image.new('RGBA', (width, height), (26, 26, 46, 255))
            
            # 创建画布
            img = bg_img
            draw = ImageDraw.Draw(img)
            
            # 绘制标题
            font_title = self._get_font(28, bold=True)
            title = "RKS 历史趋势"
            title_width = draw.textlength(title, font=font_title)
            draw.text((width // 2 - title_width // 2, padding // 2), title, fill='white', font=font_title)
            
            # 绘制统计信息
            font_stats = self._get_font(14)
            stats_text = f"当前 RKS: {current_rks:.4f} | 最高 RKS: {peak_rks:.4f} | 总记录数: {total}"
            stats_width = draw.textlength(stats_text, font=font_stats)
            draw.text((width // 2 - stats_width // 2, padding - 10), stats_text, fill='#aaaaaa', font=font_stats)
            
            # 计算坐标轴范围
            min_rks = min(rks_values) - 0.5
            max_rks = max(rks_values) + 0.5
            rks_range = max_rks - min_rks
            
            # 绘制坐标轴
            draw.line([(padding, padding), (padding, height - padding)], fill='white', width=2)
            draw.line([(padding, height - padding), (width - padding, height - padding)], fill='white', width=2)
            
            # 绘制刻度和标签
            font_axis = self._get_font(12)
            
            # Y 轴刻度
            y_ticks = 5
            for i in range(y_ticks + 1):
                y_value = min_rks + (rks_range * i / y_ticks)
                y = height - padding - (chart_height * i / y_ticks)
                draw.line([(padding - 5, y), (padding, y)], fill='white', width=2)
                draw.text((padding - 60, y - 6), f"{y_value:.1f}", fill='white', font=font_axis)
            
            # X 轴刻度（只显示部分日期）
            x_ticks = min(10, len(dates))
            step = max(1, len(dates) // x_ticks)
            for i in range(0, len(dates), step):
                x = padding + (chart_width * i / (len(dates) - 1))
                draw.line([(x, height - padding), (x, height - padding + 5)], fill='white', width=2)
                date_text = dates[i]
                draw.text((x - 30, height - padding + 10), date_text, fill='white', font=font_axis)
            
            # 绘制数据点和曲线
            points = []
            for i, (date, rks) in enumerate(zip(dates, rks_values)):
                x = padding + (chart_width * i / (len(dates) - 1))
                y = height - padding - (chart_height * (rks - min_rks) / rks_range)
                points.append((x, y))
                # 绘制数据点
                draw.ellipse([(x - 4, y - 4), (x + 4, y + 4)], fill='#00b0f0', outline='white', width=2)
            
            # 绘制平滑曲线
            if len(points) > 1:
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    draw.line([(x1, y1), (x2, y2)], fill='#00b0f0', width=3)
            
            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ RKS 历史趋势图渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染 RKS 历史趋势图失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
