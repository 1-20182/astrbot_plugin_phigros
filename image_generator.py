"""
🐱 喵喵图片生成器模块喵！

为 Phigros 插件提供统一的图片生成功能喵～
支持文本、数据、表格、排行榜等多种格式喵！
"""

import os
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from astrbot.api import logger


class ImageGenerator:
    """喵喵图片生成器喵～
    
    专门为 Phigros 插件生成漂亮图片的喵！
    会画画、会排版、还会调颜色喵～
    """
    
    def __init__(self, data_dir: Path, illustration_path: str = "./ILLUSTRATION"):
        self.data_dir = data_dir
        self.illustration_path = data_dir / illustration_path.replace("./", "")
        self.output_dir = data_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # 喵喵的字体缓存喵～
        self.font_cache = {}
        self._load_fonts()
        
        # 喵喵的调色板喵～
        self.colors = {
            'background': (30, 30, 50),
            'card': (0, 0, 0, 180),
            'text_primary': (255, 255, 255),
            'text_secondary': (200, 200, 200),
            'accent': (255, 215, 0),
            'success': (76, 175, 80),
            'warning': (255, 152, 0),
            'error': (244, 67, 54)
        }
    
    def _load_fonts(self):
        """加载字体喵～要找到最好看的字体给主人用喵！"""
        try:
            # 喵喵要找到最好看的字体喵～
            font_paths = [
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Ubuntu喵
                "/System/Library/Fonts/PingFang.ttc",  # macOS喵
                "C:/Windows/Fonts/msyh.ttc",  # Windows喵
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self.default_font = font_path
                    break
            else:
                # 喵喵找不到好看的字体，只能用默认的喵～
                self.default_font = None
                
        except Exception as e:
            logger.warning(f"�������ʧ��: {e}")
            self.default_font = None
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取指定大小的字体喵～要好好写字给主人看喵！"""
        try:
            if self.default_font:
                return ImageFont.truetype(self.default_font, size)
            else:
                return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def _create_gradient_background(self, size: Tuple[int, int], 
                                   color1: Tuple[int, int, int], 
                                   color2: Tuple[int, int, int]) -> Image.Image:
        """创建漂亮的渐变背景喵～像彩虹一样美丽喵！"""
        img = Image.new("RGB", size)
        draw = ImageDraw.Draw(img)
        
        for y in range(size[1]):
            ratio = y / size[1]
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))
        
        return img
    
    def _create_rounded_rectangle(self, size: Tuple[int, int], 
                                 radius: int, color: Tuple[int, ...]) -> Image.Image:
        """创建圆角矩形喵～圆圆的角角最可爱了喵！"""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 喵喵要画一个圆圆的矩形喵～
        draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=color)
        
        return img
    
    def _draw_text_with_shadow(self, draw: ImageDraw.Draw, text: str, 
                              pos: Tuple[int, int], font_size: int, 
                              color: Tuple[int, ...] = None,
                              shadow_offset: int = 2):
        """绘制带阴影的文字喵～要有立体感才好看喵！"""
        if color is None:
            color = self.colors['text_primary']
        
        font = self._get_font(font_size)
        x, y = pos
        
        # 喵喵先画阴影喵～
        shadow_color = (0, 0, 0, 128)
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
        
        # 然后再画文字喵～
        draw.text((x, y), text, font=font, fill=color)
    
    def generate_text_image(self, title: str, content: str, 
                           width: int = 800, max_height: int = 1200) -> Path:
        """生成文本图片喵～要把文字变成漂亮的图片给主人看喵！"""
        # 喵喵要计算图片需要多高喵～
        font_title = self._get_font(32)
        font_content = self._get_font(18)
        
        # 计算文本高度喵～
        lines = content.split('\n')
        line_height = 30
        content_height = len(lines) * line_height + 100  # 标题和边距喵
        
        height = min(max_height, max(400, content_height))
        
        # 喵喵要开始画画了喵～
        bg = self._create_gradient_background(
            (width, height), 
            self.colors['background'], 
            (60, 60, 80)
        )
        draw = ImageDraw.Draw(bg)
        
        # 标题栏喵～
        title_bar = self._create_rounded_rectangle((width - 40, 60), 15, self.colors['card'])
        bg.paste(title_bar, (20, 20), title_bar)
        
        # 绘制标题喵～
        self._draw_text_with_shadow(draw, title, (40, 35), 32, self.colors['accent'])
        
        # 绘制内容喵～
        y_offset = 100
        for line in lines:
            if y_offset + line_height < height - 40:
                self._draw_text_with_shadow(draw, line, (40, y_offset), 18)
                y_offset += line_height
            else:
                # 内容超出，添加省略号喵～
                self._draw_text_with_shadow(draw, "...", (40, y_offset), 18)
                break
        
        # 保存图片喵～
        output_path = self.output_dir / f"text_{hash(content) % 10000}.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def generate_table_image(self, title: str, headers: List[str], 
                            rows: List[List[str]], 
                            width: int = 1000, max_height: int = 1500) -> Path:
        """生成表格图片喵～要把数据排得整整齐齐的喵！"""
        # 计算表格尺寸喵～
        row_height = 40
        header_height = 50
        margin = 20
        
        table_height = header_height + len(rows) * row_height + margin * 2
        height = min(max_height, table_height + 100)
        
        # 创建背景喵～
        bg = self._create_gradient_background(
            (width, height), 
            self.colors['background'], 
            (60, 60, 80)
        )
        draw = ImageDraw.Draw(bg)
        
        # 标题喵～
        self._draw_text_with_shadow(draw, title, (margin, margin), 28, self.colors['accent'])
        
        # 表格区域喵～
        table_y = margin + 50
        table_width = width - margin * 2
        
        # 表头喵～
        header_bg = self._create_rounded_rectangle((table_width, header_height), 10, (0, 0, 0, 200))
        bg.paste(header_bg, (margin, table_y), header_bg)
        
        # 绘制表头喵～
        col_width = table_width // len(headers)
        for i, header in enumerate(headers):
            x = margin + i * col_width + 10
            self._draw_text_with_shadow(draw, header, (x, table_y + 15), 20, self.colors['accent'])
        
        # 绘制表格行喵～
        for row_idx, row in enumerate(rows):
            y = table_y + header_height + row_idx * row_height
            
            # 行背景（交替颜色喵～）
            row_color = (0, 0, 0, 150) if row_idx % 2 == 0 else (0, 0, 0, 100)
            row_bg = self._create_rounded_rectangle((table_width, row_height), 5, row_color)
            bg.paste(row_bg, (margin, y), row_bg)
            
            # 绘制单元格内容喵～
            for col_idx, cell in enumerate(row):
                x = margin + col_idx * col_width + 10
                self._draw_text_with_shadow(draw, str(cell), (x, y + 10), 16)
        
        # 保存图片喵～
        output_path = self.output_dir / f"table_{hash(str(rows)) % 10000}.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def generate_help_image(self, commands: List[Dict[str, str]]) -> Path:
        """生成帮助图片喵～要让主人知道怎么用插件喵！"""
        width, height = 900, 1200
        
        # 创建背景喵～
        bg = self._create_gradient_background(
            (width, height), 
            (40, 40, 60), 
            (80, 80, 100)
        )
        draw = ImageDraw.Draw(bg)
        
        # 标题喵～
        self._draw_text_with_shadow(draw, "🎮 Phigros 插件帮助", (50, 40), 36, self.colors['accent'])
        
        # 命令列表喵～
        y_offset = 100
        for cmd in commands:
            # 命令名称喵～
            self._draw_text_with_shadow(draw, f"/{cmd['name']}", (50, y_offset), 24, self.colors['success'])
            
            # 命令描述喵～
            desc_lines = self._wrap_text(cmd['description'], 24, width - 100)
            for line in desc_lines:
                self._draw_text_with_shadow(draw, line, (200, y_offset), 20)
                y_offset += 30
            
            # 示例喵～
            if 'example' in cmd:
                self._draw_text_with_shadow(draw, f"示例: {cmd['example']}", (250, y_offset), 18, self.colors['text_secondary'])
                y_offset += 25
            
            y_offset += 20
        
        # 保存图片喵～
        output_path = self.output_dir / "help.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def _wrap_text(self, text: str, font_size: int, max_width: int) -> List[str]:
        """文本换行喵～要让文字排得整整齐齐的喵！"""
        font = self._get_font(font_size)
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


def generate_text_image(title: str, content: str, data_dir: Path, **kwargs) -> Path:
    """生成文本图片的便捷函数喵～让主人用起来更方便喵！"""
    generator = ImageGenerator(data_dir)
    return generator.generate_text_image(title, content, **kwargs)

def generate_table_image(title: str, headers: List[str], rows: List[List[str]], 
                        data_dir: Path, **kwargs) -> Path:
    """生成表格图片的便捷函数喵～表格也要美美的喵！"""
    generator = ImageGenerator(data_dir)
    return generator.generate_table_image(title, headers, rows, **kwargs)

def generate_help_image(commands: List[Dict[str, str]], data_dir: Path) -> Path:
    """生成帮助图片的便捷函数喵～帮助主人了解插件喵！"""
    generator = ImageGenerator(data_dir)
    return generator.generate_help_image(commands)