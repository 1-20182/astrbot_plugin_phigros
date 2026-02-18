"""
Phigros 数据渲染器（重构版）
参考 phi-plugin 架构，使用模板引擎 + PIL 渲染
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from io import BytesIO
from jinja2 import Template
import base64

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
except ImportError as e:
    raise ImportError(f"缺少依赖: {e}\n请运行: pip install Pillow")


class PhigrosRenderer:
    """Phigros 数据渲染器（模板引擎版）"""

    def __init__(self, cache_dir: str = "./cache", illustration_path: Optional[str] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 设置曲绘路径
        self.illustration_path = Path(illustration_path) if illustration_path else Path(__file__).parent / "ILLUSTRATION"
        
        # 资源路径
        self.res_path = Path(__file__).parent / "resources"
        self.res_path.mkdir(exist_ok=True)
        self.html_path = self.res_path / "html"
        self.html_path.mkdir(exist_ok=True)
        
        # 字体缓存
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._base_height = 1080  # 基准高度
        
        # 曲绘缓存
        self._illustration_cache: Dict[str, Image.Image] = {}
        self._illustration_map: Dict[str, str] = {}
        self._build_illustration_map()

    def _build_illustration_map(self):
        """构建曲绘文件名映射"""
        if not self.illustration_path.exists():
            return
            
        for file in self.illustration_path.glob("*.png"):
            name = file.stem
            self._illustration_map[name.lower()] = str(file)
            
            # 同时存储简化版本（只取曲名部分）
            if "." in name:
                song_name = name.split(".")[0].lower()
                self._illustration_map[song_name] = str(file)

    async def initialize(self):
        """初始化渲染器"""
        pass

    async def terminate(self):
        """清理资源"""
        pass

    def _get_font(self, size: int, target_height: int = None) -> ImageFont.FreeTypeFont:
        """获取字体，根据目标高度按比例缩放"""
        # 计算缩放比例，以1080p为基准
        if target_height is None:
            target_height = self._base_height
        
        # 确保字体大小合适，最小为基准大小的0.6倍，最大为1.5倍
        scale = max(0.6, min(1.5, target_height / self._base_height))
        scaled_size = int(size * scale)
        
        # 确保字体大小在合理范围内
        scaled_size = max(12, min(120, scaled_size))
        
        cache_key = f"{scaled_size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # 尝试加载系统字体
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, scaled_size)
                    self._font_cache[cache_key] = font
                    return font
                except Exception:
                    continue
        
        # 使用默认字体
        return ImageFont.load_default()

    def get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取歌曲曲绘"""
        if song_key in self._illustration_cache:
            return self._illustration_cache[song_key].copy()
        
        file_path = None
        key_lower = song_key.lower()
        
        if key_lower in self._illustration_map:
            file_path = self._illustration_map[key_lower]
        else:
            song_name = key_lower.split(".")[0] if "." in key_lower else key_lower
            if song_name in self._illustration_map:
                file_path = self._illustration_map[song_name]
        
        if file_path and Path(file_path).exists():
            try:
                img = Image.open(file_path).convert("RGBA")
                self._illustration_cache[song_key] = img
                return img.copy()
            except Exception as e:
                print(f"加载曲绘失败: {e}")
        
        return None

    def _create_gradient_background(self, size: Tuple[int, int], 
                                    color1: Tuple[int, int, int] = (30, 30, 50),
                                    color2: Tuple[int, int, int] = (70, 90, 130)) -> Image.Image:
        """创建渐变背景"""
        img = Image.new("RGBA", size, color1)
        draw = ImageDraw.Draw(img)
        
        for y in range(size[1]):
            ratio = y / size[1]
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b, 255))
        
        return img

    def _create_rounded_rectangle(self, size: Tuple[int, int], radius: int, 
                                   color: Tuple[int, ...]) -> Image.Image:
        """创建圆角矩形"""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=color)
        return img

    def _draw_text(self, draw: ImageDraw.Draw, text: str, pos: Tuple[int, int],
                   font_size: int, color: Tuple[int, ...] = (255, 255, 255, 255),
                   target_height: int = None) -> Tuple[int, int]:
        """绘制文字，返回文字尺寸"""
        font = self._get_font(font_size, target_height)
        draw.text(pos, text, font=font, fill=color)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _draw_text_with_shadow(self, draw: ImageDraw.Draw, text: str, pos: Tuple[int, int],
                                font_size: int, color: Tuple[int, ...] = (255, 255, 255, 255),
                                shadow_color: Tuple[int, ...] = (0, 0, 0, 128),
                                offset: int = 2, target_height: int = None):
        """绘制带阴影的文字"""
        font = self._get_font(font_size, target_height)
        x, y = pos
        # 阴影
        draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
        # 文字
        draw.text((x, y), text, font=font, fill=color)

    def _resize_illustration(self, img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """调整曲绘大小，保持比例裁剪"""
        img_ratio = img.width / img.height
        target_ratio = size[0] / size[1]
        
        if img_ratio > target_ratio:
            new_height = size[1]
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            left = (new_width - size[0]) // 2
            img = img.crop((left, 0, left + size[0], size[1]))
        else:
            new_width = size[0]
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            top = (new_height - size[1]) // 2
            img = img.crop((0, top, size[0], top + size[1]))
        
        return img

    def _create_illustration_card(self, illust: Image.Image, size: Tuple[int, int], 
                                   radius: int = 20) -> Image.Image:
        """创建带圆角的曲绘卡片"""
        resized = self._resize_illustration(illust, size)
        
        # 创建圆角遮罩
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
        
        # 应用遮罩
        result = Image.new('RGBA', size, (0, 0, 0, 0))
        result.paste(resized, (0, 0))
        result.putalpha(mask)
        
        return result

    async def render_save_data(self, data: Dict[str, Any], output_path: str) -> str:
        """渲染用户存档数据（紧凑版）"""
        # 图片尺寸 - 使用固定尺寸，不缩放
        img_width, img_height = 1920, 1080
        
        # 创建渐变背景
        canvas = self._create_gradient_background(
            (img_width, img_height),
            (20, 20, 35),
            (35, 40, 60)
        )
        draw = ImageDraw.Draw(canvas)
        
        # 解析数据
        save = data.get("save", {})
        game_record = save.get("game_record", {})
        summary = data.get("summary", {})
        
        rks = summary.get("rks", 0)
        peak_rks = summary.get("peakRks", 0)
        
        # 固定字体大小（不根据高度缩放）
        font_title = self._get_font(48)
        font_info = self._get_font(32)
        font_song = self._get_font(22)
        font_detail = self._get_font(18)
        
        # 绘制标题栏 - 更紧凑
        title_bar = self._create_rounded_rectangle((1860, 70), 15, (0, 0, 0, 200))
        canvas.paste(title_bar, (30, 20), title_bar)
        self._draw_text_with_shadow(draw, "Phigros 存档数据", (50, 35), 48, target_height=None)
        
        # 玩家信息卡片 - 更紧凑
        info_card = self._create_rounded_rectangle((400, 140), 15, (0, 0, 0, 180))
        canvas.paste(info_card, (30, 100), info_card)
        
        # RKS 信息
        self._draw_text_with_shadow(draw, f"RKS: {rks:.4f}", (45, 115), 32, target_height=None)
        self._draw_text_with_shadow(draw, f"Peak: {peak_rks:.4f}", (45, 155), 28, 
                                     color=(255, 215, 0, 255), target_height=None)
        self._draw_text_with_shadow(draw, f"Records: {len(game_record)}", (45, 195), 24, target_height=None)
        
        # Best 成绩标题
        self._draw_text_with_shadow(draw, "Best 成绩", (30, 260), 32, target_height=None)
        
        # 成绩卡片区域 - 更紧凑的布局
        y_offset = 300
        x_positions = [30, 330, 630, 930, 1230, 1530]
        
        count = 0
        for song_key, records in list(game_record.items())[:24]:  # 显示更多
            if count > 0 and count % 6 == 0:
                y_offset += 280
                if y_offset > 1000:
                    break
            
            x_pos = x_positions[count % 6]
            
            # 曲绘卡片背景 - 更小
            card_bg = self._create_rounded_rectangle((280, 270), 12, (0, 0, 0, 140))
            canvas.paste(card_bg, (x_pos, y_offset), card_bg)
            
            # 获取曲绘
            illust = self.get_illustration(song_key)
            if illust:
                ill_card = self._create_illustration_card(illust, (260, 170), 10)
                canvas.paste(ill_card, (x_pos + 10, y_offset + 8), ill_card)
            else:
                placeholder = self._create_rounded_rectangle((260, 170), 10, (50, 50, 70, 180))
                canvas.paste(placeholder, (x_pos + 10, y_offset + 8), placeholder)
            
            # 歌曲信息
            record = records[0] if records else {}
            diff = record.get("difficulty", "?").upper()
            score = record.get("score", 0)
            acc = record.get("accuracy", 0)
            
            song_name = song_key.split(".")[0] if "." in song_key else song_key
            if len(song_name) > 8:
                song_name = song_name[:7] + ".."
            
            # 难度颜色
            diff_colors = {
                "EZ": (102, 204, 102, 255),
                "HD": (102, 178, 255, 255),
                "IN": (255, 102, 178, 255),
                "AT": (178, 102, 255, 255)
            }
            diff_color = diff_colors.get(diff, (200, 200, 200, 255))
            
            # 绘制信息 - 更紧凑
            self._draw_text_with_shadow(draw, song_name, (x_pos + 12, y_offset + 185), 
                                       22, target_height=None)
            self._draw_text_with_shadow(draw, f"[{diff}] {score}", (x_pos + 12, y_offset + 215), 
                                       18, color=diff_color, target_height=None)
            self._draw_text_with_shadow(draw, f"Acc: {acc:.2f}%", (x_pos + 12, y_offset + 240), 
                                       16, target_height=None)
            
            count += 1
        
        # 保存图片
        canvas = canvas.convert("RGB")
        canvas.save(output_path, "PNG", quality=95)
        return output_path

    async def render_song_detail(self, song_data: Dict[str, Any], output_path: str) -> str:
        """渲染歌曲详情（重构版）"""
        img_width, img_height = 1200, 800
        
        song_name = song_data.get("name", "未知")
        composer = song_data.get("composer", "未知")
        illustrator = song_data.get("illustrator", "未知")
        constants = song_data.get("chartConstants", {})
        
        # 获取曲绘作为背景
        song_key = f"{song_name}.{composer}"
        illust = self.get_illustration(song_key) or self.get_illustration(song_name)
        
        if illust:
            # 使用曲绘作为背景
            bg = self._resize_illustration(illust, (img_width, img_height))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
            enhancer = ImageEnhance.Brightness(bg)
            bg = enhancer.enhance(0.3)
            canvas = bg.convert("RGBA")
        else:
            # 使用渐变背景
            canvas = self._create_gradient_background(
                (img_width, img_height),
                (30, 30, 50),
                (60, 80, 120)
            )
        
        draw = ImageDraw.Draw(canvas)
        
        # 主卡片
        card = self._create_rounded_rectangle((1100, 700), 30, (0, 0, 0, 180))
        canvas.paste(card, (50, 50), card)
        
        # 曲绘展示
        if illust:
            ill_card = self._create_illustration_card(illust, (400, 400), 25)
            canvas.paste(ill_card, (100, 100), ill_card)
        
        # 歌曲信息
        x_info = 540
        y_info = 120
        
        self._draw_text_with_shadow(draw, song_name, (x_info, y_info), 48, target_height=img_height)
        y_info += 70
        self._draw_text_with_shadow(draw, f"作曲: {composer}", (x_info, y_info), 28, target_height=img_height)
        y_info += 50
        self._draw_text_with_shadow(draw, f"曲绘: {illustrator}", (x_info, y_info), 24, target_height=img_height)
        y_info += 70
        self._draw_text_with_shadow(draw, "谱面定数:", (x_info, y_info), 28, target_height=img_height)
        y_info += 50
        
        # 难度标签
        diff_names = {"ez": "EZ", "hd": "HD", "in": "IN", "at": "AT"}
        diff_colors = {
            "ez": (102, 204, 102, 200),
            "hd": (102, 178, 255, 200),
            "in": (255, 102, 178, 200),
            "at": (178, 102, 255, 200)
        }
        
        x_diff = x_info
        for diff_key, diff_name in diff_names.items():
            val = constants.get(diff_key)
            if val is not None:
                tag_bg = self._create_rounded_rectangle((100, 45), 10, diff_colors[diff_key])
                canvas.paste(tag_bg, (x_diff, y_info), tag_bg)
                self._draw_text(draw, f"{diff_name}: {val}", (x_diff + 10, y_info + 8), 
                               20, target_height=img_height)
                x_diff += 120
        
        canvas = canvas.convert("RGB")
        canvas.save(output_path, "PNG", quality=95)
        return output_path

    async def render_best30(self, data: Dict[str, Any], output_path: str) -> str:
        """渲染 Best30 成绩图"""
        img_width, img_height = 1920, 1080
        
        # 创建渐变背景
        canvas = self._create_gradient_background(
            (img_width, img_height),
            (20, 20, 35),
            (35, 40, 60)
        )
        draw = ImageDraw.Draw(canvas)
        
        # 解析数据
        save = data.get("save", {})
        game_record = save.get("game_record", {})
        summary = data.get("summary", {})
        
        rks = summary.get("rks", 0)
        
        # 计算每首歌曲的 RKS 贡献值并排序
        # RKS = (acc * 0.9 + 定数) * 某个系数，这里简化处理
        song_list = []
        for song_key, records in game_record.items():
            if not records:
                continue
            record = records[0]  # 取最佳成绩
            acc = record.get("accuracy", 0)
            score = record.get("score", 0)
            diff = record.get("difficulty", "?").upper()
            
            # 简化的 RKS 计算 (实际计算更复杂)
            # 这里按准确率排序
            song_list.append({
                "song_key": song_key,
                "acc": acc,
                "score": score,
                "diff": diff,
                "record": record
            })
        
        # 按准确率排序，取前30
        song_list.sort(key=lambda x: x["acc"], reverse=True)
        best30 = song_list[:30]
        
        # 绘制标题栏
        title_bar = self._create_rounded_rectangle((1860, 70), 15, (0, 0, 0, 200))
        canvas.paste(title_bar, (30, 20), title_bar)
        self._draw_text_with_shadow(draw, f"Best 30 - RKS: {rks:.4f}", (50, 35), 48, target_height=None)
        
        # 绘制 Best30 卡片 - 5行6列布局
        y_offset = 110
        x_positions = [30, 350, 670, 990, 1310, 1630]
        
        for i, song_data in enumerate(best30):
            if i > 0 and i % 6 == 0:
                y_offset += 310
                if y_offset > 1000:
                    break
            
            x_pos = x_positions[i % 6]
            
            # 歌曲信息
            song_key = song_data["song_key"]
            acc = song_data["acc"]
            score = song_data["score"]
            diff = song_data["diff"]
            
            song_name = song_key.split(".")[0] if "." in song_key else song_key
            if len(song_name) > 10:
                song_name = song_name[:9] + ".."
            
            # 难度颜色
            diff_colors = {
                "EZ": (102, 204, 102, 255),
                "HD": (102, 178, 255, 255),
                "IN": (255, 102, 178, 255),
                "AT": (178, 102, 255, 255)
            }
            diff_color = diff_colors.get(diff, (200, 200, 200, 255))
            
            # 卡片背景
            card_bg = self._create_rounded_rectangle((300, 290), 12, (0, 0, 0, 140))
            canvas.paste(card_bg, (x_pos, y_offset), card_bg)
            
            # 排名标签 (1-3名特殊颜色)
            rank_colors = {
                0: (255, 215, 0, 200),    # 金牌
                1: (192, 192, 192, 200),  # 银牌
                2: (205, 127, 50, 200)    # 铜牌
            }
            rank_color = rank_colors.get(i, (80, 80, 80, 150))
            
            rank_bg = self._create_rounded_rectangle((40, 30), 8, rank_color)
            canvas.paste(rank_bg, (x_pos + 10, y_offset + 10), rank_bg)
            self._draw_text(draw, str(i + 1), (x_pos + 18, y_offset + 12), 18, 
                           color=(255, 255, 255, 255), target_height=None)
            
            # 获取曲绘
            illust = self.get_illustration(song_key)
            if illust:
                ill_card = self._create_illustration_card(illust, (280, 180), 10)
                canvas.paste(ill_card, (x_pos + 10, y_offset + 45), ill_card)
            else:
                placeholder = self._create_rounded_rectangle((280, 180), 10, (50, 50, 70, 180))
                canvas.paste(placeholder, (x_pos + 10, y_offset + 45), placeholder)
            
            # 歌曲信息
            self._draw_text_with_shadow(draw, song_name, (x_pos + 15, y_offset + 235), 
                                       22, target_height=None)
            self._draw_text_with_shadow(draw, f"[{diff}] {score}", (x_pos + 15, y_offset + 260), 
                                       18, color=diff_color, target_height=None)
            self._draw_text_with_shadow(draw, f"Acc: {acc:.2f}%", (x_pos + 15, y_offset + 280), 
                                       16, target_height=None)
        
        # 保存图片
        canvas = canvas.convert("RGB")
        canvas.save(output_path, "PNG", quality=95)
        return output_path

    async def render_leaderboard(self, data: Dict[str, Any], output_path: str) -> str:
        """渲染排行榜（重构版）"""
        img_width, img_height = 1920, 1080
        
        # 创建渐变背景
        canvas = self._create_gradient_background(
            (img_width, img_height),
            (25, 25, 40),
            (50, 60, 90)
        )
        draw = ImageDraw.Draw(canvas)
        
        items = data.get("items", [])
        
        # 标题
        title_bar = self._create_rounded_rectangle((1800, 80), 20, (0, 0, 0, 180))
        canvas.paste(title_bar, (60, 40), title_bar)
        self._draw_text_with_shadow(draw, "🏆 Phigros RKS 排行榜", (90, 55), 40, target_height=img_height)
        
        # 绘制排行榜项
        y_offset = 140
        for i, item in enumerate(items[:15]):
            rank = item.get("rank", 0)
            alias = item.get("alias", "未知")
            score = item.get("score", 0)
            
            # 排名颜色
            rank_colors = {
                1: (255, 215, 0, 200),    # 金牌
                2: (192, 192, 192, 200),  # 银牌
                3: (205, 127, 50, 200)    # 铜牌
            }
            rank_color = rank_colors.get(rank, (100, 100, 100, 150))
            
            # 排名标签
            rank_bg = self._create_rounded_rectangle((60, 50), 12, rank_color)
            canvas.paste(rank_bg, (60, y_offset), rank_bg)
            self._draw_text(draw, str(rank), (75, y_offset + 8), 24, 
                           color=(0, 0, 0, 255), target_height=img_height)
            
            # 玩家卡片
            card = self._create_rounded_rectangle((900, 55), 15, (0, 0, 0, 130))
            canvas.paste(card, (140, y_offset - 2), card)
            
            # 玩家信息
            self._draw_text_with_shadow(draw, alias, (160, y_offset + 8), 26, target_height=img_height)
            self._draw_text_with_shadow(draw, f"RKS: {score:.4f}", (700, y_offset + 12), 
                                       22, color=(255, 215, 0, 255), target_height=img_height)
            
            y_offset += 70
        
        canvas = canvas.convert("RGB")
        canvas.save(output_path, "PNG", quality=95)
        return output_path
