"""
🎮 Phigros Query 插件主模块

核心功能：查询 Phigros 游戏数据、生成成绩图、扫码登录等
"""

import aiohttp
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain, Image, Video
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger

# 导入配置
from .config import (
    ConfigManager,
    BASE_URL, DEFAULT_API_TOKEN,
    HTTP_TIMEOUT, HTTP_CONNECT_TIMEOUT, HTTP_SOCK_READ_TIMEOUT,
    HTTP_POOL_SIZE, HTTP_POOL_PER_HOST,
    DEFAULT_ILLUSTRATION_PATH, DEFAULT_TAPTAP_VERSION,
    DEFAULT_SEARCH_LIMIT, DEFAULT_HISTORY_LIMIT,
    CACHE_TTL, QR_LOGIN_TIMEOUT
)

# 导入核心模块
from .core import PhigrosAPIClient, HybridCache
from .core.user_data_manager import UserDataManager

# 导入命令模块
from .commands import AuthCommands, QueryCommands, OtherCommands

# 导入工具函数
from .utils import (
    SimpleCache, resolve_illustration_path,
    sanitize_filename, encrypt_token, decrypt_token,
    send_image_with_fallback, format_score, format_acc, format_rks,
    truncate_text
)

# 可选模块导入（带容错）
# 使用传统的 try/except 导入方式

# SVG 转换器
try:
    from .svg_converter import convert_svg_to_png, svg_converter_available, get_converter
    SVG_CONVERTER_AVAILABLE = True
except ImportError as e:
    SVG_CONVERTER_AVAILABLE = False
    logger.warning(f"svg_converter 模块未加载: {e}")

# 旧版渲染器
try:
    from .renderer import PhigrosRenderer
    RENDERER_AVAILABLE = True
except ImportError as e:
    RENDERER_AVAILABLE = False
    logger.warning(f"renderer 模块未加载: {e}")

# 扫码登录
try:
    from .taptap_login_api import TapTapLoginManagerAPI, LoginStatus, LoginResult
    API_LOGIN_AVAILABLE = True
except ImportError as e:
    API_LOGIN_AVAILABLE = False
    logger.warning(f"taptap_login_api 模块未加载: {e}")

# 曲绘更新器
try:
    from .illustration_updater import auto_update_illustrations, IllustrationUpdater
    ILLUSTRATION_UPDATER_AVAILABLE = True
except ImportError as e:
    ILLUSTRATION_UPDATER_AVAILABLE = False
    logger.warning(f"illustration_updater 模块未加载: {e}")

# 高级渲染器
try:
    from .advanced_renderer import AdvancedPhigrosRenderer
    ADVANCED_RENDERER_AVAILABLE = True
except ImportError as e:
    ADVANCED_RENDERER_AVAILABLE = False
    logger.warning(f"advanced_renderer 模块未加载: {e}")

# Phi-Plugin 风格渲染器
try:
    from .phi_style_renderer import PhiStyleRenderer
    PHI_STYLE_RENDERER_AVAILABLE = True
except ImportError as e:
    PHI_STYLE_RENDERER_AVAILABLE = False
    logger.warning(f"phi_style_renderer 模块未加载: {e}")

# 帮助图片生成器
try:
    from .help_image_generator import HelpImageGenerator, generate_help_image
    HELP_IMAGE_GENERATOR_AVAILABLE = True
except ImportError as e:
    HELP_IMAGE_GENERATOR_AVAILABLE = False
    logger.debug(f"help_image_generator 模块未加载: {e}")  # 改为debug级别，避免不必要的警告

# 视频发送器
try:
    from .video_sender import VideoSender, get_random_video_path
    VIDEO_SENDER_AVAILABLE = True
except ImportError as e:
    VIDEO_SENDER_AVAILABLE = False
    logger.warning(f"video_sender 模块未加载: {e}")





