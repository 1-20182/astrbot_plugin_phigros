import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# 简单的日志类
class SimpleLogger:
    @staticmethod
    def info(msg):
        print(f"[INFO] {msg}")
    
    @staticmethod
    def error(msg):
        print(f"[ERROR] {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"[WARNING] {msg}")
    
    @staticmethod
    def debug(msg):
        print(f"[DEBUG] {msg}")

logger = SimpleLogger()

class PhiStyleRendererStandalone:
    """
    🎨 Phi-Plugin 风格渲染器 - 独立版本
    
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
    HEADER_HEIGHT = 180
    CARD_WIDTH = 350
    CARD_HEIGHT = 90
    CARD_MARGIN = 8
    OVERFLOW_HEADER_HEIGHT = 120
    
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
        await self._preload_resources()
    
    async def _preload_resources(self):
        """预加载常用资源到缓存"""
        logger.info("🚀 预加载渲染资源...")
        
        ratings = ['φ', 'V', 'S', 'A', 'B', 'C', 'F', 'FC']
        for rating in ratings:
            self._get_rating_image(rating)
        
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

    def _get_background_image(self, height: int) -> Image.Image:
        """获取背景图片（带缓存）"""
        logger.info("=== _get_background_image ===")
        if self._bg_cache is None or self._bg_cache.height < height:
            bg_path = self.plugin_dir / "resources" / "img" / "background" / "c774204e373ad3ab3a4137c7e5a930da.jpg"
            logger.info(f"背景图片路径: {bg_path}")
            logger.info(f"背景图片是否存在: {bg_path.exists()}")
            if bg_path.exists():
                try:
                    bg_img = Image.open(bg_path).convert("RGB")
                    logger.info(f"✅ 背景图片加载成功")
                    
                    scale_factor = 0.5
                    small_size = (int(self.WIDTH * scale_factor), int(height * scale_factor))
                    bg_img = bg_img.resize(small_size, Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=3))
                    bg_img = bg_img.resize((self.WIDTH, height), Image.Resampling.LANCZOS)
                    enhancer = ImageEnhance.Brightness(bg_img)
                    bg_img = enhancer.enhance(0.4)
                    self._bg_cache = bg_img
                    return bg_img.copy()
                except Exception as e:
                    logger.warning(f"加载背景图片失败: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())
            return Image.new('RGB', (self.WIDTH, height), (26, 26, 46))
        else:
            return self._bg_cache.crop((0, 0, self.WIDTH, height))

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """获取字体"""
        cache_key = f"{size}_{bold}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_paths = []
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

        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, size)
                    self._font_cache[cache_key] = font
                    return font
                except Exception as e:
                    continue

        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font

    def _draw_text_safe(self, draw: ImageDraw.Draw, xy, text: str, fill, font: ImageFont.FreeTypeFont, anchor=None):
        """安全绘制文本"""
        try:
            if anchor:
                draw.text(xy, text, fill=fill, font=font, anchor=anchor)
            else:
                draw.text(xy, text, fill=fill, font=font)
        except Exception as e:
            logger.warning(f"绘制文本失败 '{text}': {e}")

    def _get_rating_image(self, rating: str) -> Optional[Image.Image]:
        """获取评级图片"""
        if rating in self._rating_cache:
            return self._rating_cache[rating].copy()

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

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """十六进制颜色转 RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _draw_rounded_rect(self, draw: ImageDraw.Draw, xy: Tuple[int, int, int, int], 
                          radius: int, fill: Tuple[int, int, int, int]):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = xy
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    def _draw_header(self, img: Image.Image, draw: ImageDraw.Draw, gameuser: Dict):
        """绘制头部（玩家信息）"""
        logger.info("=== _draw_header ===")
        logger.info(f"gameuser: {gameuser}")
        
        self._draw_rounded_rect(draw,
                               (40, 20, self.WIDTH - 40, self.HEADER_HEIGHT - 20),
                               12, (0, 0, 0, 150))

        avatar_size = 100
        avatar_x = 60
        avatar_y = (self.HEADER_HEIGHT - avatar_size) // 2

        info_x = avatar_x + avatar_size + 25

        challenge_rank = gameuser.get('challengeModeRank', 0)
        logger.info(f"challenge_rank: {challenge_rank}")
        rank_badge_width = 0
        rank_img_resized = None
        if challenge_rank and challenge_rank > 0:
            rank_names = {
                1: "白色", 2: "绿色", 3: "蓝色", 4: "红色", 5: "金色", 6: "彩色"
            }
            rank_name = rank_names.get(challenge_rank, "")
            logger.info(f"rank_name: {rank_name}")

            rank_img_path = self.plugin_dir / "resources" / "img" / "other" / f"{rank_name}.png"
            logger.info(f"段位图片路径: {rank_img_path}")
            logger.info(f"段位图片是否存在: {rank_img_path.exists()}")
            if rank_img_path.exists():
                try:
                    rank_img = Image.open(rank_img_path).convert("RGBA")
                    badge_height = 36
                    badge_width = int(badge_height * rank_img.width / rank_img.height)
                    rank_img_resized = rank_img.resize((badge_width, badge_height), Image.Resampling.LANCZOS)
                    rank_badge_width = badge_width + 15
                    logger.info(f"✅ 段位图片加载成功，大小: {rank_img_resized.size}")
                except Exception as e:
                    logger.warning(f"加载段位图片失败: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())

        font_name = self._get_font(28, bold=True)
        nickname = gameuser.get('nickname', '')
        if not nickname or nickname == 'Unknown':
            nickname = gameuser.get('name', '') or gameuser.get('alias', '') or 'Phigros Player'
        if len(nickname) > 20:
            nickname = nickname[:18] + '...'
        
        nickname_x = info_x + rank_badge_width
        self._draw_text_safe(draw, (nickname_x, avatar_y + 6), nickname, fill='white', font=font_name)
        
        if rank_img_resized:
            badge_x = info_x
            badge_y = avatar_y + 10
            logger.info(f"准备粘贴段位图片到位置: ({badge_x}, {badge_y})")
            img.paste(rank_img_resized, (badge_x, badge_y), rank_img_resized)
            logger.info("✅ 段位图片已粘贴")

        font_id = self._get_font(14)
        player_id = gameuser.get('PlayerId', '')
        if not player_id or player_id == 'N/A':
            player_id = gameuser.get('playerId', '') or gameuser.get('id', '') or gameuser.get('uid', '')
        if not player_id or player_id == 'N/A':
            player_id = "TapTap User"
        if len(player_id) > 30:
            player_id = player_id[:27] + '...'
        self._draw_text_safe(draw, (info_x, avatar_y + 45), f"ID: {player_id}", fill='#aaaaaa', font=font_id)
        
        rks_width = 150
        rks_height = 90
        rks_x = self.WIDTH - rks_width - 60
        rks_y = (self.HEADER_HEIGHT - rks_height) // 2
        
        self._draw_rounded_rect(draw,
                               (rks_x, rks_y, rks_x + rks_width, rks_y + rks_height),
                               10, (255, 255, 255, 255))
        
        font_rks_label = self._get_font(14, bold=True)
        font_rks_value = self._get_font(30, bold=True)
        rks = gameuser.get('rks', 0)
        
        draw.text((rks_x + rks_width // 2, rks_y + 22), "RKS", 
                 fill='black', font=font_rks_label, anchor='mm')
        draw.text((rks_x + rks_width // 2, rks_y + 58), f"{rks:.4f}", 
                 fill='black', font=font_rks_value, anchor='mm')
    
    async def render_b30(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染 Best30 成绩图"""
        logger.info(f"🎨 开始渲染 Best30，玩家: {data.get('gameuser', {}).get('nickname', 'Unknown')}")

        try:
            gameuser = data.get('gameuser', {})
            
            total_height = self.HEADER_HEIGHT + 500

            img = self._get_background_image(total_height)
            draw = ImageDraw.Draw(img)
            
            self._draw_header(img, draw, gameuser)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', compress_level=1, optimize=False)
            logger.info(f"✅ 渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
