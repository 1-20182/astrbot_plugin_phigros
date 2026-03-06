"""
🎨 HTML + Playwright 渲染器

> "效果最佳的渲染方案！" ✨

使用 HTML/CSS 模板 + Playwright 截图，完美还原 phi-plugin 的视觉效果
"""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from astrbot.api import logger

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安装，无法使用 HTML+Playwright 渲染模式")


class HtmlPlaywrightRenderer:
    """
    🎨 HTML + Playwright 渲染器
    
    参考 phi-plugin 的设计，使用 HTML 模板 + Playwright 截图
    效果最佳，但需要安装 Playwright 和 Chromium
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
        
        # 模板目录
        self.template_dir = plugin_dir / "resources" / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Playwright 实例
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        logger.info("🎨 HTML+Playwright 渲染器初始化")
    
    async def initialize(self):
        """初始化 Playwright"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright 未安装，请运行: pip install playwright && playwright install chromium")
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("✅ Playwright 初始化成功")
        except Exception as e:
            logger.error(f"Playwright 初始化失败: {e}")
            raise
    
    async def terminate(self):
        """清理资源"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("🧹 Playwright 资源已清理")
    
    def _generate_b30_html(self, data: Dict[str, Any]) -> str:
        """
        生成 Best30 HTML 模板
        
        参考 phi-plugin 的 b19.art 模板设计
        """
        # 获取玩家信息
        gameuser = data.get('gameuser', {})
        records = data.get('records', [])
        
        # 构建 HTML
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans SC', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        /* 头部信息 */
        .header {{
            display: flex;
            align-items: center;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }}
        
        .avatar {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            overflow: hidden;
            margin-right: 20px;
            border: 3px solid #fff;
        }}
        
        .avatar img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .player-info {{
            flex: 1;
        }}
        
        .player-name {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .player-id {{
            font-size: 14px;
            color: #aaa;
        }}
        
        .rks-box {{
            background: white;
            color: black;
            padding: 10px 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .rks-label {{
            font-size: 12px;
            font-weight: bold;
        }}
        
        .rks-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        
        /* 成绩卡片网格 */
        .records-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        
        .record-card {{
            background: rgba(0, 0, 0, 0.6);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            transition: transform 0.3s;
        }}
        
        .record-card:hover {{
            transform: translateY(-5px);
        }}
        
        .card-illustration {{
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
        }}
        
        .card-info {{
            padding: 12px;
        }}
        
        .song-name {{
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .song-artist {{
            font-size: 11px;
            color: #aaa;
            margin-bottom: 8px;
        }}
        
        .score-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .score {{
            font-size: 18px;
            font-weight: bold;
            color: #ffd700;
        }}
        
        .acc {{
            font-size: 12px;
            color: #aaa;
        }}
        
        .difficulty {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }}
        
        .diff-ez {{ background: #4ade80; color: #000; }}
        .diff-hd {{ background: #60a5fa; color: #000; }}
        .diff-in {{ background: #f472b6; color: #000; }}
        .diff-at {{ background: #a78bfa; color: #000; }}
        
        .rank {{
            position: absolute;
            top: 10px;
            left: 10px;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }}
        
        .rank-1 {{ background: linear-gradient(135deg, #ffd700, #ffed4a); color: #000; }}
        .rank-2 {{ background: linear-gradient(135deg, #c0c0c0, #e8e8e8); color: #000; }}
        .rank-3 {{ background: linear-gradient(135deg, #cd7f32, #daa520); color: #fff; }}
        .rank-other {{ background: rgba(0, 0, 0, 0.7); color: #fff; }}
        
        .fc-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            width: 24px;
            height: 24px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .fc-fc {{ background: #60a5fa; }}
        .fc-ap {{ background: #ffd700; color: #000; }}
        
        /* 底部信息 */
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部信息 -->
        <div class="header">
            <div class="avatar">
                <img src="{gameuser.get('avatar_url', '')}" alt="avatar">
            </div>
            <div class="player-info">
                <div class="player-name">{gameuser.get('nickname', 'Unknown')}</div>
                <div class="player-id">ID: {gameuser.get('PlayerId', 'N/A')}</div>
            </div>
            <div class="rks-box">
                <div class="rks-label">RKS</div>
                <div class="rks-value">{gameuser.get('rks', 0):.4f}</div>
            </div>
        </div>
        
        <!-- 成绩卡片 -->
        <div class="records-grid">
'''
        
        # 添加成绩卡片
        for i, record in enumerate(records[:30], 1):
            rank_class = f"rank-{i}" if i <= 3 else "rank-other"
            diff_class = f"diff-{record.get('difficulty', 'in').lower()}"
            fc_class = ""
            fc_text = ""
            if record.get('fc'):
                fc_class = "fc-ap" if record.get('score', 0) == 1000000 else "fc-fc"
                fc_text = "AP" if record.get('score', 0) == 1000000 else "FC"
            
            html += f'''
            <div class="record-card">
                <div class="rank {rank_class}">{i}</div>
                {f'<div class="fc-badge {fc_class}">{fc_text}</div>' if fc_text else ''}
                <img class="card-illustration" src="{record.get('illustration_url', '')}" alt="{record.get('song', '')}">
                <div class="card-info">
                    <div class="song-name">{record.get('song', 'Unknown')}</div>
                    <div class="song-artist">{record.get('artist', '')}</div>
                    <div class="score-info">
                        <span class="score">{record.get('score', 0):,}</span>
                        <span class="difficulty {diff_class}">{record.get('difficulty', 'IN')}</span>
                    </div>
                    <div class="acc">Acc: {record.get('acc', 0):.2f}% | RKS: {record.get('rks', 0):.2f}</div>
                </div>
            </div>
'''
        
        html += '''
        </div>
        
        <!-- 底部 -->
        <div class="footer">
            Generated by Phigros Query Plugin
        </div>
    </div>
</body>
</html>'''
        
        return html
    
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
            # 生成 HTML
            html_content = self._generate_b30_html(data)
            
            # 创建临时 HTML 文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html = f.name
            
            try:
                # 使用 Playwright 截图
                page = await self.browser.new_page()
                await page.goto(f'file://{temp_html}')
                
                # 等待页面加载完成
                await page.wait_for_load_state('networkidle')
                
                # 获取页面高度
                height = await page.evaluate('document.body.scrollHeight')
                
                # 截图
                await page.screenshot(
                    path=str(output_path),
                    full_page=True,
                    type='png'
                )
                
                await page.close()
                
                logger.info(f"✅ 渲染成功: {output_path}")
                return True
                
            finally:
                # 清理临时文件
                os.unlink(temp_html)
                
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            return False
    
    async def render_score(self, data: Dict[str, Any], output_path: Path) -> bool:
        """渲染单曲成绩图"""
        # TODO: 实现单曲成绩渲染
        logger.warning("单曲成绩渲染暂未实现")
        return False
