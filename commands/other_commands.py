"""
📌 其他命令模块

包含帮助、视频等其他命令
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain, Image, Video


class OtherCommands:
    """
    其他命令处理器
    """

    def __init__(self, plugin):
        self.plugin = plugin

    @filter.command("phi_help")
    async def get_help(self, event: AstrMessageEvent):
        """
        获取帮助信息
        用法: /phi_help
        """
        try:
            # 尝试生成帮助图片
            if self.plugin.HELP_IMAGE_GENERATOR_AVAILABLE:
                from ..help_image_generator import generate_help_image
                output_path = self.plugin.output_dir / "help_image.png"
                success = generate_help_image(output_path)
                
                if success:
                    yield event.chain_result([
                        Plain("📚 Phigros 插件帮助\n"),
                        Image(file=str(output_path))
                    ])
                    return

            # 回退到文字帮助
            help_text = """
🎮 Phigros 插件帮助

📡 认证相关命令：
  /phi_bind <token> [版本] - 绑定账号
  /phi_unbind - 解绑账号
  /phi_qrlogin [版本] - 扫码登录

📊 查询相关命令：
  /phi_save [token] [版本] - 查存档
  /phi_b30 [token] [版本] [主题] - Best30 成绩图
  /phi_rks_history [token] [数量] - RKS 历史
  /phi_bn [数量] [主题] - BestN 成绩图
  /phi_song <曲名> - 单曲成绩图
  /phi_leaderboard - 排行榜
  /phi_rank <开始> <结束> - 查排名
  /phi_search <关键词> - 搜歌
  /phi_updates [数量] - 新曲速递

🎬 其他命令：
  /phi_video - 随机视频
  /phi_video_list - 视频列表
  /phi_help - 查看帮助

💡 使用小贴士：
  • 绑定账号后可直接使用命令
  • 版本参数：cn (国服) 或 global (国际服)
  • 主题参数：black (默认) 或 white
  • 扫码登录最方便哦！
            """
            yield event.plain_result(help_text)

        except Exception as e:
            self.plugin.logger.error(f"生成帮助信息失败: {e}")
            # 发送简单文字帮助
            simple_help = """
🎮 Phigros 插件命令：
  /phi_bind <token> - 绑定账号
  /phi_unbind - 解绑账号
  /phi_qrlogin - 扫码登录
  /phi_save - 查存档
  /phi_b30 - Best30 成绩图
  /phi_rks_history - RKS 历史
  /phi_help - 查看帮助
            """
            yield event.plain_result(simple_help)

    @filter.command("phi_video")
    async def send_random_video(self, event: AstrMessageEvent):
        """
        发送随机 Phigros 视频
        用法: /phi_video
        """
        if not self.plugin.VIDEO_SENDER_AVAILABLE:
            yield event.plain_result("❌ 视频功能不可用")
            return

        try:
            from ..video_sender import get_random_video_path
            video_path = get_random_video_path()
            
            if video_path:
                yield event.chain_result([
                    Plain("🎬 随机 Phigros 视频\n"),
                    Video(file=str(video_path))
                ])
            else:
                yield event.plain_result("❌ 没有找到视频文件，请在 VideoClip 目录添加视频")

        except Exception as e:
            self.plugin.logger.error(f"发送视频失败: {e}")
            yield event.plain_result(f"❌ 发送视频失败: {str(e)}")

    @filter.command("phi_video_list")
    async def list_videos(self, event: AstrMessageEvent):
        """
        列出所有可用视频
        用法: /phi_video_list
        """
        if not self.plugin.VIDEO_SENDER_AVAILABLE:
            yield event.plain_result("❌ 视频功能不可用")
            return

        try:
            from ..video_sender import VideoSender
            sender = VideoSender()
            videos = sender.get_video_list()
            
            if videos:
                video_list = "🎬 可用视频列表：\n"
                for i, video in enumerate(videos, 1):
                    video_list += f"{i}. {video['name']} ({video['size']})\n"
                yield event.plain_result(video_list)
            else:
                yield event.plain_result("❌ 没有找到视频文件")

        except Exception as e:
            self.plugin.logger.error(f"获取视频列表失败: {e}")
            yield event.plain_result(f"❌ 获取视频列表失败: {str(e)}")
