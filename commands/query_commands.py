"""
🔍 查询相关命令模块

包含存档查询、Best30、RKS历史等查询相关命令
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain, Image

from ..core.exceptions import PhigrosAPIError, NetworkError


class QueryCommands:
    """
    查询命令处理器
    """

    def __init__(self, plugin):
        self.plugin = plugin

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
                platform, user_id = self.plugin._get_user_id(event)
                user_data = self.plugin.user_data.get_user_data(platform, user_id)
                
                if user_data is None:
                    yield event.plain_result(
                        "❌ 未提供 sessionToken 且未绑定账号\n"
                        "💡 请使用 /phi_bind <token> 绑定账号\n"
                        "或直接提供 token: /phi_save <token>"
                    )
                    return
                
                session_token = user_data["session_token"]
                if taptap_version is None:
                    taptap_version = user_data.get("taptap_version", self.plugin.default_taptap_version)
            
            # 使用配置的默认值
            if taptap_version is None:
                taptap_version = self.plugin.default_taptap_version
            
            data = await self.plugin.api_client.get_save(
                session_token=session_token,
                taptap_version=taptap_version,
                calculate_rks=True
            )

            # 使用图片渲染
            async for result in self.plugin._render_and_send(
                event, 
                self.plugin.renderer.render_save_data if self.plugin.renderer else None,
                data, 
                f"save_{session_token[:8]}.png"
            ):
                yield result

        except PhigrosAPIError as e:
            yield event.plain_result(f"❌ 获取存档失败: {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 获取存档失败: {str(e)}")

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
                platform, user_id = self.plugin._get_user_id(event)
                user_data = self.plugin.user_data.get_user_data(platform, user_id)
                
                if user_data is None:
                    yield event.plain_result(
                        "❌ 未提供 sessionToken 且未绑定账号\n"
                        "💡 请使用 /phi_qrlogin 扫码登录\n"
                        "或使用 /phi_bind <token> 绑定账号"
                    )
                    return
                
                session_token = user_data["session_token"]
                if taptap_version is None:
                    taptap_version = user_data.get("taptap_version", self.plugin.default_taptap_version)
            
            # 使用配置的默认值
            if taptap_version is None:
                taptap_version = self.plugin.default_taptap_version
            
            # 验证主题参数
            if theme not in ["black", "white"]:
                theme = "black"
            
            yield event.plain_result("⏳ 正在查询 Best30 数据...")

            # 首先尝试使用 /save API 获取数据，然后本地渲染
            render_success = False
            output_path = self.plugin.output_dir / f"b30_{session_token[:8]}.png"

            if hasattr(self.plugin, 'renderer') and self.plugin.renderer:
                try:
                    # 调用 /save API 获取存档数据
                    save_data = await self.plugin.api_client.get_save(
                        session_token=session_token,
                        taptap_version=taptap_version,
                        calculate_rks=True
                    )

                    yield event.plain_result("🎨 正在渲染 Best30 图片...")

                    # 提取 Best30 数据
                    b30_data = self.plugin._extract_b30_data(save_data)

                    if b30_data:
                        render_success = await self.plugin.renderer.render_b30(b30_data, output_path)
                    else:
                        self.plugin.logger.warning("⚠️ 无法提取 Best30 数据")
                        
                except Exception as e:
                    self.plugin.logger.error(f"使用渲染器生成图片失败: {e}")
                    render_success = False
            
            # 如果渲染器失败，回退到 SVG 转换
            convert_success = False
            if not render_success:
                self.plugin.logger.info("🔄 使用 SVG 转换作为回退方案")
                # 调用 API 获取 SVG
                svg_data = await self.plugin.api_client.get_bestn_image(
                    session_token=session_token,
                    taptap_version=taptap_version,
                    n=30,
                    theme=theme,
                    format="svg"
                )
                
                # 保存 SVG 文件
                svg_path = self.plugin.output_dir / f"b30_{session_token[:8]}.svg"
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_data)
                
                # 将 SVG 转换为 PNG
                if self.plugin.SVG_CONVERTER_AVAILABLE:
                    try:
                        from ..svg_converter import convert_svg_to_png
                        plugin_dir = str(self.plugin.data_dir)
                        illust_path = str(self.plugin.data_dir / self.plugin.illustration_path.replace("./", ""))
                        convert_success = convert_svg_to_png(
                            str(svg_path),
                            str(output_path),
                            illustration_path=illust_path,
                            plugin_dir=plugin_dir
                        )
                    except Exception as e:
                        self.plugin.logger.error(f"SVG 转换失败: {e}")
            
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

        except PhigrosAPIError as e:
            yield event.plain_result(f"❌ 获取 Best30 失败: {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 获取 Best30 失败: {str(e)}")

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
                platform, user_id = self.plugin._get_user_id(event)
                user_data = self.plugin.user_data.get_user_data(platform, user_id)
                
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
                limit = self.plugin.default_history_limit
            
            data = await self.plugin.api_client.get_rks_history(
                session_token=session_token,
                limit=limit,
                offset=0
            )

            items = data.get("items", [])
            total = data.get("total", 0)
            current_rks = data.get("currentRks", 0)
            peak_rks = data.get("peakRks", 0)

            # 渲染 RKS 历史趋势图
            if self.plugin.renderer and hasattr(self.plugin.renderer, 'render_rks_history'):
                output_path = self.plugin.output_dir / f"rks_history_{session_token[:8]}.png"
                render_success = await self.plugin.renderer.render_rks_history(data, output_path)
                
                if render_success:
                    # 发送趋势图
                    yield event.chain_result([
                        Plain(f"📈 RKS 历史趋势图\n"),
                        Image(file=str(output_path))
                    ])
                else:
                    # 渲染失败，发送文本信息
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
            else:
                # 渲染器不可用，发送文本信息
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

        except PhigrosAPIError as e:
            yield event.plain_result(f"❌ 查询 RKS 历史失败: {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 查询 RKS 历史失败: {str(e)}")

    @filter.command("phi_leaderboard")
    async def get_leaderboard(self, event: AstrMessageEvent):
        """
        获取 RKS 排行榜 Top（带图片）
        用法: /phi_leaderboard
        """
        try:
            data = await self.plugin.api_client._make_request(
                method="GET",
                endpoint="/leaderboard/rks/top",
            )

            # 使用图片渲染
            async for result in self.plugin._render_and_send(
                event,
                self.plugin.renderer.render_leaderboard if self.plugin.renderer else None,
                data,
                "leaderboard.png"
            ):
                yield result

        except Exception as e:
            yield event.plain_result(f"❌ 获取排行榜失败: {str(e)}")

    @filter.command("phi_rank")
    async def get_by_rank(self, event: AstrMessageEvent, start: int = None, end: int = None):
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

            data = await self.plugin.api_client._make_request(
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
                limit = self.plugin.default_search_limit
            
            data = await self.plugin.api_client._make_request(
                method="GET",
                endpoint="/songs/search",
                params={"q": keyword, "limit": limit},
            )

            items = data.get("items", [])
            
            if not items:
                yield event.plain_result(f"❌ 未找到与 '{keyword}' 相关的曲目")
                return

            # 如果有曲绘，渲染第一张歌曲的详情
            if self.plugin.renderer and items:
                first_song = items[0]
                from ..utils import sanitize_filename
                safe_keyword = sanitize_filename(keyword)
                async for result in self.plugin._render_and_send(
                    event,
                    self.plugin.renderer.render_song_detail,
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
            platform, user_id = self.plugin._get_user_id(event)
            user_data = self.plugin.user_data.get_user_data(platform, user_id)
            
            if user_data is None:
                yield event.plain_result(
                    "❌ 未绑定账号\n"
                    "💡 请使用 /phi_qrlogin 扫码登录\n"
                    "或使用 /phi_bind <token> 绑定账号"
                )
                return
            
            session_token = user_data["session_token"]
            taptap_version = user_data.get("taptap_version", self.plugin.default_taptap_version)
            
            if not song_id:
                yield event.plain_result(
                    "❌ 请提供歌曲ID\n"
                    "💡 使用 /phi_search <关键词> 搜索歌曲获取ID\n"
                    "示例: /phi_song 曲名.曲师"
                )
                return
            
            yield event.plain_result(f"⏳ 正在生成歌曲成绩图...")
            
            # 调用 API 获取 SVG（返回原始文本）
            svg_data = await self.plugin.api_client._make_request(
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
            import json
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
            svg_path = self.plugin.output_dir / f"song_{safe_song_id}.svg"
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
            
            # 将 SVG 转换为 PNG（QQ 不支持 SVG）
            output_path = self.plugin.output_dir / f"song_{safe_song_id}.png"
            convert_success = False
            
            if self.plugin.SVG_CONVERTER_AVAILABLE:
                try:
                    # 传递曲绘路径和插件目录
                    plugin_dir = str(self.plugin.data_dir)
                    illust_path = str(self.plugin.data_dir / self.plugin.illustration_path.replace("./", ""))
                    from ..svg_converter import convert_svg_to_png
                    convert_success = convert_svg_to_png(
                        str(svg_path),
                        str(output_path),
                        illustration_path=illust_path,
                        plugin_dir=plugin_dir
                    )
                except Exception as e:
                    self.plugin.logger.error(f"SVG 转换失败: {e}")
            else:
                self.plugin.logger.warning("SVG 转换器未加载")

            # 发送图片或提示
            if convert_success:
                yield event.chain_result([
                    Plain(f"🎵 歌曲成绩图\n"),
                    Image(file=str(output_path))
                ])
            else:
                # 转换失败，提示用户 SVG 文件位置
                from ..svg_converter import get_converter
                converter = get_converter() if self.plugin.SVG_CONVERTER_AVAILABLE else None
                help_text = converter.install_help() if converter else "请安装 svglib: pip install svglib reportlab"
                yield event.plain_result(
                    f"⚠️ 歌曲成绩图已保存为 SVG 格式\n"
                    f"📁 文件位置: {svg_path}\n"
                    f"💡 {help_text}"
                )
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取歌曲成绩图失败: {str(e)}")

    @filter.command("phi_updates")
    async def get_updates(self, event: AstrMessageEvent, count: int = 3):
        """
        获取 Phigros 新曲速递
        用法: /phi_updates [count]
        示例: /phi_updates 3
        """
        try:
            data = await self.plugin.api_client._make_request(
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

    @filter.command("phi_bn")
    async def get_bestn(self, event: AstrMessageEvent, n: int = 30, theme: str = "black"):
        """
        获取 BestN 成绩图（API直接生成SVG）
        用法: /phi_bn [n] [theme]
        示例: /phi_bn 27 black
        参数: n=成绩数量(1-50), theme=black/white
        💡 已绑定账号可直接使用 /phi_bn
        """
        try:
            # 从绑定数据获取
            platform, user_id = self.plugin._get_user_id(event)
            user_data = self.plugin.user_data.get_user_data(platform, user_id)
            
            if user_data is None:
                yield event.plain_result(
                    "❌ 未绑定账号\n"
                    "💡 请使用 /phi_qrlogin 扫码登录\n"
                    "或使用 /phi_bind <token> 绑定账号"
                )
                return
            
            session_token = user_data["session_token"]
            taptap_version = user_data.get("taptap_version", self.plugin.default_taptap_version)
            
            # 验证参数
            if n < 1 or n > 50:
                n = 30
            if theme not in ["black", "white"]:
                theme = "black"
            
            yield event.plain_result(f"⏳ 正在查询 Best{n} 数据...")

            # 调用 API 获取 SVG
            svg_data = await self.plugin.api_client.get_bestn_image(
                session_token=session_token,
                taptap_version=taptap_version,
                n=n,
                theme=theme,
                format="svg"
            )
            
            # 保存 SVG 文件
            svg_path = self.plugin.output_dir / f"bn_{n}_{session_token[:8]}.svg"
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
            
            # 将 SVG 转换为 PNG
            output_path = self.plugin.output_dir / f"bn_{n}_{session_token[:8]}.png"
            convert_success = False
            
            if self.plugin.SVG_CONVERTER_AVAILABLE:
                try:
                    from ..svg_converter import convert_svg_to_png
                    plugin_dir = str(self.plugin.data_dir)
                    illust_path = str(self.plugin.data_dir / self.plugin.illustration_path.replace("./", ""))
                    convert_success = convert_svg_to_png(
                        str(svg_path),
                        str(output_path),
                        illustration_path=illust_path,
                        plugin_dir=plugin_dir
                    )
                except Exception as e:
                    self.plugin.logger.error(f"SVG 转换失败: {e}")
            else:
                self.plugin.logger.warning("SVG 转换器未加载")

            # 发送图片或提示
            if convert_success:
                yield event.chain_result([
                    Plain(f"🎵 Best{n} 成绩图 ({theme}主题)\n"),
                    Image(file=str(output_path))
                ])
            else:
                # 转换失败，提示用户 SVG 文件位置
                from ..svg_converter import get_converter
                converter = get_converter() if self.plugin.SVG_CONVERTER_AVAILABLE else None
                help_text = converter.install_help() if converter else "请安装 svglib: pip install svglib reportlab"
                yield event.plain_result(
                    f"⚠️ Best{n} 成绩图已保存为 SVG 格式\n"
                    f"📁 文件位置: {svg_path}\n"
                    f"💡 {help_text}"
                )
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取 Best{n} 失败: {str(e)}")
