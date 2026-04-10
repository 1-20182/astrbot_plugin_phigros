#!/usr/bin/env python3
"""
测试排行榜渲染功能
"""

import asyncio
from pathlib import Path
from design_system import PhigrosDesignSystem


async def test_leaderboard_rendering():
    """测试排行榜渲染"""
    # 模拟排行榜数据
    mock_leaderboard_data = {
        "items": [
            {"rank": 1, "alias": "Player1", "score": 16.5432},
            {"rank": 2, "alias": "Player2", "score": 16.4321},
            {"rank": 3, "alias": "Player3", "score": 16.3210},
            {"rank": 4, "alias": "Player4", "score": 16.2109},
            {"rank": 5, "alias": "Player5", "score": 16.1098},
            {"rank": 6, "alias": "Player6", "score": 16.0987},
            {"rank": 7, "alias": "Player7", "score": 16.0876},
            {"rank": 8, "alias": "Player8", "score": 16.0765},
            {"rank": 9, "alias": "Player9", "score": 16.0654},
            {"rank": 10, "alias": "Player10", "score": 16.0543}
        ]
    }
    
    # 初始化设计系统
    design_system = PhigrosDesignSystem(
        plugin_dir=Path(__file__).parent,
        cache_dir=Path(__file__).parent / "cache",
        illustration_path=Path(__file__).parent / "ILLUSTRATION"
    )
    
    await design_system.initialize()
    
    # 渲染排行榜
    output_path = Path(__file__).parent / "output" / "leaderboard_test.png"
    output_path.parent.mkdir(exist_ok=True)
    
    success = await design_system.render_leaderboard(mock_leaderboard_data, output_path)
    
    if success:
        print(f"✅ 排行榜渲染成功: {output_path}")
    else:
        print("❌ 排行榜渲染失败")
    
    await design_system.terminate()


if __name__ == "__main__":
    asyncio.run(test_leaderboard_rendering())
