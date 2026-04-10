"""
🎨 Phigros 设计系统使用示例

展示如何使用设计系统创建不同类型的图像输出
"""

import asyncio
from pathlib import Path
from design_system import PhigrosDesignSystem


async def main():
    """主函数"""
    # 初始化设计系统
    plugin_dir = Path(".")
    cache_dir = Path("./cache")
    illustration_path = Path("./resources/img/background")  # 实际使用时需要替换为正确的曲绘目录
    
    design_system = PhigrosDesignSystem(
        plugin_dir=plugin_dir,
        cache_dir=cache_dir,
        illustration_path=illustration_path
    )
    
    # 初始化资源
    await design_system.initialize()
    
    try:
        # 示例 1: 渲染 Best30 成绩图
        print("🎨 渲染 Best30 成绩图...")
        b30_data = {
            "gameuser": {
                "nickname": "测试玩家",
                "PlayerId": "123456789",
                "rks": 15.2345,
                "challengeModeRank": 400
            },
            "records": [
                {
                    "song": "Rrhar'il",
                    "difficulty": "IN",
                    "score": 998765,
                    "acc": 99.56,
                    "rks": 16.8,
                    "fc": True
                },
                {
                    "song": "Igallta",
                    "difficulty": "IN",
                    "score": 997654,
                    "acc": 99.23,
                    "rks": 16.5,
                    "fc": True
                },
                {
                    "song": "Hakken!!",
                    "difficulty": "IN",
                    "score": 996543,
                    "acc": 98.98,
                    "rks": 16.2,
                    "fc": True
                }
                # 可以添加更多记录
            ]
        }
        
        # 创建模板
        b30_template = design_system.create_template('b30', b30_data)
        
        # 渲染图片
        b30_output = Path("./output/b30_example.png")
        await design_system.render_from_template('b30', b30_template, b30_output)
        print(f"✅ Best30 成绩图已保存到: {b30_output}")
        
        # 示例 2: 渲染单曲成绩图
        print("\n🎨 渲染单曲成绩图...")
        score_data = {
            "gameuser": {
                "nickname": "测试玩家",
                "PlayerId": "123456789",
                "rks": 15.2345
            },
            "record": {
                "song": "Rrhar'il",
                "difficulty": "IN",
                "score": 998765,
                "acc": 99.56,
                "rks": 16.8,
                "fc": True
            }
        }
        
        # 创建模板
        score_template = design_system.create_template('score', score_data)
        
        # 渲染图片
        score_output = Path("./output/score_example.png")
        await design_system.render_from_template('score', score_template, score_output)
        print(f"✅ 单曲成绩图已保存到: {score_output}")
        
        # 示例 3: 渲染 RKS 历史趋势图
        print("\n🎨 渲染 RKS 历史趋势图...")
        rks_history_data = {
            "gameuser": {
                "nickname": "测试玩家",
                "rks": 15.2345
            },
            "items": [
                {"createdAt": "2024-01-01T00:00:00", "rks": 10.0},
                {"createdAt": "2024-01-15T00:00:00", "rks": 11.2},
                {"createdAt": "2024-02-01T00:00:00", "rks": 12.5},
                {"createdAt": "2024-02-15T00:00:00", "rks": 13.8},
                {"createdAt": "2024-03-01T00:00:00", "rks": 14.5},
                {"createdAt": "2024-03-15T00:00:00", "rks": 15.2}
            ],
            "currentRks": 15.2345,
            "peakRks": 15.3456,
            "total": 100
        }
        
        # 创建模板
        rks_history_template = design_system.create_template('rks_history', rks_history_data)
        
        # 渲染图片
        rks_history_output = Path("./output/rks_history_example.png")
        await design_system.render_from_template('rks_history', rks_history_template, rks_history_output)
        print(f"✅ RKS 历史趋势图已保存到: {rks_history_output}")
        
    finally:
        # 清理资源
        await design_system.terminate()
        print("\n🧹 资源已清理")


if __name__ == "__main__":
    asyncio.run(main())
