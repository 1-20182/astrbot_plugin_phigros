"""
?? ͳһͼƬ������ģ??

??Phigros ����ṩͳһ��ͼƬ���ɹ�??
֧���ı������ݡ��������а�ȶ��ָ�??
"""

import os
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from astrbot.api import logger


class ImageGenerator:
    """ͳһͼƬ����??""
    
    def __init__(self, data_dir: Path, illustration_path: str = "./ILLUSTRATION"):
        self.data_dir = data_dir
        self.illustration_path = data_dir / illustration_path.replace("./", "")
        self.output_dir = data_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # ��������
        self.font_cache = {}
        self._load_fonts()
        
        # ��ɫ����
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
        """��������"""
        try:
            # ���Լ���ϵͳ����
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
                # ʹ��Ĭ������
                self.default_font = None
                
        except Exception as e:
            logger.warning(f"加载字体失败: {e}")
            self.default_font = None
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """��ȡ����"""
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
        """�������䱳��"""
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
        """����Բ�Ǿ���"""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # ����Բ�Ǿ���
        draw.rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=color)
        
        return img
    
    def _draw_text_with_shadow(self, draw: ImageDraw.Draw, text: str, 
                              pos: Tuple[int, int], font_size: int, 
                              color: Tuple[int, ...] = None,
                              shadow_offset: int = 2):
        """���ƴ���Ӱ������"""
        if color is None:
            color = self.colors['text_primary']
        
        font = self._get_font(font_size)
        x, y = pos
        
        # ��Ӱ
        shadow_color = (0, 0, 0, 128)
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
        
        # ����
        draw.text((x, y), text, font=font, fill=color)
    
    def generate_text_image(self, title: str, content: str, 
                           width: int = 800, max_height: int = 1200) -> Path:
        """�����ı�ͼƬ"""
        # ��������߶�
        font_title = self._get_font(32)
        font_content = self._get_font(18)
        
        # �����ı��߶�
        lines = content.split('\n')
        line_height = 30
        content_height = len(lines) * line_height + 100  # ����ͱ�??
        
        height = min(max_height, max(400, content_height))
        
        # ��������
        bg = self._create_gradient_background(
            (width, height), 
            self.colors['background'], 
            (60, 60, 80)
        )
        draw = ImageDraw.Draw(bg)
        
        # ����??
        title_bar = self._create_rounded_rectangle((width - 40, 60), 15, self.colors['card'])
        bg.paste(title_bar, (20, 20), title_bar)
        
        # ���Ʊ���
        self._draw_text_with_shadow(draw, title, (40, 35), 32, self.colors['accent'])
        
        # ��������
        y_offset = 100
        for line in lines:
            if y_offset + line_height < height - 40:
                self._draw_text_with_shadow(draw, line, (40, y_offset), 18)
                y_offset += line_height
            else:
                # ���ݳ���������ʡ�Ժ�
                self._draw_text_with_shadow(draw, "...", (40, y_offset), 18)
                break
        
        # ����ͼƬ
        output_path = self.output_dir / f"text_{hash(content) % 10000}.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def generate_table_image(self, title: str, headers: List[str], 
                            rows: List[List[str]], 
                            width: int = 1000, max_height: int = 1500) -> Path:
        """���ɱ���ͼƬ"""
        # �������ߴ�
        row_height = 40
        header_height = 50
        margin = 20
        
        table_height = header_height + len(rows) * row_height + margin * 2
        height = min(max_height, table_height + 100)
        
        # ��������
        bg = self._create_gradient_background(
            (width, height), 
            self.colors['background'], 
            (60, 60, 80)
        )
        draw = ImageDraw.Draw(bg)
        
        # ����
        self._draw_text_with_shadow(draw, title, (margin, margin), 28, self.colors['accent'])
        
        # ��������
        table_y = margin + 50
        table_width = width - margin * 2
        
        # ��ͷ
        header_bg = self._create_rounded_rectangle((table_width, header_height), 10, (0, 0, 0, 200))
        bg.paste(header_bg, (margin, table_y), header_bg)
        
        # ���Ʊ�ͷ
        col_width = table_width // len(headers)
        for i, header in enumerate(headers):
            x = margin + i * col_width + 10
            self._draw_text_with_shadow(draw, header, (x, table_y + 15), 20, self.colors['accent'])
        
        # ���Ʊ���??
        for row_idx, row in enumerate(rows):
            y = table_y + header_height + row_idx * row_height
            
            # �б�����������ɫ??
            row_color = (0, 0, 0, 150) if row_idx % 2 == 0 else (0, 0, 0, 100)
            row_bg = self._create_rounded_rectangle((table_width, row_height), 5, row_color)
            bg.paste(row_bg, (margin, y), row_bg)
            
            # ���Ƶ�Ԫ����??
            for col_idx, cell in enumerate(row):
                x = margin + col_idx * col_width + 10
                self._draw_text_with_shadow(draw, str(cell), (x, y + 10), 16)
        
        # ����ͼƬ
        output_path = self.output_dir / f"table_{hash(str(rows)) % 10000}.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def generate_help_image(self, commands: List[Dict[str, str]]) -> Path:
        """���ɰ���ͼƬ"""
        width, height = 900, 1200
        
        # ��������
        bg = self._create_gradient_background(
            (width, height), 
            (40, 40, 60), 
            (80, 80, 100)
        )
        draw = ImageDraw.Draw(bg)
        
        # ����
        self._draw_text_with_shadow(draw, "?? Phigros �������", (50, 40), 36, self.colors['accent'])
        
        # �����б�
        y_offset = 100
        for cmd in commands:
            # ��������
            self._draw_text_with_shadow(draw, f"/{cmd['name']}", (50, y_offset), 24, self.colors['success'])
            
            # ��������
            desc_lines = self._wrap_text(cmd['description'], 24, width - 100)
            for line in desc_lines:
                self._draw_text_with_shadow(draw, line, (200, y_offset), 20)
                y_offset += 30
            
            # ʾ��
            if 'example' in cmd:
                self._draw_text_with_shadow(draw, f"示例: {cmd['example']}", (250, y_offset), 18, self.colors['text_secondary'])
                y_offset += 25
            
            y_offset += 20
        
        # ����ͼƬ
        output_path = self.output_dir / "help.png"
        bg.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def _wrap_text(self, text: str, font_size: int, max_width: int) -> List[str]:
        """�ı�����"""
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
    """�����ı�ͼƬ�ı�ݺ�??""
    generator = ImageGenerator(data_dir)
    return generator.generate_text_image(title, content, **kwargs)

def generate_table_image(title: str, headers: List[str], rows: List[List[str]], 
                        data_dir: Path, **kwargs) -> Path:
    """���ɱ���ͼƬ�ı�ݺ�??""
    generator = ImageGenerator(data_dir)
    return generator.generate_table_image(title, headers, rows, **kwargs)

def generate_help_image(commands: List[Dict[str, str]], data_dir: Path) -> Path:
    """���ɰ���ͼƬ�ı�ݺ���"""
    generator = ImageGenerator(data_dir)
    return generator.generate_help_image(commands)