@register("astrbot_plugin_phigros", "Assistant", "Phigros 音游数据查询插件", "1.8.0")
class PhigrosPlugin(Star):
    """
    🎮 Phigros 音游数据查询插件
    
    查存档、看排名、搜歌曲、追新曲... 功能多多，快乐加倍！
    支持扫码登录、账号绑定，还能生成美美的成绩图~ ✨
    """
    
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context, config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_client: Optional[PhigrosAPIClient] = None
        self.renderer: Optional[PhigrosRenderer] = None
        self.cache: Optional[HybridCache] = None

        # 使用插件目录作为数据目录（避免路径问题）
        self.data_dir: Path = Path(__file__).parent
        self.output_dir = self.data_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 插件数据目录: {self.data_dir}")
        logger.info(f"📁 输出目录: {self.output_dir}")

        # 初始化用户数据管理器
        self.user_data = UserDataManager(self.data_dir)

        # 从插件配置中读取设置
        self.plugin_config = config or {}
        logger.info(f"Phigros 插件配置: {self.plugin_config}")

        # 初始化命令处理器
        self.auth_commands = AuthCommands(self)
        self.query_commands = QueryCommands(self)
        self.other_commands = OtherCommands(self)

        # 暴露模块可用性到实例属性
        self.SVG_CONVERTER_AVAILABLE = SVG_CONVERTER_AVAILABLE
        self.API_LOGIN_AVAILABLE = API_LOGIN_AVAILABLE
        self.HELP_IMAGE_GENERATOR_AVAILABLE = HELP_IMAGE_GENERATOR_AVAILABLE
        self.VIDEO_SENDER_AVAILABLE = VIDEO_SENDER_AVAILABLE
        self.logger = logger
        self.base_url = BASE_URL
        
        # 导入监控模块
        from .core.monitoring import api_monitor
        self.api_monitor = api_monitor

    async def initialize(self):
        """插件初始化"""
        # 初始化用户数据管理器的锁
        await self.user_data.initialize()

        # 从插件配置中读取 API Token，如果没有则使用默认 Token
        self.api_token = ConfigManager.get_config(
            self.plugin_config, 
            "API_TOKEN", 
            DEFAULT_API_TOKEN, 
            "phigros_api_token"
        )
        if self.api_token:
            logger.info("Phigros API Token 已配置")
        else:
            logger.warning("Phigros API Token 未配置，请在 WebUI 中设置")

        # 读取其他配置
        self.enable_renderer = ConfigManager.get_config(
            self.plugin_config, 
            "ENABLE_RENDERER", 
            True, 
            "enable_renderer"
        )
        self.illustration_path = ConfigManager.get_config(
            self.plugin_config, 
            "ILLUSTRATION_PATH", 
            "./ILLUSTRATION", 
            "illustration_path"
        )
        self.image_quality = ConfigManager.get_config(
            self.plugin_config, 
            "IMAGE_QUALITY", 
            95, 
            "image_quality"
        )
        self.default_taptap_version = ConfigManager.get_config(
            self.plugin_config, 
            "TAPTAP_VERSION", 
            "cn", 
            "default_taptap_version"
        )
        self.default_search_limit = ConfigManager.get_config(
            self.plugin_config, 
            "SEARCH_LIMIT", 
            5, 
            "default_search_limit"
        )
        self.default_history_limit = ConfigManager.get_config(
            self.plugin_config, 
            "HISTORY_LIMIT", 
            10, 
            "default_history_limit"
        )

        # 初始化 API 客户端
        self.api_client = PhigrosAPIClient(
            base_url=BASE_URL,
            api_token=self.api_token,
            timeout=HTTP_TIMEOUT,
            pool_size=HTTP_POOL_SIZE,
            pool_per_host=HTTP_POOL_PER_HOST,
            cache_dir=self.output_dir / "api_cache"
        )
        await self.api_client.initialize()
        logger.info("🚀 Phigros API 客户端初始化成功")

        # 初始化混合缓存
        self.cache = HybridCache(
            cache_dir=self.output_dir / "cache",
            lru_capacity=1000,
            lru_ttl=300,  # 5分钟
            disk_ttl=3600,  # 1小时
            disk_max_size=1000
        )
        logger.info("� 混合缓存初始化成功")

        # 初始化渲染器
        logger.info(f"🔧 开始初始化渲染器: ADVANCED_RENDERER_AVAILABLE={ADVANCED_RENDERER_AVAILABLE}, enable_renderer={self.enable_renderer}")

        # 首先尝试使用 PhiStyleRenderer（直接导入）
        try:
            from .phi_style_renderer import PhiStyleRenderer
            illust_path = resolve_illustration_path(Path(__file__).parent, self.illustration_path)
            avatar_path = Path(__file__).parent / "AVATAR"
            logger.info("🎨 直接创建 PhiStyleRenderer")
            self.renderer = PhiStyleRenderer(
                plugin_dir=Path(__file__).parent,
                cache_dir=self.output_dir / "cache",
                illustration_path=illust_path,
                image_quality=self.image_quality,
                avatar_path=avatar_path
            )
            await self.renderer.initialize()
            logger.info("✅ PhiStyleRenderer 初始化成功")
        except Exception as e:
            logger.error(f"❌ PhiStyleRenderer 创建失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.renderer = None
        
        # 如果直接创建失败，尝试使用高级渲染器
        if self.renderer is None and ADVANCED_RENDERER_AVAILABLE and self.enable_renderer:
            try:
                illust_path = resolve_illustration_path(Path(__file__).parent, self.illustration_path)
                avatar_path = Path(__file__).parent / "AVATAR"
                renderer_mode = ConfigManager.get_config(
                    self.plugin_config, 
                    "RENDERER_MODE", 
                    "auto", 
                    "renderer_mode"
                )
                logger.info(f"🎨 创建 AdvancedPhigrosRenderer，模式: {renderer_mode}")
                self.renderer = AdvancedPhigrosRenderer(
                    plugin_dir=Path(__file__).parent,
                    cache_dir=self.output_dir / "cache",
                    illustration_path=illust_path,
                    mode=renderer_mode if renderer_mode != "auto" else None,
                    image_quality=self.image_quality,
                    avatar_path=avatar_path
                )
                await self.renderer.initialize()
                logger.info(f"✅ 高级渲染器初始化成功，模式: {self.renderer.get_mode()}")
            except Exception as e:
                logger.error(f"❌ 高级渲染器初始化失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.renderer = None
        elif self.renderer is None and RENDERER_AVAILABLE and self.enable_renderer:
            # 回退到旧版渲染器
            try:
                illust_path = resolve_illustration_path(Path(__file__).parent, self.illustration_path)
                self.renderer = PhigrosRenderer(
                    cache_dir=str(self.output_dir / "cache"),
                    illustration_path=str(illust_path),
                    image_quality=self.image_quality
                )
                await self.renderer.initialize()
                logger.info("渲染器初始化成功（旧版）")
            except Exception as e:
                logger.error(f"渲染器初始化失败: {e}")
                self.renderer = None

        # 自动更新曲绘（在后台运行，不阻塞初始化）
        if ILLUSTRATION_UPDATER_AVAILABLE:
            self.enable_auto_update = ConfigManager.get_config(
                self.plugin_config, 
                "ENABLE_AUTO_UPDATE_ILLUSTRATION", 
                True, 
                "enable_auto_update_illustration"
            )
            if self.enable_auto_update:
                asyncio.create_task(self._auto_update_illustrations())
            else:
                logger.info("⏭️ 曲绘自动更新已禁用，跳过检查")

    async def _auto_update_illustrations(self):
        """自动更新曲绘（后台任务）"""
        try:
            plugin_dir = Path(__file__).parent
            illust_path = resolve_illustration_path(plugin_dir, self.illustration_path)
            
            # 获取代理设置（从配置中读取）
            proxy = ConfigManager.get_config(
                self.plugin_config, 
                "ILLUSTRATION_UPDATE_PROXY", 
                "", 
                "illustration_update_proxy"
            )
            
            logger.info("🎨 正在检查曲绘更新...")
            success, fail, status = await auto_update_illustrations(
                plugin_dir=plugin_dir,
                illustration_path=illust_path,
                proxy=proxy if proxy else None
            )
            
            if success > 0:
                logger.info(f"🎉 曲绘更新完成！成功下载 {success} 个，失败 {fail} 个")
            elif "跳过检查" in status:
                logger.info(f"⏭️ {status}")
            else:
                logger.info(f"ℹ️ 曲绘状态: {status}")
                
        except Exception as e:
            logger.warning(f"自动更新曲绘失败: {e}")

    async def terminate(self):
        """插件销毁"""
        if self.api_client:
            await self.api_client.terminate()
        if self.renderer:
            await self.renderer.terminate()

    async def _render_and_send(
        self, event: AstrMessageEvent, 
        render_func, 
        data: Dict[str, Any], 
        filename: str,
        *args
    ):
        """渲染图片并发送"""
        if not self.renderer:
            # 渲染器不可用，回退到文本输出
            if 'items' in data and isinstance(data['items'], list):
                # 排行榜数据
                items = data['items'][:15]
                msg_parts = ["📊 Phigros RKS 排行榜\n\n"]
                for item in items:
                    rank = item.get('rank', 0)
                    alias = item.get('alias', '未知')
                    score = item.get('score', 0)
                    msg_parts.append(f"{rank}. {alias} - RKS: {score:.4f}\n")
                yield event.plain_result("".join(msg_parts))
            else:
                yield event.plain_result("❌ 图片渲染功能不可用")
            return
        
        try:
            output_path = str(self.output_dir / filename)
            await render_func(data, output_path, *args)
            
            # 发送图片
            yield event.chain_result([Image(file=output_path)])
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            # 渲染失败，回退到文本输出
            if 'items' in data and isinstance(data['items'], list):
                # 排行榜数据
                items = data['items'][:15]
                msg_parts = ["📊 Phigros RKS 排行榜\n\n"]
                for item in items:
                    rank = item.get('rank', 0)
                    alias = item.get('alias', '未知')
                    score = item.get('score', 0)
                    msg_parts.append(f"{rank}. {alias} - RKS: {score:.4f}\n")
                yield event.plain_result("".join(msg_parts))
            else:
                yield event.plain_result(f"❌ 图片渲染失败: {str(e)}")

    def _get_user_id(self, event: AstrMessageEvent) -> tuple:
        """获取用户平台标识和ID"""
        platform = event.get_platform_name()
        user_id = event.get_sender_id()
        return platform, user_id
    
    def _extract_b30_data(self, save_data: Dict) -> Optional[Dict]:
        """
        从存档数据中提取 Best30 数据（优化版本）
        
        Args:
            save_data: /save API 返回的存档数据
            
        Returns:
            格式化的 Best30 数据，供渲染器使用
        """
        try:
            # 预编译正则表达式（提升性能）
            import re
            html_tag_pattern = re.compile(r'<[^>]+>')
            
            def clean_nickname(value: str) -> str:
                """清理昵称中的 HTML 标签"""
                if not value or not isinstance(value, str):
                    return ""
                return html_tag_pattern.sub('', value).strip()

            def get_nickname(data_dict: Dict) -> str:
                """智能获取昵称"""
                for key in ("nickname", "name", "userName", "alias", "displayName"):
                    value = data_dict.get(key)
                    if value and isinstance(value, str):
                        cleaned = clean_nickname(value)
                        if cleaned:
                            return cleaned
                # 最后尝试 selfIntro
                self_intro = data_dict.get("selfIntro", "")
                if self_intro and isinstance(self_intro, str):
                    cleaned = clean_nickname(self_intro)
                    if cleaned:
                        return cleaned
                return ""

            def get_player_id(data_dict: Dict) -> str:
                """智能获取玩家ID"""
                for key in ("playerId", "objectId", "id", "userId", "uid"):
                    value = data_dict.get(key)
                    if value:
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                        elif isinstance(value, (int, float)):
                            return str(value)
                return ""

            # 获取 save 数据
            save_info = save_data.get("save", {})
            summary_parsed = save_info.get("summaryParsed", {})
            user_info = save_info.get("user", {})
            
            # 智能获取玩家信息
            nickname = get_nickname(summary_parsed) or get_nickname(user_info) or "Phigros Player"
            player_id = get_player_id(summary_parsed) or get_player_id(user_info) or "TapTap User"
            
            # 获取其他信息
            game_progress = save_info.get("game_progress", {})
            challenge_mode_rank = game_progress.get("challengeModeRank", 0)
            
            # 添加调试日志
            logger.info(f"游戏进度数据: {game_progress}")
            logger.info(f"提取到的段位信息: {challenge_mode_rank}")
            
            rks_data = save_data.get("rks", {})
            rks = rks_data.get("totalRks", 0) if isinstance(rks_data, dict) else (rks_data or 0)
            
            gameuser = {
                "nickname": nickname,
                "PlayerId": player_id,
                "rks": rks,
                "challengeModeRank": challenge_mode_rank,
                "avatar": user_info.get("avatar", ""),
            }
            
            # 获取成绩记录
            records_data = rks_data.get("b30Charts", []) if isinstance(rks_data, dict) else []
            
            # 快速构建 game_record 查找表
            game_record_raw = save_info.get("game_record", {})
            game_record = {}
            
            if isinstance(game_record_raw, dict):
                for song_key, records_list in game_record_raw.items():
                    if isinstance(records_list, list):
                        song_name = song_key.split(".")[0] if "." in song_key else song_key
                        for record_item in records_list:
                            if isinstance(record_item, dict):
                                diff = record_item.get("difficulty", "IN")
                                game_record[f"{song_name}.{diff}"] = record_item
            
            # 批量处理成绩记录（使用列表推导式提升性能）
            scored_records = []
            for record in records_data:
                song_id = record.get("songId", "")
                song_name = song_id.split(".")[0] if "." in song_id else song_id
                difficulty = record.get("difficulty", "IN")
                
                # 查找完整成绩数据
                full_record = game_record.get(f"{song_name}.{difficulty}")
                
                if isinstance(full_record, dict):
                    scored_records.append({
                        "song": song_name,
                        "song_id": song_id,
                        "artist": "",
                        "difficulty": difficulty,
                        "score": full_record.get("score", 0),
                        "acc": full_record.get("accuracy", 0),
                        "rks": record.get("rks", 0),
                        "fc": full_record.get("is_full_combo", False),
                        "illustration_url": f"https://somnia.xtower.site/illustrationLowRes/{song_name}.png"
                    })
                else:
                    scored_records.append({
                        "song": song_name,
                        "song_id": song_id,
                        "artist": "",
                        "difficulty": difficulty,
                        "score": 0,
                        "acc": 0,
                        "rks": record.get("rks", 0),
                        "fc": False,
                        "illustration_url": f"https://somnia.xtower.site/illustrationLowRes/{song_name}.png"
                    })
            
            # 按 RKS 排序并取前30
            scored_records.sort(key=lambda x: x["rks"], reverse=True)
            
            logger.info(f"✅ Best30 提取完成: {len(scored_records)} 条记录, 玩家: {nickname}, RKS: {rks:.4f}")
            
            return {
                "gameuser": gameuser,
                "records": scored_records[:30]
            }
            
        except Exception as e:
            logger.error(f"提取 Best30 数据失败: {e}")
            return None

    # ==================== 命令: 监控指标 ====================
    @filter.command("phi_metrics")
    async def show_metrics(self, event: AstrMessageEvent):
        """
        显示 API 监控指标
        用法: /phi_metrics
        """
        try:
            # 获取监控指标
            metrics = await self.api_monitor.get_metrics()
            
            if not metrics:
                yield event.plain_result("📊 暂无监控数据")
                return
            
            # 构建响应消息
            msg_parts = ["📊 API 监控指标\n\n"]
            
            # 总体指标
            overall = metrics.pop("overall", {})
            if overall:
                msg_parts.append("🎯 总体指标:\n")
                msg_parts.append(f"   成功率: {overall['success_rate']}%\n")
                msg_parts.append(f"   平均耗时: {overall['avg_duration']}s\n")
                msg_parts.append(f"   总调用: {overall['total_calls_all_time']}\n")
                msg_parts.append(f"   总错误: {overall['total_errors_all_time']}\n\n")
            
            # 各端点指标
            if metrics:
                msg_parts.append("📈 各端点指标:\n")
                for endpoint, data in metrics.items():
                    msg_parts.append(f"   🔗 {endpoint}:\n")
                    msg_parts.append(f"     成功率: {data['success_rate']}%\n")
                    msg_parts.append(f"     平均耗时: {data['avg_duration']}s\n")
                    msg_parts.append(f"     调用: {data['total_calls']}\n")
                    msg_parts.append(f"     错误: {data['errors']}\n\n")
            
            yield event.plain_result("".join(msg_parts))
            
            # 同时记录到日志
            await self.api_monitor.log_metrics()
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取监控指标失败: {str(e)}")


