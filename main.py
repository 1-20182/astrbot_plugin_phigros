import aiohttp
import asyncio
import json
import hashlib
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger

# 导入渲染器
try:
    from .renderer import PhigrosRenderer
    RENDERER_AVAILABLE = True
except ImportError:
    RENDERER_AVAILABLE = False
    logger.warning("渲染器未加载，图片功能不可用")

# 导入扫码登录模块 (API 版本)
try:
    from .taptap_login_api import TapTapLoginManagerAPI, LoginStatus, LoginResult
    API_LOGIN_AVAILABLE = True
except ImportError:
    API_LOGIN_AVAILABLE = False
    logger.warning("API 扫码登录模块未加载")

BASE_URL = "https://r0semi.xtower.site/api/v1/open"
DEFAULT_API_TOKEN = ""


class UserDataManager:
    """用户数据管理器 - 保存和读取用户绑定的 sessionToken"""

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


def sanitize_filename(name: str) -> str:
    """清理文件名，防止路径穿越攻击"""
    # 移除路径分隔符和危险字符
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 限制长度
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    # 如果为空，使用默认值
    if not sanitized:
        sanitized = "unnamed"
    return sanitized


@register("astrbot_plugin_phigros", "Assistant", "Phigros 音游数据查询插件", "1.0.0")
class PhigrosPlugin(Star):
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

        # 设置 HTTP 请求超时
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

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

        # 初始化渲染器
        if RENDERER_AVAILABLE and self.enable_renderer:
            try:
                # 解析曲绘路径
                illust_path = Path(__file__).parent / self.illustration_path.replace("./", "")
                self.renderer = PhigrosRenderer(
                    cache_dir=str(self.output_dir / "cache"),
                    illustration_path=str(illust_path),
                    image_quality=self.image_quality
                )
                await self.renderer.initialize()
                logger.info("渲染器初始化成功")
            except Exception as e:
                logger.error(f"渲染器初始化失败: {e}")
                self.renderer = None

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
        self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发起 HTTP 请求"""
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

                # 成功响应，解析 JSON
                try:
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise Exception(f"响应格式错误: 期望 dict，实际为 {type(data).__name__}")
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
            from astrbot.api.message_components import Image
            yield event.chain_result([Image(file=output_path)])
            
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            yield event.plain_result(f"❌ 图片渲染失败: {str(e)}")

    def _get_user_id(self, event: AstrMessageEvent) -> tuple:
        """获取用户平台标识和ID"""
        platform = event.get_platform_name()
        user_id = event.get_sender_id()
        return platform, user_id

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
            if qr_path.exists():
                from astrbot.api.message_components import Image
                yield event.chain_result([
                    Plain("📱 请使用 TapTap APP 扫描下方二维码登录:\n"),
                    Image(file=str(qr_path)),
                    Plain("⏰ 二维码有效期 2 分钟，请在手机上确认登录...")
                ])
            else:
                yield event.plain_result("❌ 二维码文件未生成，请检查日志")
                return

            # 等待扫码
            yield event.plain_result("⏳ 等待扫码...")

            result: LoginResult = await login_manager.wait_for_scan(timeout=120)

            if result.success:
                session_token = result.session_token

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

    # ==================== 命令: 获取 Best30 ====================
    @filter.command("phi_b30")
    async def get_best30(self, event: AstrMessageEvent, session_token: str = None, taptap_version: str = None):
        """
        获取 Best 30 成绩图
        用法: /phi_b30 [sessionToken] [taptapVersion]
        示例: /phi_b30 或 /phi_b30 your_token cn
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
            
            yield event.plain_result("⏳ 正在获取 Best30 数据...")
            
            data = await self._make_request(
                method="POST",
                endpoint="/save",
                params={"calculate_rks": "true"},
                json_data={"sessionToken": session_token, "taptapVersion": taptap_version},
            )

            # 使用 Best30 渲染
            async for result in self._render_and_send(
                event, 
                self.renderer.render_best30 if self.renderer else None,
                data, 
                f"b30_{session_token[:8]}.png"
            ):
                yield result

        except Exception as e:
            yield event.plain_result(f"❌ 获取 Best30 失败: {str(e)}")

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
    async def get_by_rank(self, event: AstrMessageEvent, start: int, end: Optional[int] = None):
        """
        按排名区间查询玩家
        用法: /phi_rank <start> [end]
        示例: /phi_rank 1 10 或 /phi_rank 100
        """
        try:
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

    # ==================== 命令: 新曲速递 ====================
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
                endpoint="/open/song-updates",
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
4. /phi_b30 [sessionToken] [taptapVersion]
   获取 Best 30 成绩图（带曲绘）⭐推荐
   示例: /phi_b30 或 /phi_b30 your_token cn
   💡 已绑定账号可直接使用 /phi_b30

5. /phi_save [sessionToken] [taptapVersion]
   获取用户存档数据（带曲绘图片）
   示例: /phi_save 或 /phi_save your_token cn
   💡 已绑定账号可直接使用 /phi_save

6. /phi_rks_history [sessionToken] [limit]
   查询 RKS 历史变化
   示例: /phi_rks_history 或 /phi_rks_history your_token 10
   💡 已绑定账号可直接使用 /phi_rks_history

7. /phi_leaderboard
   获取 RKS 排行榜 Top（带图片）

8. /phi_rank <start> [end]
   按排名区间查询玩家
   示例: /phi_rank 1 10

9. /phi_search <关键词> [limit]
   搜索曲目信息（带曲绘图片）
   示例: /phi_search Originally 5

10. /phi_updates [count]
    获取新曲速递
    示例: /phi_updates 3

11. /phi_help
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
