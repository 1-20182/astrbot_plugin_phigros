"""
测试图片生成功能
"""
import asyncio
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from phi_style_renderer import PhiStyleRenderer

async def test_renderers():
    """测试所有渲染器功能"""
    plugin_dir = Path(__file__).parent
    cache_dir = plugin_dir / "output" / "cache"
    illustration_path = plugin_dir / "ILLUSTRATION"
    avatar_path = plugin_dir / "AVATAR"
    
    # 创建渲染器
    renderer = PhiStyleRenderer(
        plugin_dir=plugin_dir,
        cache_dir=cache_dir,
        illustration_path=illustration_path,
        avatar_path=avatar_path
    )
    
    await renderer.initialize()
    
    try:
        # 1. 测试 render_b30 (使用模拟数据)
        print("📊 测试 render_b30...")
        b30_data = {
            "gameuser": {
                "nickname": "测试玩家",
                "PlayerId": "test123",
                "rks": 15.5,
                "challengeModeRank": 400
            },
            "records": [
                {
                    "song": "Test Song 1",
                    "difficulty": "IN",
                    "score": 990000,
                    "acc": 99.5,
                    "rks": 15.5,
                    "fc": True,
                    "__index__": 0
                }
            ]
        }
        b30_output = plugin_dir / "output" / "test_b30.png"
        success = await renderer.render_b30(b30_data, b30_output)
        print(f"   {'✅' if success else '❌'} render_b30: {b30_output}")
        
        # 2. 测试 render_rks_history
        print("\n📈 测试 render_rks_history...")
        rks_history_data = {
            "items": [
                {"createdAt": "2024-01-01T00:00:00Z", "rks": 15.0, "rksJump": 0.5},
                {"createdAt": "2024-01-02T00:00:00Z", "rks": 15.2, "rksJump": 0.2},
                {"createdAt": "2024-01-03T00:00:00Z", "rks": 15.5, "rksJump": 0.3}
            ],
            "currentRks": 15.5,
            "peakRks": 15.5,
            "total": 3
        }
        rks_output = plugin_dir / "output" / "test_rks_history.png"
        success = await renderer.render_rks_history(rks_history_data, rks_output)
        print(f"   {'✅' if success else '❌'} render_rks_history: {rks_output}")
        
        # 3. 测试 render_leaderboard
        print("\n🏆 测试 render_leaderboard...")
        leaderboard_data = {
            "items": [
                {"rank": 1, "alias": "玩家1", "score": 16.0},
                {"rank": 2, "alias": "玩家2", "score": 15.8},
                {"rank": 3, "alias": "玩家3", "score": 15.5}
            ]
        }
        leaderboard_output = plugin_dir / "output" / "test_leaderboard.png"
        success = await renderer.render_leaderboard(leaderboard_data, leaderboard_output)
        print(f"   {'✅' if success else '❌'} render_leaderboard: {leaderboard_output}")
        
        # 4. 测试 render_song_detail
        print("\n🎵 测试 render_song_detail...")
        song_data = {
            "name": "测试歌曲",
            "composer": "测试作曲家",
            "chartConstants": {
                "ez": 10.5,
                "hd": 13.0,
                "in": 15.5,
                "at": 17.0
            }
        }
        song_output = plugin_dir / "output" / "test_song_detail.png"
        success = await renderer.render_song_detail(song_data, song_output)
        print(f"   {'✅' if success else '❌'} render_song_detail: {song_output}")
        
        # 5. 测试 render_save_data
        print("\n💾 测试 render_save_data...")
        save_data = {
            "gameuser": {
                "nickname": "存档玩家",
                "PlayerId": "save123",
                "rks": 14.5,
                "challengeModeRank": 380
            },
            "rks": {"totalRks": 14.5},
            "save": {
                "summaryParsed": {},
                "game_progress": {"challengeModeRank": 380}
            }
        }
        save_output = plugin_dir / "output" / "test_save_data.png"
        success = await renderer.render_save_data(save_data, save_output)
        print(f"   {'✅' if success else '❌'} render_save_data: {save_output}")
        
        # 6. 测试 render_rank
        print("\n📊 测试 render_rank...")
        rank_data = {
            "items": [
                {"rank": 10, "alias": "排名10玩家", "score": 14.0},
                {"rank": 11, "alias": "排名11玩家", "score": 13.9},
                {"rank": 12, "alias": "排名12玩家", "score": 13.8}
            ],
            "start": 10,
            "end": 12
        }
        rank_output = plugin_dir / "output" / "test_rank.png"
        success = await renderer.render_rank(rank_data, rank_output)
        print(f"   {'✅' if success else '❌'} render_rank: {rank_output}")
        
        # 7. 测试 render_updates
        print("\n🆕 测试 render_updates...")
        updates_data = [
            {
                "version": "3.0.0",
                "updateDate": "2024-01-01",
                "content": "**新曲更新**\n- 新增 5 首歌曲\n- 新增 2 首 AT 难度"
            }
        ]
        updates_output = plugin_dir / "output" / "test_updates.png"
        success = await renderer.render_updates(updates_data, updates_output, 1)
        print(f"   {'✅' if success else '❌'} render_updates: {updates_output}")
        
        print("\n🎉 所有测试完成!")
        
    finally:
        await renderer.terminate()

if __name__ == "__main__":
    asyncio.run(test_renderers())
