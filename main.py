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
from astrbot.api.message_components import Plain, Image
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger

# 导入配置
from .config import (
    BASE_URL, DEFAULT_API_TOKEN,
    HTTP_TIMEOUT, HTTP_CONNECT_TIMEOUT, HTTP_SOCK_READ_TIMEOUT,
    HTTP_POOL_SIZE, HTTP_POOL_PER_HOST,
    DEFAULT_ILLUSTRATION_PATH, DEFAULT_TAPTAP_VERSION,
    DEFAULT_SEARCH_LIMIT, DEFAULT_HISTORY_LIMIT,
    CACHE_TTL, QR_LOGIN_TIMEOUT
)

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


class UserDataManager:
    """
    👤 用户数据管理器
    
    帮你保管 sessionToken，绑定一次，永久免输！
    数据存在本地，安全又可靠~ 🔒
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_file = data_dir / "user_data.json"
        self._data: Dict[str, Dict[str, str]] = {}
        self._lock = None  # 异步锁，在 initialize 中初始化
        self._load_data()

    async def initialize(self):
        """初始化异步锁"""
        self._lock = asyncio.Lock()

    def _load_data(self):
        """从文件加载用户数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.info(f"已加载 {len(self._data)} 个用户的数据")
            except Exception as e:
                logger.error(f"加载用户数据失败: {e}")
                self._data = {}
        else:
            self._data = {}

    def _save_data(self):
        """保存用户数据到文件"""
        try:
            # 确保目录存在
            self.data_dir.mkdir(parents=True, exist_ok=True)
            # 设置文件权限为仅所有者可读写 (Unix/Linux)
            import os
            if os.name != 'nt':  # 非 Windows 系统
                import stat
                old_umask = os.umask(0o077)
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                # 设置文件权限
                if os.name != 'nt':
                    os.chmod(self.data_file, stat.S_IRUSR | stat.S_IWUSR)
            finally:
                if os.name != 'nt':
                    os.umask(old_umask)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")

    def _encrypt_token(self, token: str) -> str:
        """对 token 进行简单混淆（非加密，仅增加读取难度）"""
        # 使用简单的 base64 编码 + 前缀混淆
        import base64
        encoded = base64.b64encode(token.encode()).decode()
        return f"enc:{encoded}"

    def _decrypt_token(self, encrypted: str) -> str:
        """解密 token"""
        import base64
        if encrypted.startswith("enc:"):
            encoded = encrypted[4:]
            return base64.b64decode(encoded.encode()).decode()
        return encrypted  # 兼容旧数据

    async def bind_user(self, platform: str, user_id: str, session_token: str, taptap_version: str = "cn") -> bool:
        """
        绑定用户数据

        Args:
            platform: 平台标识 (如 qq, wechat 等)
            user_id: 用户ID
            session_token: Phigros sessionToken
            taptap_version: TapTap 版本 (cn/global)

        Returns:
            bool: 是否绑定成功
        """
        async with self._lock:
            key = f"{platform}:{user_id}"
            self._data[key] = {
                "session_token": self._encrypt_token(session_token),
                "taptap_version": taptap_version,
                "bind_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_data()
        return True

    async def unbind_user(self, platform: str, user_id: str) -> bool:
        """
        解绑用户数据

        Args:
            platform: 平台标识
            user_id: 用户ID

        Returns:
            bool: 是否解绑成功
        """
        async with self._lock:
            key = f"{platform}:{user_id}"
            if key in self._data:
                del self._data[key]
                self._save_data()
                return True
            return False

    def get_user_data(self, platform: str, user_id: str) -> Optional[Dict[str, str]]:
        """
        获取用户绑定的数据

        Args:
            platform: 平台标识
            user_id: 用户ID

        Returns:
            Dict 或 None: 包含 session_token 和 taptap_version 的字典
        """
        key = f"{platform}:{user_id}"
        data = self._data.get(key)
        if data:
            # 解密 token
            return {
                "session_token": self._decrypt_token(data["session_token"]),
                "taptap_version": data.get("taptap_version", "cn"),
                "bind_time": data.get("bind_time", "")
            }
        return None

    def is_user_bound(self, platform: str, user_id: str) -> bool:
        """检查用户是否已绑定"""
        key = f"{platform}:{user_id}"
        return key in self._data


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
        self.api_token: Optional[str] = None
        self.renderer: Optional[PhigrosRenderer] = None

        # 使用 StarTools 获取插件数据目录
        self.data_dir: Path = StarTools.get_data_dir("astrbot_plugin_phigros")
        self.output_dir = self.data_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化用户数据管理器
        self.user_data = UserDataManager(self.data_dir)

        # 从插件配置中读取设置
        self.plugin_config = config or {}
        logger.info(f"Phigros 插件配置: {self.plugin_config}")

    async def initialize(self):
        """插件初始化"""
        # 初始化用户数据管理器的锁
        await self.user_data.initialize()

        # 设置 HTTP 请求超时和连接池
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
        connector = aiohttp.TCPConnector(
            limit=50,  # 连接池大小
            limit_per_host=20,  # 每个主机的连接数
            enable_cleanup_closed=True,  # 清理关闭的连接
            force_close=False,  # 复用连接
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "PhigrosQueryBot/1.8.0"}
        )

        # 从插件配置中读取 API Token，如果没有则使用默认 Token
        self.api_token = self.plugin_config.get("phigros_api_token", DEFAULT_API_TOKEN)
        if self.api_token:
            logger.info("Phigros API Token 已配置")
        else:
            logger.warning("Phigros API Token 未配置，请在 WebUI 中设置")

        # 读取其他配置
        self.enable_renderer = self.plugin_config.get("enable_renderer", True)
        self.illustration_path = self.plugin_config.get("illustration_path", "./ILLUSTRATION")
        self.image_quality = self.plugin_config.get("image_quality", 95)
        self.default_taptap_version = self.plugin_config.get("default_taptap_version", "cn")
        self.default_search_limit = self.plugin_config.get("default_search_limit", 5)
        self.default_history_limit = self.plugin_config.get("default_history_limit", 10)

        # 初始化 API 缓存（TTL 5 分钟）
        self._api_cache = SimpleCache(ttl=300)
        logger.info("🚀 API 缓存已初始化")

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
            logger.info("✅ PhiStyleRenderer 创建成功")
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
                renderer_mode = self.plugin_config.get("renderer_mode", "auto")
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
            self.enable_auto_update = self.plugin_config.get("enable_auto_update_illustration", True)
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
            proxy = self.plugin_config.get("illustration_update_proxy", "")
            
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
        if self.session:
            await self.session.close()
        if self.renderer:
            await self.renderer.terminate()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["X-OpenApi-Token"] = self.api_token
        return headers

    async def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None,
        return_raw: bool = False
    ) -> Any:
        """发起 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: URL 参数
            json_data: JSON 请求体
            return_raw: 是否返回原始响应内容（用于图片等非 JSON 响应）
        """
        if not self.session:
            raise Exception("HTTP 会话未初始化")

        url = f"{BASE_URL}{endpoint}"
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                params=params,
                json=json_data,
            ) as response:
                # 首先检查响应状态
                if response.status != 200:
                    # 尝试读取错误信息
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("detail", f"请求失败，状态码: {response.status}")
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        # 非 JSON 响应，读取文本
                        error_text = await response.text()
                        error_msg = f"请求失败，状态码: {response.status}，响应: {error_text[:200]}"
                    raise Exception(error_msg)

                # 如果请求原始内容，直接返回文本
                if return_raw:
                    return await response.text()

                # 成功响应，解析 JSON
                try:
                    data = await response.json()
                    return data
                except json.JSONDecodeError as e:
                    raise Exception(f"解析响应数据失败: {str(e)}")
        except aiohttp.ClientError as e:
            raise Exception(f"网络请求错误: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("请求超时，请稍后重试")

    async def _render_and_send(
        self, event: AstrMessageEvent, 
        render_func, 
        data: Dict[str, Any], 
        filename: str,
        *args
    ):
        """渲染图片并发送"""
        if not self.renderer:
            yield event.plain_result("❌ 图片渲染功能不可用")
            return
        
        try:
            output_path = str(self.output_dir / filename)
            await render_func(data, output_path, *args)
            
            # 发送图片
            yield event.chain_result([Image(file=output_path)])
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
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

    # ==================== 命令: 绑定用户数据 ====================
    @filter.command("phi_bind")
    async def bind_user(self, event: AstrMessageEvent, session_token: str, taptap_version: str = "cn"):
        """
        绑定 Phigros 账号（保存 sessionToken）
        用法: /phi_bind <sessionToken> [taptapVersion]
        示例: /phi_bind uhrmqs8v0mmn0ikzxqgozrctr cn
        """
        try:
            platform, user_id = self._get_user_id(event)
            
            # 验证 token 是否有效
            test_data = await self._make_request(
                method="POST",
                endpoint="/save",
                params={"calculate_rks": "true"},
                json_data={"sessionToken": session_token, "taptapVersion": taptap_version},
            )
            
            # 保存用户数据
            await self.user_data.bind_user(platform, user_id, session_token, taptap_version)
            
            # 获取用户存档摘要
            summary = test_data.get("summary", {})
            rks = summary.get("rks", "N/A")
            
            yield event.plain_result(
                f"✅ 绑定成功！\n"
                f"📊 当前 RKS: {rks}\n"
                f"🎮 版本: {taptap_version}\n"
                f"💡 现在可以直接使用 /phi_save 和 /phi_rks_history 查询了~"
            )
            
        except Exception as e:
            yield event.plain_result(f"❌ 绑定失败: {str(e)}\n请检查 sessionToken 是否正确")

    # ==================== 命令: TapTap 扫码登录 ====================
    @filter.command("phi_qrlogin")
    async def qr_login(self, event: AstrMessageEvent, taptap_version: str = "cn"):
        """
        使用 TapTap 扫码登录（自动获取 sessionToken）
        用法: /phi_qrlogin [taptapVersion]
        示例: /phi_qrlogin cn
        """
        if not API_LOGIN_AVAILABLE:
            yield event.plain_result(
                "❌ 扫码登录功能不可用\n"
                "💡 请检查插件是否完整安装"
            )
            return

        yield event.plain_result("⏳ 正在获取二维码，请稍候...")

        try:
            # 使用 API 版本的登录管理器
            login_manager = TapTapLoginManagerAPI(
                base_url=BASE_URL,
                api_token=self.api_token or "",
                output_dir=self.output_dir,
                session=self.session
            )

            # 生成二维码
            qr_base64 = await login_manager.generate_qr_code(taptap_version)
            logger.info(f"🔍 二维码生成返回: {'成功' if qr_base64 else '失败'}")
            logger.info(f"🔍 登录管理器二维码路径: {login_manager.qr_code_path}")
            logger.info(f"🔍 本地二维码路径: {self.output_dir / 'taptap_qr.png'}")

            if not qr_base64:
                yield event.plain_result(
                    "❌ 获取二维码失败\n"
                    "💡 可能原因：\n"
                    "1. API Token 无效或未配置\n"
                    "2. 网络连接问题\n"
                    "3. 请检查日志了解详情\n\n"
                    "建议使用 /phi_bind <token> 手动绑定"
                )
                return

            # 发送二维码
            qr_path = self.output_dir / "taptap_qr.png"
            logger.info(f"🔍 检查二维码文件: {qr_path}, 存在: {qr_path.exists()}")
            if qr_path.exists():
                logger.info(f"🔍 文件大小: {qr_path.stat().st_size} bytes")
                
                # 先发送文字提示
                yield event.plain_result("📱 请使用 TapTap APP 扫描下方二维码登录:")
                
                try:
                    # 尝试发送图片（兼容不同平台）
                    logger.info("🔍 尝试发送图片...")
                    yield event.chain_result([Image(file=str(qr_path))])
                    logger.info("� 图片发送完成")
                    
                    # 再发送剩余文字
                    yield event.plain_result("⏰ 二维码有效期 2 分钟，请在手机上确认登录...\n⏳ 等待扫码中...")
                except Exception as e:
                    logger.error(f"🔍 发送二维码图片失败: {e}")
                    import traceback
                    logger.error(f"🔍 异常详情: {traceback.format_exc()}")
                    # 如果文件方式失败，尝试使用 base64
                    try:
                        import base64
                        with open(qr_path, 'rb') as f:
                            img_base64 = base64.b64encode(f.read()).decode()
                        yield event.chain_result([Image.fromBase64(img_base64)])
                        yield event.plain_result("⏰ 二维码有效期 2 分钟，请在手机上确认登录...\n⏳ 等待扫码中...")
                    except Exception as e2:
                        logger.error(f"🔍 Base64 方式也失败: {e2}")
                        # 最后回退：只发送链接
                        yield event.plain_result(
                            f"📱 请使用 TapTap APP 扫描登录\n"
                            f"💡 如果看不到二维码，请访问:\n"
                            f"https://lilith.xtower.site/\n"
                            f"⏰ 二维码有效期 2 分钟"
                        )
            else:
                logger.error(f"🔍 二维码文件不存在: {qr_path}")
                yield event.plain_result("❌ 二维码文件未生成，请检查日志")
                return

            # 等待扫码
            logger.info("开始等待用户扫码...")
            result: LoginResult = await login_manager.wait_for_scan(timeout=120)

            if result.success:
                session_token = result.session_token
                logger.info(f"扫码登录成功，获取到 sessionToken: {session_token[:20] if session_token else 'None'}...")

                if not session_token:
                    yield event.plain_result("❌ 登录成功但未获取到 sessionToken，请重试")
                    return

                # 自动绑定
                platform, user_id = self._get_user_id(event)
                await self.user_data.bind_user(platform, user_id, session_token, taptap_version)

                # 验证 token 并获取 RKS
                try:
                    test_data = await self._make_request(
                        method="POST",
                        endpoint="/save",
                        params={"calculate_rks": "true"},
                        json_data={"sessionToken": session_token, "taptapVersion": taptap_version},
                    )
                    summary = test_data.get("summary", {})
                    rks = summary.get("rks", "N/A")

                    yield event.plain_result(
                        f"🎉 扫码登录成功！\n"
                        f"📊 当前 RKS: {rks}\n"
                        f"🎮 版本: {taptap_version}\n"
                        f"✅ 账号已自动绑定，现在可以直接使用 /phi_save 查询了~"
                    )
                except Exception as e:
                    yield event.plain_result(
                        f"✅ 扫码登录成功并已绑定！\n"
                        f"⚠️ 但验证时出错: {str(e)}\n"
                        f"💡 绑定已保存，可以直接尝试 /phi_save"
                    )
            else:
                yield event.plain_result(f"❌ {result.error_message or '登录失败'}\n请重试或使用 /phi_bind <token> 手动绑定")

        except Exception as e:
            yield event.plain_result(f"❌ 扫码登录过程出错: {str(e)}")

    # ==================== 命令: 解绑用户数据 ====================
    @filter.command("phi_unbind")
    async def unbind_user(self, event: AstrMessageEvent):
        """
        解绑 Phigros 账号
        用法: /phi_unbind
        """
        platform, user_id = self._get_user_id(event)
        
        if await self.user_data.unbind_user(platform, user_id):
            yield event.plain_result("✅ 已解绑 Phigros 账号")
        else:
            yield event.plain_result("❌ 你还没有绑定账号哦~")

    # ==================== 命令: 获取用户存档 ====================
    @filter.command("phi_save")
    async def get_save(self, event: AstrMessageEvent, session_token: str = None, taptap_version: str = None):
        """
        获取 Phigros 云存档数据
        用法: /phi_save [sessionToken] [taptapVersion]
        示例: /phi_save uhrmqs8v0mmn0ikzxqgozrctr cn
        提示: 如果已绑定账号，可以不填 sessionToken
        """
        try:
            # 如果没有提供 session_token，尝试从绑定数据获取
            if session_token is None:
                platform, user_id = self._get_user_id(event)
                user_data = self.user_data.get_user_data(platform, user_id)
                
                if user_data is None:
                    yield event.plain_result(
                        "❌ 未提供 sessionToken 且未绑定账号\n"
                        "💡 请使用 /phi_bind <token> 绑定账号\n"
                        "或直接提供 token: /phi_save <token>"
                    )
                    return
                
                session_token = user_data["session_token"]
                if taptap_version is None:
                    taptap_version = user_data.get("taptap_version", self.default_taptap_version)
            
            # 使用配置的默认值
            if taptap_version is None:
                taptap_version = self.default_taptap_version
            
            data = await self._make_request(
                method="POST",
                endpoint="/save",
                params={"calculate_rks": "true"},
                json_data={"sessionToken": session_token, "taptapVersion": taptap_version},
            )

            # 使用图片渲染
            async for result in self._render_and_send(
                event, 
                self.renderer.render_save_data if self.renderer else None,
                data, 
                f"save_{session_token[:8]}.png"
            ):
                yield result

        except Exception as e:
            yield event.plain_result(f"❌ 获取存档失败: {str(e)}")

    # ==================== 命令: 获取 Best30 (API SVG版本) ====================
    @filter.command("phi_b30")
    async def get_best30(self, event: AstrMessageEvent, session_token: str = None, taptap_version: str = None, theme: str = "black"):
        """
        获取 Best 30 成绩图（API直接生成SVG）
        用法: /phi_b30 [sessionToken] [taptapVersion] [theme]
        示例: /phi_b30 或 /phi_b30 your_token cn black
        提示: 如果已绑定账号，可以不填 sessionToken
        """
        try:
            # 如果没有提供 session_token，尝试从绑定数据获取
            if session_token is None:
                platform, user_id = self._get_user_id(event)
                user_data = self.user_data.get_user_data(platform, user_id)
                
                if user_data is None:
                    yield event.plain_result(
                        "❌ 未提供 sessionToken 且未绑定账号\n"
                        "💡 请使用 /phi_qrlogin 扫码登录\n"
                        "或使用 /phi_bind <token> 绑定账号"
                    )
                    return
                
                session_token = user_data["session_token"]
                if taptap_version is None:
                    taptap_version = user_data.get("taptap_version", self.default_taptap_version)
            
            # 使用配置的默认值
            if taptap_version is None:
                taptap_version = self.default_taptap_version
            
            # 验证主题参数
            if theme not in ["black", "white"]:
                theme = "black"
            
            yield event.plain_result("⏳ 正在查询 Best30 数据...")

            # 首先尝试使用 /save API 获取数据，然后本地渲染
            render_success = False
            output_path = self.output_dir / f"b30_{session_token[:8]}.png"

            if hasattr(self, 'renderer') and self.renderer:
                try:
                    # 调用 /save API 获取存档数据
                    save_data = await self._make_request(
                        method="POST",
                        endpoint="/save",
                        params={"calculate_rks": "true"},
                        json_data={
                            "sessionToken": session_token,
                            "taptapVersion": taptap_version
                        }
                    )

                    yield event.plain_result("🎨 正在渲染 Best30 图片...")

                    # 提取 Best30 数据
                    b30_data = self._extract_b30_data(save_data)

                    if b30_data:
                        render_success = await self.renderer.render_b30(b30_data, output_path)
                    else:
                        logger.warning("⚠️ 无法提取 Best30 数据")
                        
                except Exception as e:
                    logger.error(f"使用渲染器生成图片失败: {e}")
                    render_success = False
            
            # 如果渲染器失败，回退到 SVG 转换
            convert_success = False
            if not render_success:
                logger.info("🔄 使用 SVG 转换作为回退方案")
                # 调用 API 获取 SVG
                svg_data = await self._make_request(
                    method="POST",
                    endpoint="/image/bn",
                    params={"format": "svg"},
                    json_data={
                        "sessionToken": session_token,
                        "taptapVersion": taptap_version,
                        "n": 30,
                        "theme": theme
                    },
                    return_raw=True
                )
                
                # 保存 SVG 文件
                svg_path = self.output_dir / f"b30_{session_token[:8]}.svg"
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_data)
                
                # 将 SVG 转换为 PNG
                if SVG_CONVERTER_AVAILABLE:
                    try:
                        plugin_dir = str(Path(__file__).parent)
                        illust_path = str(Path(__file__).parent / self.illustration_path.replace("./", ""))
                        convert_success = convert_svg_to_png(
                            str(svg_path),
                            str(output_path),
                            illustration_path=illust_path,
                            plugin_dir=plugin_dir
                        )
                    except Exception as e:
                        logger.error(f"SVG 转换失败: {e}")
            
            # 发送图片或提示
            if render_success or convert_success:
                yield event.chain_result([
                    Plain(f"🎵 Best30 成绩图 ({theme}主题)\n"),
                    Image(file=str(output_path))
                ])
            else:
                # 转换失败
                yield event.plain_result(
                    f"❌ 生成 Best30 成绩图失败\n"
                    f"💡 请检查日志了解详细错误信息"
                )

        except Exception as e:
            yield event.plain_result(f"❌ 获取 Best30 失败: {str(e)}")

    # ==================== 命令: 获取 BestN 图片 (API 版本) ====================
    @filter.command("phi_bn")
    async def get_bestn_image(self, event: AstrMessageEvent, n: int = 27, theme: str = "black"):
        """
        获取 BestN 成绩图（API 直接生成）
        用法: /phi_bn [n] [theme]
        示例: /phi_bn 27 black
        参数:
          n: 成绩数量，建议 27 (默认)
          theme: 主题，black 或 white (默认 black)
        注意: 需要先绑定账号或扫码登录
        """
        try:
            # 从绑定数据获取
            platform, user_id = self._get_user_id(event)
            user_data = self.user_data.get_user_data(platform, user_id)
            
            if user_data is None:
                yield event.plain_result(
                    "❌ 未绑定账号\n"
                    "💡 请使用 /phi_qrlogin 扫码登录\n"
                    "或使用 /phi_bind <token> 绑定账号"
                )
                return
            
            session_token = user_data["session_token"]
            taptap_version = user_data.get("taptap_version", self.default_taptap_version)
            
            # 验证参数
            if n < 1 or n > 50:
                yield event.plain_result("❌ n 的范围应为 1-50")
                return
            
            if theme not in ["black", "white"]:
                theme = "black"
            
            yield event.plain_result(f"⏳ 正在生成 Best{n} 成绩图...")
            
            # 调用 API 获取 SVG（返回原始文本）
            svg_data = await self._make_request(
                method="POST",
                endpoint="/image/bn",
                params={"format": "svg"},
                json_data={
                    "sessionToken": session_token,
                    "taptapVersion": taptap_version,
                    "n": n,
                    "theme": theme
                },
                return_raw=True
            )
            
            # 保存 SVG 文件
            svg_path = self.output_dir / f"bn_{session_token[:8]}_{n}.svg"
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
            
            # 将 SVG 转换为 PNG（QQ 不支持 SVG）
            output_path = self.output_dir / f"bn_{session_token[:8]}_{n}.png"
            convert_success = False
            
            if SVG_CONVERTER_AVAILABLE:
                try:
                    # 传递曲绘路径和插件目录
                    plugin_dir = str(Path(__file__).parent)
                    illust_path = str(Path(__file__).parent / self.illustration_path.replace("./", ""))
                    convert_success = convert_svg_to_png(
                        str(svg_path),
                        str(output_path),
                        illustration_path=illust_path,
                        plugin_dir=plugin_dir
                    )
                except Exception as e:
                    logger.error(f"SVG 转换失败: {e}")
            else:
                logger.warning("SVG 转换器未加载")

            # 发送图片或提示
            if convert_success:
                yield event.chain_result([
                    Plain(f"🎵 Best{n} 成绩图 ({theme}主题)\n"),
                    Image(file=str(output_path))
                ])
            else:
                # 转换失败，提示用户 SVG 文件位置
                converter = get_converter() if SVG_CONVERTER_AVAILABLE else None
                help_text = converter.install_help() if converter else "请安装 svglib: pip install svglib reportlab"
                yield event.plain_result(
                    f"⚠️ Best{n} 成绩图已保存为 SVG 格式\n"
                    f"📁 文件位置: {svg_path}\n"
                    f"💡 {help_text}"
                )
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取 BestN 图片失败: {str(e)}")

    # ==================== 命令: 查询 RKS 历史 ====================
    @filter.command("phi_rks_history")
    async def get_rks_history(self, event: AstrMessageEvent, session_token: str = None, limit: int = None):
        """
        查询 RKS 历史变化
        用法: /phi_rks_history [sessionToken] [limit]
        示例: /phi_rks_history uhrmqs8v0mmn0ikzxqgozrctr 10
        提示: 如果已绑定账号，可以不填 sessionToken
        """
        try:
            # 如果没有提供 session_token，尝试从绑定数据获取
            if session_token is None:
                platform, user_id = self._get_user_id(event)
                user_data = self.user_data.get_user_data(platform, user_id)
                
                if user_data is None:
                    yield event.plain_result(
                        "❌ 未提供 sessionToken 且未绑定账号\n"
                        "💡 请使用 /phi_bind <token> 绑定账号\n"
                        "或直接提供 token: /phi_rks_history <token>"
                    )
                    return
                
                session_token = user_data["session_token"]
            
            # 使用配置的默认值
            if limit is None:
                limit = self.default_history_limit
            
            data = await self._make_request(
                method="POST",
                endpoint="/rks/history",
                json_data={"auth": {"sessionToken": session_token}, "limit": limit, "offset": 0},
            )

            items = data.get("items", [])
            total = data.get("total", 0)
            current_rks = data.get("currentRks", 0)
            peak_rks = data.get("peakRks", 0)

            msg_parts = ["📈 RKS 历史记录\n"]
            msg_parts.append(f"📊 当前 RKS: {current_rks}\n")
            msg_parts.append(f"🏆 最高 RKS: {peak_rks}\n")
            msg_parts.append(f"📝 总记录数: {total}\n\n")

            if items:
                msg_parts.append("最近变化:\n")
                for item in items[:limit]:
                    rks = item.get("rks", 0)
                    jump = item.get("rksJump", 0)
                    created = item.get("createdAt", "")[:10]
                    jump_str = f"(+{jump})" if jump > 0 else f"({jump})" if jump < 0 else ""
                    msg_parts.append(f"  • {created}: {rks:.4f} {jump_str}\n")
            else:
                msg_parts.append("暂无历史记录")

            yield event.plain_result("".join(msg_parts))

        except Exception as e:
            yield event.plain_result(f"❌ 查询 RKS 历史失败: {str(e)}")

    # ==================== 命令: 获取排行榜 ====================
    @filter.command("phi_leaderboard")
    async def get_leaderboard(self, event: AstrMessageEvent):
        """
        获取 RKS 排行榜 Top 数据
        用法: /phi_leaderboard
        """
        try:
            data = await self._make_request(
                method="GET",
                endpoint="/leaderboard/rks/top",
            )

            # 使用图片渲染
            async for result in self._render_and_send(
                event,
                self.renderer.render_leaderboard if self.renderer else None,
                data,
                "leaderboard.png"
            ):
                yield result

        except Exception as e:
            yield event.plain_result(f"❌ 获取排行榜失败: {str(e)}")

    # ==================== 命令: 按排名区间查询 ====================
    @filter.command("phi_rank")
    async def get_by_rank(self, event: AstrMessageEvent, start: int = None, end: Optional[int] = None):
        """
        按排名区间查询玩家
        用法: /phi_rank <start> [end]
        示例: /phi_rank 1 10 或 /phi_rank 100
        """
        try:
            # 如果没有提供start，默认查询前10名
            if start is None:
                start = 1
                
            params = {"start": start}
            if end:
                params["end"] = end
            else:
                params["count"] = 10

            data = await self._make_request(
                method="GET",
                endpoint="/leaderboard/rks/by-rank",
                params=params,
            )

            items = data.get("items", [])

            msg_parts = [f"📊 排名 {start}-{end or start+9} 的玩家\n\n"]

            for item in items:
                rank = item.get("rank", 0)
                alias = item.get("alias", "未知")
                score = item.get("score", 0)
                msg_parts.append(f"  {rank}. {alias} - RKS: {score:.4f}\n")

            yield event.plain_result("".join(msg_parts))

        except Exception as e:
            yield event.plain_result(f"❌ 查询排名失败: {str(e)}")

    # ==================== 命令: 歌曲搜索 ====================
    @filter.command("phi_search")
    async def search_songs(self, event: AstrMessageEvent, keyword: str, limit: int = None):
        """
        搜索 Phigros 曲目
        用法: /phi_search <关键词> [limit]
        示例: /phi_search Originally 5
        """
        try:
            # 使用配置的默认值
            if limit is None:
                limit = self.default_search_limit
            
            data = await self._make_request(
                method="GET",
                endpoint="/songs/search",
                params={"q": keyword, "limit": limit},
            )

            items = data.get("items", [])
            
            if not items:
                yield event.plain_result(f"❌ 未找到与 '{keyword}' 相关的曲目")
                return

            # 如果有曲绘，渲染第一张歌曲的详情
            if self.renderer and items:
                first_song = items[0]
                safe_keyword = sanitize_filename(keyword)
                async for result in self._render_and_send(
                    event,
                    self.renderer.render_song_detail,
                    first_song,
                    f"song_{safe_keyword}.png"
                ):
                    yield result
            else:
                # 文本输出
                total = data.get("total", 0)
                msg_parts = [f"🎵 搜索 '{keyword}' 找到 {total} 首曲目\n\n"]

                for item in items[:limit]:
                    name = item.get("name", "未知")
                    composer = item.get("composer", "未知")
                    constants = item.get("chartConstants", {})

                    msg_parts.append(f"📀 {name}\n")
                    msg_parts.append(f"   作曲: {composer}\n")
                    msg_parts.append(f"   定数: ")

                    for diff in ["ez", "hd", "in", "at"]:
                        val = constants.get(diff)
                        if val is not None:
                            msg_parts.append(f"{diff.upper()}:{val} ")
                    msg_parts.append("\n\n")

                yield event.plain_result("".join(msg_parts))

        except Exception as e:
            yield event.plain_result(f"❌ 搜索曲目失败: {str(e)}")

    # ==================== 命令: 获取单曲成绩图 ====================
    @filter.command("phi_song")
    async def get_song_image(self, event: AstrMessageEvent, song_id: str):
        """
        获取指定歌曲的成绩图
        用法: /phi_song <歌曲ID>
        示例: /phi_song 曲名.曲师
        提示: 使用 /phi_search 搜索歌曲获取准确的歌曲ID
        注意: 需要先绑定账号或扫码登录
        """
        try:
            # 从绑定数据获取
            platform, user_id = self._get_user_id(event)
            user_data = self.user_data.get_user_data(platform, user_id)
            
            if user_data is None:
                yield event.plain_result(
                    "❌ 未绑定账号\n"
                    "💡 请使用 /phi_qrlogin 扫码登录\n"
                    "或使用 /phi_bind <token> 绑定账号"
                )
                return
            
            session_token = user_data["session_token"]
            taptap_version = user_data.get("taptap_version", self.default_taptap_version)
            
            if not song_id:
                yield event.plain_result(
                    "❌ 请提供歌曲ID\n"
                    "💡 使用 /phi_search <关键词> 搜索歌曲获取ID\n"
                    "示例: /phi_song 曲名.曲师"
                )
                return
            
            yield event.plain_result(f"⏳ 正在生成歌曲成绩图...")
            
            # 调用 API 获取 SVG（返回原始文本）
            svg_data = await self._make_request(
                method="POST",
                endpoint="/image/song",
                params={"format": "svg"},
                json_data={
                    "sessionToken": session_token,
                    "taptapVersion": taptap_version,
                    "song": song_id
                },
                return_raw=True
            )
            
            # 尝试解析为 JSON（检查是否是候选列表）
            try:
                json_data = json.loads(svg_data)
                if isinstance(json_data, dict) and "candidates" in json_data:
                    candidates = json_data.get("candidates", [])
                    if candidates:
                        msg_parts = ["🎵 找到多个匹配的歌曲，请使用准确的ID:\n\n"]
                        for i, candidate in enumerate(candidates[:10], 1):
                            cid = candidate.get("id", "未知")
                            name = candidate.get("name", "未知")
                            msg_parts.append(f"{i}. {name}\n")
                            msg_parts.append(f"   ID: {cid}\n\n")
                        yield event.plain_result("".join(msg_parts))
                    else:
                        yield event.plain_result("❌ 未找到匹配的歌曲")
                    return
            except json.JSONDecodeError:
                # 不是 JSON，说明是 SVG 数据，继续处理
                pass
            
            # 保存 SVG 文件
            safe_song_id = song_id.replace(".", "_").replace("/", "_")[:50]
            svg_path = self.output_dir / f"song_{safe_song_id}.svg"
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
            
            # 将 SVG 转换为 PNG（QQ 不支持 SVG）
            output_path = self.output_dir / f"song_{safe_song_id}.png"
            convert_success = False
            
            if SVG_CONVERTER_AVAILABLE:
                try:
                    # 传递曲绘路径和插件目录
                    plugin_dir = str(Path(__file__).parent)
                    illust_path = str(Path(__file__).parent / self.illustration_path.replace("./", ""))
                    convert_success = convert_svg_to_png(
                        str(svg_path),
                        str(output_path),
                        illustration_path=illust_path,
                        plugin_dir=plugin_dir
                    )
                except Exception as e:
                    logger.error(f"SVG 转换失败: {e}")
            else:
                logger.warning("SVG 转换器未加载")

            # 发送图片或提示
            if convert_success:
                yield event.chain_result([
                    Plain(f"🎵 歌曲成绩图\n"),
                    Image(file=str(output_path))
                ])
            else:
                # 转换失败，提示用户 SVG 文件位置
                converter = get_converter() if SVG_CONVERTER_AVAILABLE else None
                help_text = converter.install_help() if converter else "请安装 svglib: pip install svglib reportlab"
                yield event.plain_result(
                    f"⚠️ 歌曲成绩图已保存为 SVG 格式\n"
                    f"📁 文件位置: {svg_path}\n"
                    f"💡 {help_text}"
                )
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取歌曲成绩图失败: {str(e)}")

    # ==================== 命令: 获取新曲速递 ====================
    @filter.command("phi_updates")
    async def get_updates(self, event: AstrMessageEvent, count: int = 3):
        """
        获取 Phigros 新曲速递
        用法: /phi_updates [count]
        示例: /phi_updates 3
        """
        try:
            data = await self._make_request(
                method="GET",
                endpoint="/song-updates",
            )

            if not isinstance(data, list):
                yield event.plain_result("❌ 获取新曲速递失败: 响应格式错误")
                return

            msg_parts = ["🆕 Phigros 新曲速递\n\n"]

            for update in data[:count]:
                version = update.get("version", "未知版本")
                update_date = update.get("updateDate", "")[:10]
                content = update.get("content", "")

                msg_parts.append(f"📦 版本 {version} ({update_date})\n")
                lines = content.split("\n")
                for line in lines[:20]:
                    line = line.strip()
                    if line and not line.startswith("---"):
                        line = line.replace("# ", "• ").replace("## ", "  ")
                        line = line.replace("**", "").replace("*", "")
                        if line:
                            msg_parts.append(f"{line}\n")
                msg_parts.append("\n")

            yield event.plain_result("".join(msg_parts))

        except Exception as e:
            yield event.plain_result(f"❌ 获取新曲速递失败: {str(e)}")

    # ==================== 命令: 帮助 ====================
    @filter.command("phi_help")
    async def show_help(self, event: AstrMessageEvent):
        """
        显示 Phigros 插件帮助信息
        用法: /phi_help
        """
        help_text = """🎮 Phigros Query 插件帮助

📋 可用命令:

【账号绑定】
1. /phi_qrlogin [taptapVersion]
   TapTap 扫码登录（自动获取 token）⭐推荐
   示例: /phi_qrlogin cn

2. /phi_bind <sessionToken> [taptapVersion]
   手动绑定 Phigros 账号
   示例: /phi_bind your_token cn

3. /phi_unbind
   解绑 Phigros 账号

【数据查询】
4. /phi_b30 [sessionToken] [taptapVersion] [theme]
   获取 Best 30 成绩图（API直接生成SVG）⭐推荐
   示例: /phi_b30 或 /phi_b30 your_token cn black
   参数: theme=black/white (默认 black)
   💡 已绑定账号可直接使用 /phi_b30

5. /phi_bn [n] [theme]
   获取 BestN 成绩图（API直接生成SVG）🆕
   示例: /phi_bn 27 black
   参数: n=成绩数量(1-50), theme=black/white
   💡 已绑定账号可直接使用 /phi_bn

6. /phi_song <歌曲ID>
   获取单曲成绩图（API直接生成）🆕
   示例: /phi_song 曲名.曲师
   💡 先用 /phi_search 搜索获取准确ID

7. /phi_save [sessionToken] [taptapVersion]
   获取用户存档数据（带曲绘图片）
   示例: /phi_save 或 /phi_save your_token cn
   💡 已绑定账号可直接使用 /phi_save

8. /phi_rks_history [sessionToken] [limit]
   查询 RKS 历史变化
   示例: /phi_rks_history 或 /phi_rks_history your_token 10
   💡 已绑定账号可直接使用 /phi_rks_history

9. /phi_leaderboard
   获取 RKS 排行榜 Top（带图片）

10. /phi_rank <start> [end]
    按排名区间查询玩家
    示例: /phi_rank 1 10

11. /phi_search <关键词> [limit]
    搜索曲目信息（带曲绘图片）
    示例: /phi_search Originally 5

12. /phi_updates [count]
    获取新曲速递
    示例: /phi_updates 3

13. /phi_update_illust [proxy]
    手动更新曲绘（从 GitHub 自动下载）
    示例: /phi_update_illust
    示例: /phi_update_illust http://127.0.0.1:7890

14. /phi_help
    显示此帮助信息

💡 使用提示:
• 首次使用建议先绑定账号: /phi_bind <token>
• 绑定后 /phi_save 和 /phi_rks_history 可直接使用
• sessionToken 需要从 TapTap 获取
• taptapVersion 可选值: cn (国服) 或 global (国际版)

⚙️ 配置项（在插件配置中设置）:
• phigros_api_token - API Token
• enable_renderer - 是否启用图片渲染
• illustration_path - 曲绘文件路径
• image_quality - 图片质量 (1-100)
• default_taptap_version - 默认 TapTap 版本
• default_search_limit - 默认搜索数量
• default_history_limit - 默认历史记录数量
"""
        yield event.plain_result(help_text)

    @filter.command("phi_update_illust")
    async def phi_update_illust(self, event: AstrMessageEvent, proxy: str = ""):
        """手动更新曲绘"""
        if not ILLUSTRATION_UPDATER_AVAILABLE:
            yield event.plain_result("❌ 曲绘更新器未加载，无法更新")
            return

        yield event.plain_result("🎨 开始检查曲绘更新...")

        try:
            plugin_dir = Path(__file__).parent
            illust_path = plugin_dir / self.illustration_path.replace("./", "")

            # 使用提供的代理或配置中的代理
            proxy_url = proxy if proxy else self.plugin_config.get("illustration_update_proxy", "")

            success, fail, status = await auto_update_illustrations(
                plugin_dir=plugin_dir,
                illustration_path=illust_path,
                proxy=proxy_url if proxy_url else None
            )

            if success > 0:
                result = f"🎉 曲绘更新完成！\n✅ 成功下载: {success} 个\n❌ 失败: {fail} 个"
                if status:
                    result += f"\n📋 {status}"
            elif "跳过检查" in status:
                result = f"⏭️ {status}\n💡 使用 `/phi_update_illust force` 强制更新"
            else:
                result = f"ℹ️ {status}"

            yield event.plain_result(result)

        except Exception as e:
            yield event.plain_result(f"❌ 更新失败: {e}")
