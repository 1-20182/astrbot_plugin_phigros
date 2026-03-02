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
from astrbot.api import logger

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


class PhiStyleRenderer:
    """
    🎨 Phi-Plugin 风格渲染器
    
    精确还原 phi-plugin 的 b19 设计
    """
    
    # 颜色定义（来自 phi-plugin 的 CSS）
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
    
    # 布局常量
    WIDTH = 1200
    HEADER_HEIGHT = 180
    CARD_WIDTH = 360
    CARD_HEIGHT = 100
    CARD_MARGIN = 15
    
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
        async def load_single(record: Dict) -> Tuple[str, Optional[Image.Image]]:
            song_name = record.get('song', '')
            if not song_name:
                return '', None

            # 检查缓存
            cache_key = song_name.lower()
            if cache_key in self._processed_illust_cache:
                return cache_key, self._processed_illust_cache[cache_key]

            # 在线程池中加载图片
            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(
                self._executor,
                self._load_and_process_illustration,
                song_name
            )
            return cache_key, img

        # 并行加载所有曲绘
        tasks = [load_single(record) for record in records]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 存储到缓存
        for result in results:
            if isinstance(result, tuple) and result[1] is not None:
                self._processed_illust_cache[result[0]] = result[1]

        logger.info(f"✅ 预加载完成: {len(self._processed_illust_cache)} 张曲绘")

    def _load_and_process_illustration(self, song_name: str) -> Optional[Image.Image]:
        """在线程中加载和处理曲绘"""
        try:
            # 尝试多种方式查找曲绘
            illust = self._get_illustration(song_name)
            if illust:
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
        # 如果缓存的背景图高度不够，重新生成
        if self._bg_cache is None or self._bg_cache.height < height:
            bg_path = self.plugin_dir / "resources" / "img" / "background" / "c774204e373ad3ab3a4137c7e5a930da.jpg"
            if bg_path.exists():
                try:
                    # 使用更小的半径进行模糊，提升性能
                    bg_img = Image.open(bg_path).convert("RGB")
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
                    return bg_img.copy()
                except Exception as e:
                    logger.warning(f"加载背景图片失败: {e}")
            # 使用默认深色背景
            return Image.new('RGB', (self.WIDTH, height), (26, 26, 46))
        else:
            # 使用缓存的背景图，裁剪到目标高度
            return self._bg_cache.crop((0, 0, self.WIDTH, height))

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
        """获取字体 - 支持多种字体回退，确保能显示特殊字符"""
        cache_key = f"{size}_{bold}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # 字体列表按优先级排序，支持中文、日文、韩文、特殊符号、Emoji
        font_paths = []

        if bold:
            font_paths.extend([
                "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
                "C:/Windows/Fonts/simsunb.ttf",  # 宋体粗体
                "C:/Windows/Fonts/msgothic.ttc",  # MS Gothic (日文)
                "C:/Windows/Fonts/malgunbd.ttf",  # 韩语
            ])
        else:
            font_paths.extend([
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/msyhl.ttc",  # 微软雅黑细体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/msgothic.ttc",  # MS Gothic (日文)
                "C:/Windows/Fonts/malgun.ttf",  # 韩语
                "C:/Windows/Fonts/segoeui.ttf",  # Segoe UI (支持特殊符号)
                "C:/Windows/Fonts/arial.ttf",  # Arial
            ])

        # Linux 字体（Ubuntu/Debian/CentOS 等）
        font_paths.extend([
            # Ubuntu/Debian 常见字体
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            # CentOS/RHEL 常见字体
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
            # 通用路径
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
        ])

        # macOS 字体
        font_paths.extend([
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
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

    def _get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取曲绘（支持大小写不敏感和多种扩展名）"""
        if song_key in self._illustration_cache:
            return self._illustration_cache[song_key].copy()

        # 查找曲绘文件
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
                logger.info(f"✅ 找到曲绘: {song_key} -> {matched_file.name}")
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

        布局参考：
        - 三列交错排列（L/M/R）
        - M列向下偏移 5%，R列向下偏移 8%
        - 每列最多10个卡片
        """
        logger.info(f"🎨 开始渲染 Best30，玩家: {data.get('gameuser', {}).get('nickname', 'Unknown')}")

        try:
            gameuser = data.get('gameuser', {})
            records = data.get('records', [])[:30]

            if not records:
                logger.error("❌ 没有成绩记录可渲染")
                return False

            # 计算布局
            cards_per_col = 10
            num_cols = 3

            # 计算总高度
            col_offsets = [0, int(self.CARD_HEIGHT * 0.5), int(self.CARD_HEIGHT * 0.8)]
            max_cards_in_col = min(cards_per_col, (len(records) + num_cols - 1) // num_cols)
            content_height = max_cards_in_col * (self.CARD_HEIGHT + self.CARD_MARGIN) + max(col_offsets)
            total_height = self.HEADER_HEIGHT + content_height + 100

            # 并行预加载曲绘（大幅提升性能）
            logger.info("🚀 并行预加载曲绘...")
            await self._preload_illustrations(records)

            # 加载背景图片
            img = self._get_background_image(total_height)
            draw = ImageDraw.Draw(img)

            # 绘制头部
            self._draw_header(img, draw, gameuser)

            # 绘制三列卡片（使用预加载的曲绘）
            start_y = self.HEADER_HEIGHT + 30
            col_x_positions = [30, 420, 810]

            for i, record in enumerate(records):
                col = i % 3
                row = i // 3
                x = col_x_positions[col]
                y = start_y + row * (self.CARD_HEIGHT + self.CARD_MARGIN) + col_offsets[col]
                self._draw_song_card_fast(img, draw, i + 1, record, x, y)
            
            # 绘制底部
            self._draw_footer(img, draw, total_height - 50)
            
            # 保存（优化：使用最快压缩级别）
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _draw_header(self, img: Image.Image, draw: ImageDraw.Draw, gameuser: Dict):
        """绘制头部（玩家信息）"""
        # 黑色半透明背景块
        self._draw_rounded_rect(draw,
                               (50, 30, self.WIDTH - 50, self.HEADER_HEIGHT - 30),
                               10, (0, 0, 0, 128))

        # 头像区域（圆形）
        avatar_size = 80
        avatar_x = 80
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
        info_x = avatar_x + avatar_size + 30

        # 课题模式段位 - 先加载段位图片获取尺寸
        challenge_rank = gameuser.get('challengeModeRank', 0)
        rank_badge_width = 0
        rank_img_resized = None
        if challenge_rank and challenge_rank > 0:
            rank_names = {
                1: "白色", 2: "绿色", 3: "蓝色", 4: "红色", 5: "金色", 6: "彩色"
            }
            rank_name = rank_names.get(challenge_rank, "")

            # 加载段位颜色图片
            rank_img_path = self.plugin_dir / "resources" / "img" / "other" / f"{rank_name}.png"
            if rank_img_path.exists():
                try:
                    rank_img = Image.open(rank_img_path).convert("RGBA")
                    # 调整大小 - 段位徽章与昵称同高
                    badge_height = 28
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 10  # 徽章宽度 + 间距
                except Exception as e:
                    logger.warning(f"加载段位图片失败: {e}")

        # 昵称 - 智能获取，支持特殊字符
        font_name = self._get_font(28, bold=True)
        nickname = gameuser.get('nickname', '')
        # 如果昵称为空，尝试其他字段
        if not nickname or nickname == 'Unknown':
            nickname = gameuser.get('name', '') or gameuser.get('alias', '') or 'Phigros Player'
        # 限制昵称长度，避免溢出
        if len(nickname) > 20:
            nickname = nickname[:18] + '...'
        
        # 昵称位置（如果有段位徽章，留出空间）
        nickname_x = info_x + rank_badge_width
        self._draw_text_safe(draw, (nickname_x, avatar_y + 5), nickname, fill='white', font=font_name)
        
        # 在昵称左侧显示段位徽章
        if rank_img_resized:
            badge_x = info_x
            badge_y = avatar_y + 8  # 与昵称垂直居中对齐
            img.paste(rank_img_resized, (badge_x, badge_y), rank_img_resized)

        # ID - 智能获取，避免显示 N/A
        font_id = self._get_font(14)
        player_id = gameuser.get('PlayerId', '')
        # 如果 ID 为空或 N/A，尝试其他字段
        if not player_id or player_id == 'N/A':
            player_id = gameuser.get('playerId', '') or gameuser.get('id', '') or gameuser.get('uid', '')
        if not player_id or player_id == 'N/A':
            player_id = "TapTap User"
        # 限制 ID 长度
        if len(player_id) > 25:
            player_id = player_id[:22] + '...'
        self._draw_text_safe(draw, (info_x, avatar_y + 45), f"ID: {player_id}", fill='#aaaaaa', font=font_id)
        
        # RKS 框（白色背景）
        rks_width = 140
        rks_height = 80
        rks_x = self.WIDTH - rks_width - 80
        rks_y = (self.HEADER_HEIGHT - rks_height) // 2
        
        self._draw_rounded_rect(draw,
                               (rks_x, rks_y, rks_x + rks_width, rks_y + rks_height),
                               8, (255, 255, 255, 255))
        
        # RKS 文字
        font_rks_label = self._get_font(12)
        font_rks_value = self._get_font(26, bold=True)
        rks = gameuser.get('rks', 0)
        
        draw.text((rks_x + rks_width // 2, rks_y + 18), "RKS", 
                 fill='black', font=font_rks_label, anchor='mm')
        draw.text((rks_x + rks_width // 2, rks_y + 50), f"{rks:.4f}", 
                 fill='black', font=font_rks_value, anchor='mm')
    
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
            # 绘制占位符
            draw.rectangle([x, y, x + illust_width, y + illust_height], fill='#333333')
        
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

    def _draw_song_card_fast(self, img: Image.Image, draw: ImageDraw.Draw, rank: int,
                              record: Dict, x: int, y: int):
        """快速绘制歌曲卡片（使用预加载的曲绘）"""
        card_width = self.CARD_WIDTH
        card_height = self.CARD_HEIGHT
        illust_width = card_width // 2
        illust_height = card_height

        # 使用预加载的曲绘
        song = record.get('song', '')
        cache_key = song.lower()
        illust = self._processed_illust_cache.get(cache_key)

        if illust:
            # 预加载的曲绘已经调整过大小
            img.paste(illust, (x, y))
        else:
            # 回退：绘制占位符
            draw.rectangle([x, y, x + illust_width, y + illust_height], fill='#333333')

        # 排名徽章（简化绘制）
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

        # 绘制背景和边框
        bg_color = (40, 40, 55)
        self._draw_rounded_rect(draw,
                               (info_x, info_y, info_x + info_width, info_y + info_height),
                               5, (*bg_color, 255))
        draw.rectangle([info_x, info_y, info_x + 3, info_y + info_height],
                      fill=self._hex_to_rgb(diff_color))

        # 文字信息（简化版，不使用发光效果以提升性能）
        font_song = self._get_font(13, bold=True)
        song_name = record.get('song', 'Unknown')
        if len(song_name) > 12:
            song_name = song_name[:10] + '...'
        draw.text((info_x + 10, info_y + 8), song_name, fill='white', font=font_song)

        font_score = self._get_font(18, bold=True)
        score = record.get('score', 0)
        draw.text((info_x + 10, info_y + 32), f"{score:,}", fill='#ffd700', font=font_score)

        font_acc = self._get_font(10)
        acc = record.get('acc', 0)
        rks = record.get('rks', 0)
        draw.text((info_x + 10, info_y + 58), f"Acc: {acc:.2f}%", fill='#aaaaaa', font=font_acc)
        draw.text((info_x + 10, info_y + 73), f"RKS: {rks:.2f}", fill='#aaaaaa', font=font_acc)

        # 评级图片
        rating = self._calculate_rating(score, acc, record.get('fc', False))
        rating_img = self._get_rating_image(rating)
        if rating_img:
            rating_height = 40
            rating_width = int(rating_height * rating_img.width / rating_img.height)
            rating_resized = rating_img.resize((rating_width, rating_height), Image.Resampling.LANCZOS)
            rating_x = info_x + info_width - rating_width - 10
            rating_y = info_y + (info_height - rating_height) // 2
            img.paste(rating_resized, (rating_x, rating_y), rating_resized)

        # FC/AP 标识
        if record.get('fc'):
            score_val = record.get('score', 0)
            fc_text = 'AP' if score_val == 1000000 else 'FC'
            fc_color = '#ffd700' if score_val == 1000000 else '#00b0f0'
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
        
        # 绘制发光效果
        for offset in range(glow_radius, 0, -1):
            alpha = int(40 - offset * 8)  # 逐渐减淡
            if alpha <= 0:
                continue
            glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            # 绘制8个方向的发光
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset),
                          (-offset, -offset), (offset, -offset), (-offset, offset), (offset, offset)]:
                if anchor:
                    glow_draw.text((x + dx, y + dy), text, fill=(*glow_color, alpha), font=font, anchor=anchor)
                else:
                    glow_draw.text((x + dx, y + dy), text, fill=(*glow_color, alpha), font=font)
            # 模糊发光层
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=offset))
            img.paste(glow_layer, (0, 0), glow_layer)
        
        # 绘制主文字
        if anchor:
            draw.text((x, y), text, fill=text_color, font=font, anchor=anchor)
        else:
            draw.text((x, y), text, fill=text_color, font=font)

    def _draw_footer(self, img: Image.Image, draw: ImageDraw.Draw, y: int):
        """绘制底部（带发光效果）"""
        text = "phigros插件——飞翔的死猪提供技术支持"
        font = self._get_font(14)
        self._draw_text_with_glow(img, self.WIDTH // 2, y, text, '#ffffff', font,
                                  glow_color=(100, 200, 255), glow_radius=8, anchor='mm')
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        logger.warning("单曲成绩渲染暂未实现")
        return False
