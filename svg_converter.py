"""
🎨 SVG 转 PNG 转换器 - 纯 Python 实现

> "你的 SVG 图片，我来搞定！" ✨

支持跨平台（Windows/Linux/Mac），无需外部依赖
还能自动加载本地曲绘，超方便的！
"""

import io
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from xml.etree import ElementTree as ET
from astrbot.api import logger

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class SVGConverter:
    """
    🎨 SVG 转换器 - 纯 Python 实现
    
    支持 cairosvg → Inkscape → Pillow 三级回退
    还能自动加载本地曲绘和背景图，超贴心的！
    """

    # SVG 命名空间
    SVG_NS = "http://www.w3.org/2000/svg"

    def __init__(self, illustration_path: Optional[str] = None, plugin_dir: Optional[str] = None):
        self.cairosvg_available = False
        self.inkscape_available = False
        self._check_availability()

        # 曲绘路径
        self.illustration_path = Path(illustration_path) if illustration_path else None
        self._illustration_map: Dict[str, str] = {}
        self._illustration_cache: Dict[str, Image.Image] = {}
        self._build_illustration_map()

        # 插件目录（用于查找默认背景）
        if plugin_dir:
            self.plugin_dir = Path(plugin_dir)
        else:
            # 尝试多个可能的路径
            possible_paths = [
                Path(__file__).parent,
                Path.cwd() / "data" / "plugins" / "astrbot_plugin_phigros",
                Path.cwd(),
            ]
            self.plugin_dir = Path(__file__).parent
            for path in possible_paths:
                bg_path = path / "default_wallpaper.jpg"
                if bg_path.exists():
                    self.plugin_dir = path
                    logger.info(f"找到背景图路径: {path}")
                    break

        logger.info(f"插件目录设置为: {self.plugin_dir}")

        # 加载默认背景
        self._default_background: Optional[Image.Image] = None
        self._load_default_background()

        # 字体缓存
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
        self._load_fonts()
    
    def _check_availability(self):
        """检查可用的转换工具"""
        # 检查 cairosvg (需要实际测试是否能正常工作)
        try:
            import cairosvg
            # 实际测试 cairosvg 是否能正常工作（cairo 库是否可用）
            import io
            test_svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
            cairosvg.svg2png(bytestring=test_svg, output_width=10, output_height=10)
            self.cairosvg_available = True
            logger.info("SVG 转换: cairosvg 可用")
        except ImportError:
            logger.debug("SVG 转换: cairosvg 未安装")
        except Exception as e:
            logger.debug(f"SVG 转换: cairosvg 已安装但无法使用 ({e})")
        
        # 检查 Inkscape
        try:
            result = subprocess.run(
                ["inkscape", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.inkscape_available = True
                logger.info("SVG 转换: Inkscape 可用")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            logger.debug("SVG 转换: Inkscape 未找到")

    def _build_illustration_map(self):
        """构建曲绘文件名映射"""
        if not self.illustration_path or not self.illustration_path.exists():
            return

        for file in self.illustration_path.glob("*.png"):
            name = file.stem
            # 存储完整文件名（小写）
            self._illustration_map[name.lower()] = str(file)
            # 同时存储简化版本（只取曲名部分）
            if "." in name:
                song_name = name.split(".")[0].lower()
                self._illustration_map[song_name] = str(file)

        logger.info(f"SVG 转换: 加载了 {len(self._illustration_map)} 个曲绘映射")

    def _load_default_background(self):
        """加载默认背景图片"""
        bg_path = self.plugin_dir / "default_wallpaper.jpg"
        logger.info(f"SVG 转换: 查找默认背景 {bg_path}")
        if bg_path.exists():
            try:
                self._default_background = Image.open(bg_path).convert("RGBA")
                logger.info(f"SVG 转换: 已加载默认背景 {bg_path.name}, 尺寸: {self._default_background.size}")
            except Exception as e:
                logger.warning(f"加载默认背景失败: {e}")
        else:
            logger.warning(f"SVG 转换: 未找到默认背景 {bg_path}")

    def _load_fonts(self):
        """加载字体"""
        # 尝试加载插件目录下的字体
        font_paths = [
            self.plugin_dir / "resources" / "font.ttf",
            self.plugin_dir / "resources" / "font.otf",
            self.plugin_dir / "font.ttf",
            self.plugin_dir / "font.otf",
        ]

        # 系统字体路径（跨平台支持）
        system_fonts = [
            # Windows 字体
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/msgothic.ttc",  # MS Gothic (日文)
            "C:/Windows/Fonts/malgun.ttf",  # 韩语
            # Linux 字体（Ubuntu/Debian/CentOS）
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # 文泉驿正黑
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto CJK
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # DejaVu
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Liberation
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",  # FreeFont
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",  # Ubuntu
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",  # CentOS/RHEL
            "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/arphic/uming.ttc",  # 文鼎 UMing
            "/usr/share/fonts/truetype/arphic/ukai.ttc",  # 文鼎 UKai
            # macOS 字体
            "/System/Library/Fonts/PingFang.ttc",  # 苹方
            "/System/Library/Fonts/STHeiti Light.ttc",  # 黑体
            "/System/Library/Fonts/Hiragino Sans GB.ttc",  # 冬青黑体
            "/Library/Fonts/Arial Unicode.ttf",
        ]

        self._font_paths = []

        # 检查插件目录字体
        for font_path in font_paths:
            if font_path.exists():
                self._font_paths.append(str(font_path))
                logger.info(f"SVG 转换: 找到插件字体 {font_path.name}")

        # 检查系统字体
        for font_path in system_fonts:
            if Path(font_path).exists():
                self._font_paths.append(font_path)
                logger.info(f"SVG 转换: 找到系统字体 {Path(font_path).name}")

        if not self._font_paths:
            logger.warning("SVG 转换: 未找到任何字体，将使用默认字体")
        else:
            logger.info(f"SVG 转换: 共找到 {len(self._font_paths)} 个字体")

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取指定大小的字体"""
        if size in self._font_cache:
            return self._font_cache[size]

        # 尝试加载可用字体
        for font_path in self._font_paths:
            try:
                font = ImageFont.truetype(font_path, size)
                self._font_cache[size] = font
                return font
            except:
                continue

        # 使用默认字体
        font = ImageFont.load_default()
        self._font_cache[size] = font
        return font

    def _get_illustration(self, song_key: str) -> Optional[Image.Image]:
        """获取曲绘图片"""
        if not song_key:
            return None

        # 检查缓存
        if song_key in self._illustration_cache:
            return self._illustration_cache[song_key].copy()

        # 查找曲绘文件
        key_lower = song_key.lower()
        file_path = None

        if key_lower in self._illustration_map:
            file_path = self._illustration_map[key_lower]
        elif "." in key_lower:
            song_name = key_lower.split(".")[0]
            if song_name in self._illustration_map:
                file_path = self._illustration_map[song_name]

        if file_path and Path(file_path).exists():
            try:
                img = Image.open(file_path).convert("RGBA")
                self._illustration_cache[song_key] = img.copy()
                return img
            except Exception as e:
                logger.warning(f"加载曲绘失败 {file_path}: {e}")

        return None

    def _extract_song_key_from_url(self, url: str) -> Optional[str]:
        """从 URL 中提取歌曲 key"""
        # URL 格式: https://somnia.xtower.site/illustrationBlur/SpeedUp.DarTokki.png
        # 或: https://somnia.xtower.site/illustration/SpeedUp.DarTokki.png
        try:
            # 提取文件名部分
            filename = url.split("/")[-1]
            # 移除 .png 后缀
            if filename.endswith(".png"):
                filename = filename[:-4]
            # URL 解码（处理中文歌曲名）
            import urllib.parse
            filename = urllib.parse.unquote(filename)
            return filename
        except:
            return None

    def convert(self, svg_path: str, output_path: str, width: int = None, height: int = None) -> bool:
        """
        转换 SVG 为 PNG

        优先级:
        1. cairosvg (如果可用)
        2. Inkscape (如果可用)
        3. 纯 Python 实现 (Pillow)

        Args:
            svg_path: SVG 文件路径
            output_path: 输出 PNG 路径
            width: 输出宽度（可选）
            height: 输出高度（可选）

        Returns:
            bool: 转换是否成功
        """
        svg_path = Path(svg_path)
        output_path = Path(output_path)

        # 打印调试信息
        logger.info(f"SVG转换开始: plugin_dir={self.plugin_dir}, background={self._default_background is not None}")

        if not svg_path.exists():
            logger.error(f"SVG 文件不存在: {svg_path}")
            return False
        
        # 优先使用 cairosvg
        if self.cairosvg_available:
            result = self._convert_with_cairosvg(svg_path, output_path, width, height)
            if result:
                return True
            logger.warning("cairosvg 转换失败，尝试其他方式")
        
        # 尝试 Inkscape
        if self.inkscape_available:
            try:
                return self._convert_with_inkscape(svg_path, output_path, width, height)
            except Exception as e:
                logger.warning(f"Inkscape 转换失败: {e}")
        
        # 使用纯 Python 实现
        if PIL_AVAILABLE:
            try:
                return self._convert_with_pillow(svg_path, output_path, width, height)
            except Exception as e:
                logger.warning(f"Pillow 转换失败: {e}")
        
        logger.error("没有可用的 SVG 转换工具")
        return False
    
    def _convert_with_cairosvg(self, svg_path: Path, output_path: Path, width: int = None, height: int = None) -> bool:
        """使用 cairosvg 转换"""
        try:
            import cairosvg
            
            png_data = cairosvg.svg2png(
                url=str(svg_path),
                output_width=width,
                output_height=height
            )
            
            with open(output_path, 'wb') as f:
                f.write(png_data)
            
            logger.info(f"cairosvg 转换成功: {output_path}")
            return True
        except Exception as e:
            logger.warning(f"cairosvg 转换失败: {e}")
            return False
    
    def _convert_with_inkscape(self, svg_path: Path, output_path: Path, width: int = None, height: int = None) -> bool:
        """使用 Inkscape 转换"""
        cmd = [
            "inkscape",
            str(svg_path),
            "--export-filename", str(output_path),
            "--export-type=png"
        ]
        
        if width:
            cmd.extend(["--export-width", str(width)])
        if height:
            cmd.extend(["--export-height", str(height)])
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"Inkscape 错误: {result.stderr.decode()}")
        
        logger.info(f"Inkscape 转换成功: {output_path}")
        return True
    
    def _convert_with_pillow(self, svg_path: Path, output_path: Path, width: int = None, height: int = None) -> bool:
        """
        使用 Pillow 纯 Python 实现转换 SVG
        这是一个简化实现，支持基本的 SVG 元素
        
        针对 BestN SVG 优化：
        - BestN SVG 宽度固定 1200，高度动态计算
        - 默认 n=30 时常见高度为 1644
        """
        try:
            # 解析 SVG
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # 获取 SVG 尺寸
            svg_width, svg_height = self._get_svg_size(root)
            
            # 记录原始尺寸用于调试
            logger.info(f"📐 SVG 原始尺寸: {svg_width}x{svg_height}")
            
            # BestN SVG 特性：宽度固定 1200，高度动态
            # 如果检测到是 BestN 类型的 SVG（宽度接近 1200），进行优化
            is_bestn_svg = abs(svg_width - 1200) < 10
            if is_bestn_svg:
                logger.info(f"🎯 检测到 BestN SVG，宽度固定 {svg_width}")

            # 如果指定了输出尺寸，进行缩放
            if width and height:
                output_width, output_height = width, height
            elif width:
                # 保持宽高比缩放
                scale = width / svg_width
                output_width = width
                output_height = int(svg_height * scale)
            elif height:
                # 保持宽高比缩放
                scale = height / svg_height
                output_width = int(svg_width * scale)
                output_height = height
            else:
                # 默认输出尺寸：保持原始尺寸，但限制最大宽度为 2400（2倍缩放）
                # 这样既能保证清晰度，又不会生成过大的图片
                max_width = 2400
                if svg_width > max_width:
                    scale = max_width / svg_width
                    output_width = max_width
                    output_height = int(svg_height * scale)
                else:
                    output_width = int(svg_width)
                    output_height = int(svg_height)

            # 确保尺寸合理（限制最大 4096x4096，避免内存问题）
            max_output_size = 4096
            output_width = max(1, min(output_width, max_output_size))
            output_height = max(1, min(output_height, max_output_size))
            
            logger.info(f"📏 输出尺寸: {output_width}x{output_height} (缩放比: {output_width/svg_width:.2f})")

            # 强制尝试加载背景（如果还没有加载）
            if self._default_background is None:
                logger.info("背景未加载，强制尝试加载...")
                self._load_default_background()

            # 创建图像（使用默认背景）
            logger.info(f"背景状态: _default_background={self._default_background is not None}")
            if self._default_background is not None:
                logger.info("使用默认背景图")
                
                # 针对长图（如 BestN）优化背景处理
                # 计算宽高比
                output_ratio = output_height / output_width
                bg_ratio = self._default_background.height / self._default_background.width
                
                if output_ratio > bg_ratio * 1.5:
                    # 输出图比背景图更"长"，使用平铺或拉伸模式
                    logger.info(f"📐 检测到长图（比例 {output_ratio:.2f}），优化背景处理")
                    
                    # 方法：先缩放背景宽度匹配，然后垂直平铺或拉伸
                    bg_width = output_width
                    bg_height = int(bg_width * bg_ratio)
                    bg_scaled = self._default_background.resize((bg_width, bg_height), Image.Resampling.LANCZOS)
                    
                    # 创建目标尺寸的图像
                    img = Image.new('RGBA', (output_width, output_height))
                    
                    # 垂直平铺背景
                    y_offset = 0
                    while y_offset < output_height:
                        remaining_height = min(bg_height, output_height - y_offset)
                        if remaining_height < bg_height:
                            # 裁剪最后一行
                            bg_crop = bg_scaled.crop((0, 0, bg_width, remaining_height))
                            img.paste(bg_crop, (0, y_offset))
                        else:
                            img.paste(bg_scaled, (0, y_offset))
                        y_offset += bg_height
                else:
                    # 正常比例，直接缩放
                    bg_resized = self._default_background.resize((output_width, output_height), Image.Resampling.LANCZOS)
                    img = bg_resized.copy()

                # 添加半透明遮罩以提高文字可读性
                overlay = Image.new('RGBA', (output_width, output_height), (0, 0, 0, 160))
                img = Image.alpha_composite(img, overlay)
            else:
                logger.warning("背景图仍不可用，使用SVG背景色")
                # 尝试获取 SVG 背景色
                bg_color = root.get('background-color', '')
                if bg_color:
                    bg_rgba = self._get_color(bg_color, (20, 24, 38, 255))
                    img = Image.new('RGBA', (output_width, output_height), bg_rgba)
                else:
                    # 使用深色背景作为回退
                    img = Image.new('RGBA', (output_width, output_height), (20, 24, 38, 255))

            draw = ImageDraw.Draw(img)

            # 计算缩放比例
            scale_x = output_width / svg_width
            scale_y = output_height / svg_height

            # 渲染 SVG 元素，传递原始 SVG 尺寸用于计算百分比
            self._render_svg_element(root, draw, scale_x, scale_y, svg_width=svg_width, svg_height=svg_height)

            # 保存为 PNG
            img.save(output_path, 'PNG')
            logger.info(f"Pillow 转换成功: {output_path} ({output_width}x{output_height})")
            return True

        except Exception as e:
            logger.error(f"Pillow SVG 转换失败: {e}")
            import traceback
            logger.debug(f"转换失败详情: {traceback.format_exc()}")
            return False
    
    def _get_svg_size(self, root) -> Tuple[float, float]:
        """获取 SVG 尺寸"""
        width = root.get('width', '')
        height = root.get('height', '')
        
        # 解析 viewBox (优先使用)
        viewbox = root.get('viewBox')
        if viewbox:
            parts = viewbox.replace(',', ' ').split()
            if len(parts) >= 4:
                try:
                    vb_width = float(parts[2])
                    vb_height = float(parts[3])
                    if vb_width > 0 and vb_height > 0:
                        return vb_width, vb_height
                except ValueError:
                    pass
        
        # 解析 width/height
        w = self._parse_length(width) if width else 0
        h = self._parse_length(height) if height else 0
        
        # 如果解析失败，使用默认值
        if w <= 0:
            w = 800
        if h <= 0:
            h = 600
            
        return w, h
    
    def _parse_length(self, value: str) -> float:
        """解析长度值"""
        if not value:
            return 0
        # 移除单位
        value = value.strip().lower()
        
        # 处理百分比 - 返回 0 表示需要根据其他方式计算
        if value.endswith('%'):
            return 0
        
        # 移除其他单位
        for unit in ['px', 'pt', 'pc', 'cm', 'mm', 'in', 'em', 'ex']:
            if value.endswith(unit):
                value = value[:-len(unit)]
                break
        
        try:
            return float(value)
        except ValueError:
            return 0

    def _render_svg_element(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                           offset_x: float = 0, offset_y: float = 0, svg_width: float = 800, svg_height: float = 600):
        """渲染 SVG 元素"""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # 处理当前元素
        if tag == 'rect':
            self._draw_rect(element, draw, scale_x, scale_y, offset_x, offset_y, svg_width, svg_height)
        elif tag == 'circle':
            self._draw_circle(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'ellipse':
            self._draw_ellipse(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'line':
            self._draw_line(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'polyline':
            self._draw_polyline(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'polygon':
            self._draw_polygon(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'path':
            self._draw_path(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'text':
            self._draw_text(element, draw, scale_x, scale_y, offset_x, offset_y)
        elif tag == 'image':
            self._draw_image(element, draw, scale_x, scale_y, offset_x, offset_y, svg_width, svg_height)
        elif tag == 'g':
            # 处理组元素
            transform = element.get('transform', '')
            new_offset_x, new_offset_y = offset_x, offset_y

            # 简单解析 translate
            translate_match = re.search(r'translate\(([^,]+),?([^)]*)\)', transform)
            if translate_match:
                new_offset_x += float(translate_match.group(1)) * scale_x
                if translate_match.group(2):
                    new_offset_y += float(translate_match.group(2)) * scale_y

            for child in element:
                self._render_svg_element(child, draw, scale_x, scale_y, new_offset_x, new_offset_y, svg_width, svg_height)
            return
        elif tag in ['defs', 'style', 'linearGradient', 'filter', 'stop']:
            # 跳过这些元素（它们定义样式但不直接渲染）
            return

        # 递归处理子元素（对于没有特定处理的元素）
        for child in element:
            self._render_svg_element(child, draw, scale_x, scale_y, offset_x, offset_y, svg_width, svg_height)
    
    def _get_color(self, color_str: str, default: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> Tuple[int, int, int, int]:
        """解析颜色"""
        if not color_str or color_str == 'none':
            return default
        
        color_str = color_str.strip().lower()
        
        # 处理 rgb()
        rgb_match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
        if rgb_match:
            return (int(rgb_match.group(1)), int(rgb_match.group(2)), 
                   int(rgb_match.group(3)), 255)
        
        # 处理 rgba()
        rgba_match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', color_str)
        if rgba_match:
            return (int(rgba_match.group(1)), int(rgba_match.group(2)), 
                   int(rgba_match.group(3)), int(float(rgba_match.group(4)) * 255))
        
        # 处理十六进制
        if color_str.startswith('#'):
            color_str = color_str[1:]
            if len(color_str) == 3:
                r = int(color_str[0] * 2, 16)
                g = int(color_str[1] * 2, 16)
                b = int(color_str[2] * 2, 16)
                return (r, g, b, 255)
            elif len(color_str) == 6:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                return (r, g, b, 255)
        
        # 常见颜色名
        color_map = {
            'black': (0, 0, 0, 255),
            'white': (255, 255, 255, 255),
            'red': (255, 0, 0, 255),
            'green': (0, 128, 0, 255),
            'blue': (0, 0, 255, 255),
            'yellow': (255, 255, 0, 255),
            'cyan': (0, 255, 255, 255),
            'magenta': (255, 0, 255, 255),
            'silver': (192, 192, 192, 255),
            'gray': (128, 128, 128, 255),
            'grey': (128, 128, 128, 255),
            'maroon': (128, 0, 0, 255),
            'olive': (128, 128, 0, 255),
            'lime': (0, 255, 0, 255),
            'aqua': (0, 255, 255, 255),
            'teal': (0, 128, 128, 255),
            'navy': (0, 0, 128, 255),
            'fuchsia': (255, 0, 255, 255),
            'purple': (128, 0, 128, 255),
        }
        
        return color_map.get(color_str, default)
    
    def _draw_rect(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                   offset_x: float, offset_y: float, svg_width: float = 800, svg_height: float = 600):
        """绘制矩形"""
        x_str = element.get('x', '0')
        y_str = element.get('y', '0')
        width_str = element.get('width', '0')
        height_str = element.get('height', '0')

        # 解析 x, y
        try:
            x = self._parse_length(x_str) * scale_x + offset_x
        except:
            x = offset_x
        try:
            y = self._parse_length(y_str) * scale_y + offset_y
        except:
            y = offset_y

        # 解析 width，处理百分比
        try:
            if width_str.endswith('%'):
                width = svg_width * float(width_str[:-1]) / 100.0 * scale_x
            else:
                width = self._parse_length(width_str) * scale_x
        except:
            width = 0

        # 解析 height，处理百分比
        try:
            if height_str.endswith('%'):
                height = svg_height * float(height_str[:-1]) / 100.0 * scale_y
            else:
                height = self._parse_length(height_str) * scale_y
        except:
            height = 0

        # 如果 rect 是全屏背景（100% x 100%），跳过绘制以保留自定义背景
        is_fullscreen = (width_str == '100%' or width >= svg_width * scale_x - 1) and \
                       (height_str == '100%' or height >= svg_height * scale_y - 1)

        fill = self._get_color(element.get('fill', 'none'), None)
        stroke = self._get_color(element.get('stroke', 'none'), None)
        stroke_width = float(element.get('stroke-width', 1)) * min(scale_x, scale_y)

        rx = float(element.get('rx', 0)) * scale_x
        ry = float(element.get('ry', 0)) * scale_y

        # 跳过全屏背景矩形（保留自定义背景图）
        if is_fullscreen and fill and fill[3] > 200:  # 不透明的全屏矩形
            logger.debug(f"跳过全屏背景矩形: fill={fill}")
            return

        if fill:
            if rx > 0 or ry > 0:
                draw.rounded_rectangle([x, y, x + width, y + height],
                                      radius=max(rx, ry), fill=fill)
            else:
                draw.rectangle([x, y, x + width, y + height], fill=fill)
        
        if stroke and stroke_width > 0:
            draw.rectangle([x, y, x + width, y + height], outline=stroke, width=int(stroke_width))
    
    def _draw_circle(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                     offset_x: float, offset_y: float):
        """绘制圆形"""
        cx = float(element.get('cx', 0)) * scale_x + offset_x
        cy = float(element.get('cy', 0)) * scale_y + offset_y
        r = float(element.get('r', 0)) * min(scale_x, scale_y)
        
        fill = self._get_color(element.get('fill', 'none'), None)
        stroke = self._get_color(element.get('stroke', 'none'), None)
        stroke_width = float(element.get('stroke-width', 1)) * min(scale_x, scale_y)
        
        bbox = [cx - r, cy - r, cx + r, cy + r]
        
        if fill:
            draw.ellipse(bbox, fill=fill)
        if stroke and stroke_width > 0:
            draw.ellipse(bbox, outline=stroke, width=int(stroke_width))
    
    def _draw_ellipse(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                      offset_x: float, offset_y: float):
        """绘制椭圆"""
        cx = float(element.get('cx', 0)) * scale_x + offset_x
        cy = float(element.get('cy', 0)) * scale_y + offset_y
        rx = float(element.get('rx', 0)) * scale_x
        ry = float(element.get('ry', 0)) * scale_y
        
        fill = self._get_color(element.get('fill', 'none'), None)
        stroke = self._get_color(element.get('stroke', 'none'), None)
        stroke_width = float(element.get('stroke-width', 1)) * min(scale_x, scale_y)
        
        bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
        
        if fill:
            draw.ellipse(bbox, fill=fill)
        if stroke and stroke_width > 0:
            draw.ellipse(bbox, outline=stroke, width=int(stroke_width))
    
    def _draw_line(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                   offset_x: float, offset_y: float):
        """绘制直线"""
        x1 = float(element.get('x1', 0)) * scale_x + offset_x
        y1 = float(element.get('y1', 0)) * scale_y + offset_y
        x2 = float(element.get('x2', 0)) * scale_x + offset_x
        y2 = float(element.get('y2', 0)) * scale_y + offset_y
        
        stroke = self._get_color(element.get('stroke', 'black'))
        stroke_width = int(float(element.get('stroke-width', 1)) * min(scale_x, scale_y))
        
        draw.line([(x1, y1), (x2, y2)], fill=stroke, width=stroke_width)
    
    def _draw_polyline(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                       offset_x: float, offset_y: float):
        """绘制折线"""
        points_str = element.get('points', '')
        points = self._parse_points(points_str, scale_x, scale_y, offset_x, offset_y)
        
        if len(points) < 2:
            return
        
        stroke = self._get_color(element.get('stroke', 'black'))
        stroke_width = int(float(element.get('stroke-width', 1)) * min(scale_x, scale_y))
        
        draw.line(points, fill=stroke, width=stroke_width)
    
    def _draw_polygon(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                      offset_x: float, offset_y: float):
        """绘制多边形"""
        points_str = element.get('points', '')
        points = self._parse_points(points_str, scale_x, scale_y, offset_x, offset_y)
        
        if len(points) < 3:
            return
        
        fill = self._get_color(element.get('fill', 'none'), None)
        stroke = self._get_color(element.get('stroke', 'none'), None)
        stroke_width = int(float(element.get('stroke-width', 1)) * min(scale_x, scale_y))
        
        if fill:
            draw.polygon(points, fill=fill)
        if stroke and stroke_width > 0:
            draw.polygon(points, outline=stroke)
    
    def _parse_points(self, points_str: str, scale_x: float, scale_y: float,
                      offset_x: float, offset_y: float) -> List[Tuple[float, float]]:
        """解析点坐标"""
        points = []
        coords = points_str.replace(',', ' ').split()
        
        for i in range(0, len(coords) - 1, 2):
            try:
                x = float(coords[i]) * scale_x + offset_x
                y = float(coords[i + 1]) * scale_y + offset_y
                points.append((x, y))
            except (ValueError, IndexError):
                continue
        
        return points
    
    def _draw_path(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                   offset_x: float, offset_y: float):
        """绘制路径 - 简化实现"""
        d = element.get('d', '')
        if not d:
            return
        
        fill = self._get_color(element.get('fill', 'none'), None)
        stroke = self._get_color(element.get('stroke', 'none'), None)
        stroke_width = int(float(element.get('stroke-width', 1)) * min(scale_x, scale_y))
        
        # 简化的路径解析 - 只处理基本的 M 和 L 命令
        points = []
        current_x, current_y = 0, 0
        
        # 解析路径命令
        commands = re.findall(r'([MmLlHhVvCcSsQqTtAaZz])\s*([^MmLlHhVvCcSsQqTtAaZz]*)', d)
        
        for cmd, args_str in commands:
            args = [float(x) for x in re.findall(r'[-+]?[\d.]+', args_str)]
            
            if cmd == 'M' and len(args) >= 2:
                current_x, current_y = args[0] * scale_x + offset_x, args[1] * scale_y + offset_y
                if not points:
                    points.append((current_x, current_y))
            elif cmd == 'm' and len(args) >= 2:
                current_x += args[0] * scale_x
                current_y += args[1] * scale_y
                if not points:
                    points.append((current_x, current_y))
            elif cmd == 'L' and len(args) >= 2:
                current_x, current_y = args[0] * scale_x + offset_x, args[1] * scale_y + offset_y
                points.append((current_x, current_y))
            elif cmd == 'l' and len(args) >= 2:
                current_x += args[0] * scale_x
                current_y += args[1] * scale_y
                points.append((current_x, current_y))
            elif cmd == 'H' and len(args) >= 1:
                current_x = args[0] * scale_x + offset_x
                points.append((current_x, current_y))
            elif cmd == 'h' and len(args) >= 1:
                current_x += args[0] * scale_x
                points.append((current_x, current_y))
            elif cmd == 'V' and len(args) >= 1:
                current_y = args[0] * scale_y + offset_y
                points.append((current_x, current_y))
            elif cmd == 'v' and len(args) >= 1:
                current_y += args[0] * scale_y
                points.append((current_x, current_y))
            elif cmd in ['Z', 'z']:
                if len(points) > 2:
                    if fill:
                        draw.polygon(points, fill=fill)
                    if stroke and stroke_width > 0:
                        draw.polygon(points, outline=stroke)
                points = []
        
        # 绘制剩余的点
        if len(points) > 1:
            if fill and len(points) > 2:
                draw.polygon(points, fill=fill)
            if stroke and stroke_width > 0:
                draw.line(points, fill=stroke, width=stroke_width)
    
    def _draw_text(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                   offset_x: float, offset_y: float):
        """绘制文本 - 使用加载的字体"""
        x = float(element.get('x', 0)) * scale_x + offset_x
        y = float(element.get('y', 0)) * scale_y + offset_y

        # 获取文本内容
        text = ''
        for child in element:
            if child.tag.endswith('}tspan') or child.tag == 'tspan':
                if child.text:
                    text += child.text
            elif child.text:
                text += child.text

        if not text and element.text:
            text = element.text

        if not text:
            return

        fill = self._get_color(element.get('fill', 'white'))  # 默认白色
        font_size = int(float(element.get('font-size', '16').replace('px', '')) * min(scale_x, scale_y))
        font_size = max(8, min(font_size, 200))

        # 使用加载的字体
        font = self._get_font(font_size)

        # 绘制文字阴影（提高可读性）
        shadow_color = (0, 0, 0, 128)
        draw.text((x+1, y+1), text, fill=shadow_color, font=font)
        
        # 绘制主文字
        draw.text((x, y), text, fill=fill, font=font)
        
        logger.debug(f"绘制文字: '{text[:20]}...' at ({x}, {y}), size={font_size}, color={fill}")

    def _draw_image(self, element, draw: ImageDraw.Draw, scale_x: float, scale_y: float,
                    offset_x: float, offset_y: float, svg_width: float = 800, svg_height: float = 600):
        """绘制图片 - 使用本地曲绘"""
        # 获取 href 属性（可能是 href 或 xlink:href）
        href = element.get('href', '') or element.get('{http://www.w3.org/1999/xlink}href', '')
        if not href:
            return

        # 解析位置和尺寸
        x_str = element.get('x', '0')
        y_str = element.get('y', '0')
        width_str = element.get('width', '0')
        height_str = element.get('height', '0')

        try:
            x = self._parse_length(x_str) * scale_x + offset_x
        except:
            x = offset_x
        try:
            y = self._parse_length(y_str) * scale_y + offset_y
        except:
            y = offset_y

        # 解析 width，处理百分比
        try:
            if width_str.endswith('%'):
                width = svg_width * float(width_str[:-1]) / 100.0 * scale_x
            else:
                width = self._parse_length(width_str) * scale_x
        except:
            width = 0

        # 解析 height，处理百分比
        try:
            if height_str.endswith('%'):
                height = svg_height * float(height_str[:-1]) / 100.0 * scale_y
            else:
                height = self._parse_length(height_str) * scale_y
        except:
            height = 0

        if width <= 0 or height <= 0:
            return

        # 从 URL 提取歌曲 key
        song_key = self._extract_song_key_from_url(href)
        logger.info(f"尝试加载曲绘: {song_key} (from {href})")
        if not song_key:
            logger.warning(f"无法从 URL 提取歌曲 key: {href}")
            return

        # 加载本地曲绘
        illust = self._get_illustration(song_key)
        if not illust:
            logger.warning(f"未找到本地曲绘: {song_key}")
            return
        
        logger.info(f"找到曲绘: {song_key}, 尺寸: {illust.size}")

        # 调整图片大小
        try:
            # 获取 preserveAspectRatio 属性
            preserve_ratio = element.get('preserveAspectRatio', '')

            # 计算缩放和裁剪
            img_width, img_height = illust.size
            target_width = int(width)
            target_height = int(height)

            if 'slice' in preserve_ratio:
                # slice 模式：填充整个区域，可能裁剪
                img_ratio = img_width / img_height
                target_ratio = target_width / target_height

                if img_ratio > target_ratio:
                    # 图片更宽，按高度缩放，裁剪宽度
                    new_height = target_height
                    new_width = int(img_width * (target_height / img_height))
                    resized = illust.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # 居中裁剪
                    left = (new_width - target_width) // 2
                    resized = resized.crop((left, 0, left + target_width, target_height))
                else:
                    # 图片更高，按宽度缩放，裁剪高度
                    new_width = target_width
                    new_height = int(img_height * (target_width / img_width))
                    resized = illust.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # 居中裁剪
                    top = (new_height - target_height) // 2
                    resized = resized.crop((0, top, target_width, top + target_height))
            else:
                # 默认模式：适应区域，保持完整
                resized = illust.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # 获取父图像
            parent_img = draw._image

            # 粘贴曲绘（使用 alpha 通道）
            if resized.mode == 'RGBA':
                parent_img.paste(resized, (int(x), int(y)), resized)
            else:
                parent_img.paste(resized, (int(x), int(y)))

            logger.debug(f"绘制曲绘成功: {song_key} ({width}x{height})")
        except Exception as e:
            logger.warning(f"绘制曲绘失败 {song_key}: {e}")

    def get_available_converters(self) -> list:
        """获取可用的转换器列表"""
        converters = []
        if self.cairosvg_available:
            converters.append("cairosvg")
        if self.inkscape_available:
            converters.append("inkscape")
        if PIL_AVAILABLE:
            converters.append("pillow (纯Python)")
        return converters
    
    def install_help(self) -> str:
        """获取安装帮助信息"""
        help_text = []
        
        if not self.cairosvg_available and not self.inkscape_available:
            help_text.append("SVG 转换工具未安装，可选方案：")
            help_text.append("")
            help_text.append("方案 1 - cairosvg (推荐，Windows需要GTK+)：")
            help_text.append("  1. 下载 GTK+ 运行时：https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
            help_text.append("  2. 安装后重启 AstrBot")
            help_text.append("  3. pip install cairosvg")
            help_text.append("")
            help_text.append("方案 2 - Inkscape：")
            help_text.append("  1. 下载安装：https://inkscape.org/release/")
            help_text.append("  2. 确保 inkscape 命令在系统 PATH 中")
            help_text.append("")
            help_text.append("方案 3 - 纯 Python (Pillow)：")
            help_text.append("  插件将自动使用 Pillow 进行基础 SVG 渲染")
            help_text.append("  注：仅支持基本 SVG 元素")
        
        return "\n".join(help_text)


# 全局转换器实例
_converter: Optional[SVGConverter] = None


def get_converter(illustration_path: Optional[str] = None, plugin_dir: Optional[str] = None) -> SVGConverter:
    """获取 SVG 转换器实例

    Args:
        illustration_path: 曲绘文件夹路径（可选）
        plugin_dir: 插件目录路径（可选，用于加载默认背景和字体）
    """
    global _converter
    if _converter is None:
        logger.info("创建新的 SVGConverter 实例")
        _converter = SVGConverter(illustration_path=illustration_path, plugin_dir=plugin_dir)
    else:
        logger.info(f"使用现有 SVGConverter 实例: plugin_dir={_converter.plugin_dir}, has_bg={_converter._default_background is not None}")
        # 更新路径（如果提供了新路径）
        if plugin_dir:
            new_plugin_dir = Path(plugin_dir)
            if _converter.plugin_dir != new_plugin_dir:
                logger.info(f"更新插件目录: {new_plugin_dir}")
                _converter.plugin_dir = new_plugin_dir
                _converter._load_default_background()
                _converter._load_fonts()
            elif not _converter._default_background:
                logger.info("背景未加载，尝试重新加载")
                _converter._load_default_background()
                _converter._load_fonts()
        if illustration_path:
            new_illust_path = Path(illustration_path)
            if _converter.illustration_path != new_illust_path or not _converter._illustration_map:
                logger.info(f"更新曲绘目录: {new_illust_path}")
                _converter.illustration_path = new_illust_path
                _converter._build_illustration_map()
    return _converter


def convert_svg_to_png(svg_path: str, output_path: str, width: int = None, height: int = None,
                       illustration_path: Optional[str] = None, plugin_dir: Optional[str] = None) -> bool:
    """
    转换 SVG 为 PNG（便捷函数）

    Args:
        svg_path: SVG 文件路径
        output_path: 输出 PNG 路径
        width: 输出宽度（可选）
        height: 输出高度（可选）
        illustration_path: 曲绘文件夹路径（可选）
        plugin_dir: 插件目录路径（可选，用于加载默认背景和字体）

    Returns:
        bool: 转换是否成功
    """
    converter = get_converter(illustration_path=illustration_path, plugin_dir=plugin_dir)
    return converter.convert(svg_path, output_path, width, height)


def svg_converter_available() -> bool:
    """检查是否有可用的 SVG 转换器"""
    converter = get_converter()
    return len(converter.get_available_converters()) > 0
