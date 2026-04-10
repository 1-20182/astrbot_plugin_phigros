"""
🔐 认证相关命令模块

包含用户绑定、解绑、扫码登录等认证相关命令
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain, Image

from ..core.exceptions import PhigrosAPIError, AuthError


class AuthCommands:
    """
    认证命令处理器
    """

    def __init__(self, plugin):
        self.plugin = plugin

    @filter.command("phi_bind")
    async def bind_user(self, event: AstrMessageEvent, session_token: str, taptap_version: str = "cn"):
        """
        绑定 Phigros 账号（保存 sessionToken）
        用法: /phi_bind <sessionToken> [taptapVersion]
        示例: /phi_bind uhrmqs8v0mmn0ikzxqgozrctr cn
        """
        try:
            platform, user_id = self.plugin._get_user_id(event)
            
            # 验证 token 是否有效
            test_data = await self.plugin.api_client.get_save(
                session_token=session_token,
                taptap_version=taptap_version,
                calculate_rks=True
            )
            
            # 保存用户数据
            await self.plugin.user_data.bind_user(platform, user_id, session_token, taptap_version)
            
            # 获取用户存档摘要
            summary = test_data.get("summary", {})
            rks = summary.get("rks", "N/A")
            
            yield event.plain_result(
                f"✅ 绑定成功！\n"
                f"📊 当前 RKS: {rks}\n"
                f"🎮 版本: {taptap_version}\n"
                f"💡 现在可以直接使用 /phi_save 和 /phi_rks_history 查询了~"
            )
            
        except PhigrosAPIError as e:
            yield event.plain_result(f"❌ 绑定失败: {str(e)}\n请检查 sessionToken 是否正确")
        except Exception as e:
            yield event.plain_result(f"❌ 绑定失败: {str(e)}\n请检查 sessionToken 是否正确")

    @filter.command("phi_qrlogin")
    async def qr_login(self, event: AstrMessageEvent, taptap_version: str = "cn"):
        """
        使用 TapTap 扫码登录（自动获取 sessionToken）
        用法: /phi_qrlogin [taptapVersion]
        示例: /phi_qrlogin cn
        """
        from ..taptap_login_api import TapTapLoginManagerAPI, LoginStatus, LoginResult

        if not self.plugin.API_LOGIN_AVAILABLE:
            yield event.plain_result(
                "❌ 扫码登录功能不可用\n"
                "💡 请检查插件是否完整安装"
            )
            return

        yield event.plain_result("⏳ 正在获取二维码，请稍候...")

        try:
            # 使用 API 版本的登录管理器
            login_manager = TapTapLoginManagerAPI(
                base_url=self.plugin.base_url,
                api_token=self.plugin.api_token or "",
                output_dir=self.plugin.output_dir,
                session=self.plugin.session
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

            # 发送二维码图片和登录提示
            qr_path = self.plugin.output_dir / "taptap_qr.png"

            if qr_path.exists():
                try:
                    # 方法1: 使用 fromFileSystem
                    from astrbot.api.message_components import Image
                    abs_path = qr_path.resolve()

                    yield event.chain_result([
                        Plain("📱 请使用 TapTap APP 扫描二维码登录\n"),
                        Image.fromFileSystem(str(abs_path)),
                        Plain("\n🌐 或访问链接: https://lilith.xtower.site/\n"
                              "⏰ 二维码有效期 2 分钟\n"
                              "⏳ 等待扫码中...")
                    ])
                except Exception as e1:
                    try:
                        # 方法2: 使用 base64 发送
                        import base64
                        with open(qr_path, 'rb') as f:
                            img_base64 = base64.b64encode(f.read()).decode()
                        
                        yield event.chain_result([
                            Plain("📱 请使用 TapTap APP 扫描二维码登录\n"),
                            Image.fromBase64(img_base64),
                            Plain("\n🌐 或访问链接: https://lilith.xtower.site/\n"
                                  "⏰ 二维码有效期 2 分钟\n"
                                  "⏳ 等待扫码中...")
                        ])
                    except Exception as e2:
                        # 方法3: 只发送文字提示
                        yield event.plain_result(
                            f"📱 请使用 TapTap APP 扫描二维码登录\n"
                            f"🌐 访问链接: https://lilith.xtower.site/\n"
                            f"⏰ 二维码有效期 2 分钟\n"
                            f"⏳ 等待扫码中..."
                        )
            else:
                yield event.plain_result(
                    f"📱 请使用 TapTap APP 扫描二维码登录\n"
                    f"🌐 访问链接: https://lilith.xtower.site/\n"
                    f"⏰ 二维码有效期 2 分钟\n"
                    f"⏳ 等待扫码中..."
                )

            # 等待扫码
            result: LoginResult = await login_manager.wait_for_scan(timeout=120)

            if result.success:
                session_token = result.session_token

                if not session_token:
                    yield event.plain_result("❌ 登录成功但未获取到 sessionToken，请重试")
                    return

                # 自动绑定
                platform, user_id = self.plugin._get_user_id(event)
                await self.plugin.user_data.bind_user(platform, user_id, session_token, taptap_version)

                # 验证 token 并获取 RKS
                try:
                    test_data = await self.plugin.api_client.get_save(
                        session_token=session_token,
                        taptap_version=taptap_version,
                        calculate_rks=True
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
        finally:
            # 清理资源
            try:
                await login_manager.terminate()
            except Exception as e:
                logger.warning(f"清理登录管理器资源时出错: {e}")

    @filter.command("phi_unbind")
    async def unbind_user(self, event: AstrMessageEvent):
        """
        解绑 Phigros 账号
        用法: /phi_unbind
        """
        platform, user_id = self.plugin._get_user_id(event)
        
        if await self.plugin.user_data.unbind_user(platform, user_id):
            yield event.plain_result("✅ 已解绑 Phigros 账号")
        else:
            yield event.plain_result("❌ 你还没有绑定账号哦~")
