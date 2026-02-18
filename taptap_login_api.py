"""
TapTap 扫码登录模块 (API 版本)
使用 Phigros Query 开放平台 API 实现二维码登录
"""

import asyncio
import base64
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from astrbot.api import logger
import aiohttp

# 尝试导入 qrcode 库
try:
    import qrcode
    from PIL import Image as PILImage
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    logger.warning("未安装 qrcode 库，将使用 API 返回的二维码")


class LoginStatus(Enum):
    """登录状态枚举"""
    INITIALIZING = "initializing"
    QR_GENERATING = "qr_generating"
    QR_READY = "qr_ready"
    SCANNING = "scanning"
    SCANNED = "scanned"
    CONFIRMING = "confirming"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class LoginResult:
    """登录结果"""
    success: bool
    session_token: Optional[str] = None
    error_message: Optional[str] = None
    qr_code_path: Optional[str] = None


class TapTapLoginManagerAPI:
    """TapTap 扫码登录管理器 (API 版本)"""

    def __init__(self, base_url: str, api_token: str, output_dir: Path, session: aiohttp.ClientSession):
        """
        初始化登录管理器

        Args:
            base_url: API 基础 URL
            api_token: API Token
            output_dir: 输出目录
            session: aiohttp ClientSession
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.session = session

        # 文件路径
        self.qr_code_path = output_dir / "taptap_qr.png"

        # 状态
        self._current_status = LoginStatus.INITIALIZING
        self._session_token: Optional[str] = None
        self._error_message: Optional[str] = None
        self._qr_id: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["X-OpenApi-Token"] = self.api_token
        return headers

    async def generate_qr_code(self, taptap_version: str = "cn") -> Optional[str]:
        """
        生成二维码

        Args:
            taptap_version: TapTap 版本，cn（大陆版）或 global（国际版）

        Returns:
            str: 二维码图片的 base64 编码
        """
        self._current_status = LoginStatus.QR_GENERATING

        try:
            url = f"{self.base_url}/auth/qrcode"
            params = {"taptapVersion": taptap_version}

            logger.info(f"正在请求生成二维码: {url}")

            async with self.session.post(
                url=url,
                headers=self._get_headers(),
                params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"生成二维码失败: HTTP {response.status} - {error_text}")

                data = await response.json()

                # 保存 qrId 用于后续轮询
                self._qr_id = data.get("qrId")
                qrcode_base64 = data.get("qrcodeBase64")
                verification_url = data.get("verificationUrl")

                if not self._qr_id or not qrcode_base64:
                    raise Exception("API 返回数据不完整")

                logger.info(f"二维码生成成功，qrId: {self._qr_id}")
                logger.info(f"验证链接: {verification_url}")

                # 使用 verificationUrl 生成二维码图片（更可靠）
                if QRCODE_AVAILABLE and verification_url:
                    logger.info("使用 qrcode 库生成二维码图片")
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_H,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(verification_url)
                    qr.make(fit=True)
                    
                    # 生成图片
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(self.qr_code_path)
                    logger.info(f"二维码已保存到: {self.qr_code_path}")
                else:
                    # 回退：使用 API 返回的 base64 数据
                    logger.info("使用 API 返回的 base64 数据")
                    
                    # 处理 Base64 数据（移除可能的 data URI 前缀）
                    if ',' in qrcode_base64:
                        qrcode_base64 = qrcode_base64.split(',')[1]
                    
                    # 修复 Base64 填充
                    padding_needed = 4 - len(qrcode_base64) % 4
                    if padding_needed != 4:
                        qrcode_base64 += '=' * padding_needed
                    
                    # 保存二维码图片
                    qr_data = base64.b64decode(qrcode_base64)
                    with open(self.qr_code_path, 'wb') as f:
                        f.write(qr_data)

                self._current_status = LoginStatus.QR_READY
                return qrcode_base64

        except aiohttp.ClientError as e:
            self._current_status = LoginStatus.ERROR
            self._error_message = f"网络请求错误: {str(e)}"
            logger.error(self._error_message)
            return None
        except Exception as e:
            self._current_status = LoginStatus.ERROR
            self._error_message = f"生成二维码失败: {str(e)}"
            logger.error(self._error_message)
            return None

    async def check_login_status(self) -> Dict[str, Any]:
        """
        检查登录状态

        Returns:
            Dict: 包含 status 和可能的 sessionToken
        """
        if not self._qr_id:
            return {"status": "error", "error": "qrId 未设置"}

        try:
            url = f"{self.base_url}/auth/qrcode/{self._qr_id}/status"

            async with self.session.get(
                url=url,
                headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"检查状态失败: HTTP {response.status} - {error_text}")

                data = await response.json()
                logger.debug(f"登录状态响应: {data}")
                return data

        except Exception as e:
            logger.error(f"检查登录状态出错: {e}")
            return {"status": "error", "error": str(e)}

    async def wait_for_scan(self, timeout: int = 120, callback: Optional[Callable] = None) -> LoginResult:
        """
        等待用户扫码

        Args:
            timeout: 超时时间（秒）
            callback: 状态回调函数

        Returns:
            LoginResult: 登录结果
        """
        if not self._qr_id:
            return LoginResult(success=False, error_message="qrId 未设置，请先生成二维码")

        logger.info(f"开始等待扫码，超时时间: {timeout}秒，qrId: {self._qr_id}")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        start_time = loop.time()
        last_status = None

        while (loop.time() - start_time) < timeout:
            try:
                logger.debug(f"正在检查登录状态... (已等待 {int(loop.time() - start_time)} 秒)")
                result = await self.check_login_status()
                status = result.get("status")
                retry_after = result.get("retryAfter", 2)
                logger.info(f"登录状态: {status}, 重试间隔: {retry_after}秒")

                # 登录成功
                if status == "success":
                    # 尝试多种可能的字段名
                    session_token = result.get("sessionToken") or result.get("session_token") or result.get("token")
                    logger.info(f"收到登录成功响应，sessionToken: {session_token[:20] if session_token else 'None'}...")
                    logger.info(f"完整响应数据: {result}")
                    if session_token:
                        self._session_token = session_token
                        self._current_status = LoginStatus.SUCCESS
                        logger.info(f"登录成功，获取到 sessionToken: {session_token[:20]}...")

                        if callback:
                            callback(LoginStatus.SUCCESS, "登录成功！")

                        return LoginResult(
                            success=True,
                            session_token=session_token,
                            qr_code_path=str(self.qr_code_path) if self.qr_code_path.exists() else None
                        )
                    else:
                        return LoginResult(success=False, error_message="登录成功但未获取到 sessionToken")

                # 二维码已扫描，等待确认
                elif status == "scanned":
                    if last_status != LoginStatus.SCANNED:
                        last_status = LoginStatus.SCANNED
                        self._current_status = LoginStatus.SCANNED
                        logger.info("二维码已扫描，等待确认")

                        if callback:
                            callback(LoginStatus.SCANNED, "二维码已扫描，请在手机上确认登录")

                # 等待扫码
                elif status == "pending":
                    remaining = int(timeout - (loop.time() - start_time))
                    if callback and remaining % 10 == 0:  # 每10秒更新一次
                        callback(LoginStatus.QR_READY, f"等待扫码... ({remaining}秒)")

                # 二维码过期
                elif status == "expired":
                    self._current_status = LoginStatus.TIMEOUT
                    logger.warning("二维码已过期")

                    if callback:
                        callback(LoginStatus.TIMEOUT, "二维码已过期，请重试")

                    return LoginResult(success=False, error_message="二维码已过期")

                # 错误状态
                elif status == "error":
                    error_msg = result.get("error", "未知错误")
                    self._current_status = LoginStatus.ERROR
                    logger.error(f"登录出错: {error_msg}")

                    if callback:
                        callback(LoginStatus.ERROR, f"登录出错: {error_msg}")

                    return LoginResult(success=False, error_message=f"登录出错: {error_msg}")

                # 未知状态
                else:
                    logger.warning(f"未知的登录状态: {status}, 完整数据: {result}")

                # 等待后重试
                logger.debug(f"当前状态: {status}, 等待 {retry_after} 秒后重试...")
                await asyncio.sleep(retry_after)

            except Exception as e:
                logger.error(f"检查登录状态出错: {e}")
                await asyncio.sleep(2)

        # 超时
        self._current_status = LoginStatus.TIMEOUT
        logger.warning("登录超时")

        if callback:
            callback(LoginStatus.TIMEOUT, "登录超时，请重试")

        return LoginResult(success=False, error_message="登录超时")

    async def login(self, taptap_version: str = "cn", timeout: int = 120, callback: Optional[Callable] = None) -> LoginResult:
        """
        完整的登录流程

        Args:
            taptap_version: TapTap 版本
            timeout: 超时时间
            callback: 状态回调函数，接收 (status: LoginStatus, message: str)

        Returns:
            LoginResult: 登录结果
        """
        try:
            # 生成二维码
            qr_base64 = await self.generate_qr_code(taptap_version)

            if not qr_base64:
                return LoginResult(
                    success=False,
                    error_message=self._error_message or "生成二维码失败"
                )

            # 通知二维码已就绪
            if callback:
                callback(LoginStatus.QR_READY, "二维码已生成")

            # 等待扫码
            result = await self.wait_for_scan(timeout=timeout, callback=callback)

            return result

        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            return LoginResult(success=False, error_message=f"登录出错: {str(e)}")

    @property
    def current_status(self) -> LoginStatus:
        """获取当前状态"""
        return self._current_status

    @property
    def session_token(self) -> Optional[str]:
        """获取 session token"""
        return self._session_token

    @property
    def qr_id(self) -> Optional[str]:
        """获取二维码 ID"""
        return self._qr_id
