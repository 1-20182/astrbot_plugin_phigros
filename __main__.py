#!/usr/bin/env python3
"""
Phigros 插件独立运行入口

允许插件在没有 AstrBot 环境的情况下运行
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入核心模块
try:
    from phi_style_renderer_standalone import PhiStyleRendererStandalone
    HAS_STANDALONE_RENDERER = True
except ImportError:
    HAS_STANDALONE_RENDERER = False

try:
    from main import PhigrosPlugin
    from phi_style_renderer import PhiStyleRenderer
    from utils import resolve_illustration_path
    HAS_CORE_MODULES = True
except ImportError:
    HAS_CORE_MODULES = False

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

logger = SimpleLogger()

# 模拟 Context 类
class MockContext:
    def __init__(self):
        self.config = {}

async def test_renderer():
    """测试渲染器功能"""
    logger.info("🎨 测试渲染器功能")
    
    plugin_dir = Path(__file__).parent
    cache_dir = plugin_dir / "output" / "cache"
    illustration_path = plugin_dir / "ILLUSTRATION"
    
    # 创建渲染器
    if HAS_STANDALONE_RENDERER:
        renderer = PhiStyleRendererStandalone(
            plugin_dir=plugin_dir,
            cache_dir=cache_dir,
            illustration_path=illustration_path,
            image_quality=95
        )
    elif HAS_CORE_MODULES:
        renderer = PhiStyleRenderer(
            plugin_dir=plugin_dir,
            cache_dir=cache_dir,
            illustration_path=illustration_path,
            image_quality=95
        )
    else:
        logger.error("❌ 没有可用的渲染器")
        return
    
    # 初始化渲染器
    await renderer.initialize()
    
    # 测试数据
    test_data = {
        "gameuser": {
            "nickname": "Test Player",
            "PlayerId": "123456",
            "rks": 15.5,
            "challengeModeRank": 438
        },
        "records": [
            {
                "song": "Igallta",
                "difficulty": "IN",
                "score": 980000,
                "acc": 99.5,
                "fc": True,
                "rks": 15.0
            },
            {
                "song": "Spasmodic",
                "difficulty": "IN",
                "score": 970000,
                "acc": 98.5,
                "fc": True,
                "rks": 14.0
            }
        ]
    }
    
    # 渲染测试
    output_path = plugin_dir / "test_output.png"
    success = await renderer.render_b30(test_data, output_path)
    
    if success:
        logger.info(f"✅ 渲染成功！输出文件: {output_path}")
    else:
        logger.error("❌ 渲染失败")
    
    # 清理资源
    await renderer.terminate()

async def test_plugin():
    """测试插件初始化"""
    logger.info("🔧 测试插件初始化")
    
    if not HAS_CORE_MODULES:
        logger.error("❌ 核心模块导入失败，无法测试插件")
        return
    
    # 创建模拟上下文
    context = MockContext()
    
    # 初始化插件
    plugin = PhigrosPlugin(context)
    await plugin.initialize()
    
    logger.info("✅ 插件初始化成功")
    
    # 清理资源
    await plugin.terminate()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Phigros 插件独立运行工具")
    parser.add_argument("--test-renderer", action="store_true", help="测试渲染器功能")
    parser.add_argument("--test-plugin", action="store_true", help="测试插件初始化")
    
    args = parser.parse_args()
    
    if args.test_renderer:
        await test_renderer()
    elif args.test_plugin:
        await test_plugin()
    else:
        # 默认运行
        logger.info("🚀 Phigros 插件独立运行测试")
        logger.info("使用 --help 查看可用命令")
        
        # 测试渲染器
        await test_renderer()

if __name__ == "__main__":
    asyncio.run(main())
