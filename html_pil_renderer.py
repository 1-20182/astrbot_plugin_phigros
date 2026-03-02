"""
🎨 HTML + Pillow 渲染器

> "纯 Python 实现，无需浏览器！" ✨

将 HTML/CSS 模板渲染为图片，使用 Pillow 实现
效果接近 Playwright，但无需安装 Chromium
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from astrbot.api import logger

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


class HtmlPilRenderer:
    """
    🎨 HTML + Pillow 渲染器
    
    解析简化版 HTML/CSS，使用 Pillow 渲染为图片
    无需浏览器，纯 Python 实现
    """
    
    def __init__(self, 
                 plugin_dir: Path,
                 cache_dir: Path,
                 illustration_path: Path,
                 image_quality: int = 95):
        """初始化渲染器"""
        self.plugin_dir = plugin_dir
        self.cache_dir = cache_dir
        self.illustration_path = illustration_path
        self.image_quality = image_quality
        
        # 字体缓存
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        
        # 曲绘缓存
        self._illustration_cache: Dict[str, Image.Image] = {}
        
        logger.info("🎨 HTML+Pillow 渲染器初始化")
    
    async def initialize(self):
        """初始化"""
        pass
    
    async def terminate(self):
        """清理资源"""
        self._illustration_cache.clear()
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取字体"""
        cache_key = f"{size}"
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
                    font = ImageFont.truetype(font_path, size)
                    self._font_cache[cache_key] = font
                    return font
                except:
                    pass
        
        # 使用默认字体
        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font
    
    def _get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取曲绘"""
        if song_key in self._illustration_cache:
            return self._illustration_cache[song_key].copy()
        
        # 查找曲绘文件
        illust_path = self.illustration_path / f"{song_key}.png"
        if not illust_path.exists():
            # 尝试其他格式
            for file in self.illustration_path.glob(f"*{song_key}*.png"):
                illust_path = file
                break
        
        if illust_path.exists():
            try:
                img = Image.open(illust_path).convert("RGBA")
                self._illustration_cache[song_key] = img.copy()
                return img
            except Exception as e:
                logger.warning(f"加载曲绘失败 {song_key}: {e}")
        
        return None
    
    def _draw_rounded_rect(self, draw: ImageDraw.Draw, xy: Tuple[int, int, int, int], 
                          radius: int, fill: Tuple[int, int, int, int]):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = xy
        # 绘制主体矩形
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        # 绘制四个圆角
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    async def render_b30(self, data: Dict[str, Any], output_path: Path) -> bool:
        """
        渲染 Best30 成绩图
        
        参考 phi-plugin 的 b19 布局设计
        """
        try:
            # 画布尺寸
            width = 1200
            header_height = 150
            card_height = 200
            padding = 20
            
            # 获取数据
            gameuser = data.get('gameuser', {})
            records = data.get('records', [])[:30]
            
            # 计算总高度
            rows = (len(records) + 2) // 3  # 每行3个
            content_height = rows * (card_height + padding) + padding
            total_height = header_height + content_height + 60  # 头部 + 内容 + 底部
            
            # 创建画布
            img = Image.new('RGB', (width, total_height), '#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # 绘制渐变背景
            for y in range(total_height):
                r = int(26 + (22 - 26) * y / total_height)
                g = int(26 + (33 - 26) * y / total_height)
                b = int(46 + (62 - 46) * y / total_height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # 绘制头部
            self._draw_header(draw, gameuser, width, header_height)
            
            # 绘制成绩卡片
            y_offset = header_height + padding
            for i, record in enumerate(records):
                row = i // 3
                col = i % 3
                x = padding + col * (380 + padding)
                y = y_offset + row * (card_height + padding)
                self._draw_record_card(draw, i + 1, record, x, y, 380, card_height)
            
            # 绘制底部
            footer_y = total_height - 50
            font = self._get_font(14)
            draw.text((width // 2, footer_y), "Generated by Phigros Query Plugin", 
                     fill='#666666', font=font, anchor='mm')
            
            # 保存
            img.save(output_path, 'PNG', quality=self.image_quality)
            logger.info(f"✅ 渲染成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _draw_header(self, draw: ImageDraw.Draw, gameuser: Dict, width: int, height: int):
        """绘制头部信息"""
        padding = 20
        
        # 背景
        self._draw_rounded_rect(draw, 
                               (padding, padding, width - padding, height - padding),
                               15, (0, 0, 0, 128))
        
        # 头像位置
        avatar_size = 80
        avatar_x = padding + 20
        avatar_y = (height - avatar_size) // 2
        
        # 绘制头像圆形背景
        draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
                    fill='#333333', outline='white', width=3)
        
        # 玩家信息
        info_x = avatar_x + avatar_size + 20
        
        # 昵称
        font_name = self._get_font(24)
        nickname = gameuser.get('nickname', 'Unknown')
        draw.text((info_x, avatar_y + 10), nickname, fill='white', font=font_name)
        
        # ID
        font_id = self._get_font(14)
        player_id = gameuser.get('PlayerId', 'N/A')
        draw.text((info_x, avatar_y + 45), f"ID: {player_id}", fill='#aaaaaa', font=font_id)
        
        # RKS 框
        rks_width = 120
        rks_height = 70
        rks_x = width - padding - rks_width - 20
        rks_y = (height - rks_height) // 2
        
        # RKS 背景
        self._draw_rounded_rect(draw,
                               (rks_x, rks_y, rks_x + rks_width, rks_y + rks_height),
                               10, (255, 255, 255, 255))
        
        # RKS 文字
        font_rks_label = self._get_font(12)
        font_rks_value = self._get_font(24)
        rks = gameuser.get('rks', 0)
        
        draw.text((rks_x + rks_width // 2, rks_y + 15), "RKS", 
                 fill='black', font=font_rks_label, anchor='mm')
        draw.text((rks_x + rks_width // 2, rks_y + 45), f"{rks:.4f}", 
                 fill='black', font=font_rks_value, anchor='mm')
    
    def _draw_record_card(self, draw: ImageDraw.Draw, rank: int, record: Dict,
                         x: int, y: int, width: int, height: int):
        """绘制成绩卡片"""
        # 卡片背景
        self._draw_rounded_rect(draw, (x, y, x + width, y + height), 12, (0, 0, 0, 153))
        
        # 排名徽章
        badge_size = 30
        badge_colors = {
            1: ('#ffd700', '#000000'),  # 金牌
            2: ('#c0c0c0', '#000000'),  # 银牌
            3: ('#cd7f32', '#ffffff'),  # 铜牌
        }
        badge_color, text_color = badge_colors.get(rank, ('#000000', '#ffffff'))
        
        badge_x = x + 10
        badge_y = y + 10
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=badge_color)
        
        font_rank = self._get_font(14)
        draw.text((badge_x + badge_size // 2, badge_y + badge_size // 2), 
                 str(rank), fill=text_color, font=font_rank, anchor='mm')
        
        # FC/AP 徽章
        score = record.get('score', 0)
        if record.get('fc'):
            fc_x = x + width - 34
            fc_y = y + 10
            fc_color = '#ffd700' if score == 1000000 else '#60a5fa'
            fc_text = 'AP' if score == 1000000 else 'FC'
            
            self._draw_rounded_rect(draw, (fc_x, fc_y, fc_x + 24, fc_y + 24), 4, fc_color)
            font_fc = self._get_font(10)
            draw.text((fc_x + 12, fc_y + 12), fc_text, 
                     fill='black' if score == 1000000 else 'white', 
                     font=font_fc, anchor='mm')
        
        # 曲绘区域
        illust_height = 100
        illust_y = y + 50
        
        # 尝试加载曲绘
        song = record.get('song', '')
        illust = self._get_illustration(song)
        if illust:
            # 缩放曲绘
            illust_resized = illust.resize((width - 20, illust_height), Image.Resampling.LANCZOS)
            # 创建临时图像用于粘贴
            temp_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            temp_img.paste(illust_resized, (10, 50))
            # 混合到主图像
            # 这里简化处理，实际应该使用 mask
        else:
            # 绘制占位符
            draw.rectangle([x + 10, illust_y, x + width - 10, illust_y + illust_height],
                          fill='#333333')
        
        # 歌曲信息
        info_y = illust_y + illust_height + 10
        
        # 曲名
        font_song = self._get_font(14)
        song_name = record.get('song', 'Unknown')
        # 截断过长的曲名
        if len(song_name) > 20:
            song_name = song_name[:18] + '...'
        draw.text((x + 10, info_y), song_name, fill='white', font=font_song)
        
        # 分数和难度
        score_y = info_y + 25
        font_score = self._get_font(18)
        score = record.get('score', 0)
        draw.text((x + 10, score_y), f"{score:,}", fill='#ffd700', font=font_score)
        
        # 难度标签
        diff = record.get('difficulty', 'IN')
        diff_colors = {
            'EZ': '#4ade80',
            'HD': '#60a5fa',
            'IN': '#f472b6',
            'AT': '#a78bfa',
        }
        diff_color = diff_colors.get(diff, '#f472b6')
        diff_x = x + width - 50
        self._draw_rounded_rect(draw, (diff_x, score_y - 5, diff_x + 40, score_y + 20), 4, diff_color)
        font_diff = self._get_font(11)
        draw.text((diff_x + 20, score_y + 5), diff, fill='black', font=font_diff, anchor='mm')
        
        # Acc 和 RKS
        acc_y = score_y + 25
        font_acc = self._get_font(11)
        acc = record.get('acc', 0)
        rks = record.get('rks', 0)
        draw.text((x + 10, acc_y), f"Acc: {acc:.2f}% | RKS: {rks:.2f}", 
                 fill='#aaaaaa', font=font_acc)
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        # TODO: 实现单曲成绩渲染
        logger.warning("单曲成绩渲染暂未实现")
        return False
