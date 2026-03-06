"""
TapTap 扫码登录模块
使用 Playwright 模拟浏览器操作，获取二维码并监听登录状态
"""

import asyncio
import base64
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from astrbot.api import logger

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # 静默处理，不再输出警告（已改用 API 版本）
    pass


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


class TapTapLoginManager:
    """TapTap 扫码登录管理器"""
    
    # 官网地址
    LOGIN_URL = "https://lilith.xtower.site/"
    
    # 选择器配置
    SELECTORS = {
        "login_button": [
            'button:has-text("登录")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'a:has-text("登录")',
            'a:has-text("Login")',
            '[class*="login" i]',
            '[class*="signin" i]',
            '#login',
            '.login-btn',
        ],
        "taptap_option": [
            'text=/TapTap|taptap|TAPTAP/i',
            'img[alt*="TapTap" i]',
            'img[src*="taptap" i]',
            '[class*="taptap" i]',
            'button:has-text("TapTap")',
        ],
        "qr_code": [
            'img[src*="qr" i]',
            'img[alt*="二维码" i]',
            'img[alt*="QR" i]',
            '.qr-code img',
            '[class*="qr" i] img',
            '[class*="qrcode" i] img',
            'canvas[class*="qr" i]',
            'canvas',
            'img[src^="data:image"]',
        ],
    }
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # 文件路径
        self.qr_code_path = output_dir / "taptap_qr.png"
        self.debug_path = output_dir / "debug_page.png"
        self.error_path = output_dir / "error_page.png"
        
        # 浏览器实例
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # 状态
        self._current_status = LoginStatus.INITIALIZING
        self._session_token: Optional[str] = None
        self._error_message: Optional[str] = None
    
    async def initialize(self) -> bool:
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            self._error_message = "请先安装 playwright: pip install playwright && playwright install chromium"
            logger.error(self._error_message)
            return False
        
        try:
            logger.info("正在初始化浏览器...")
            self._playwright = await async_playwright().start()
            
            # 启动浏览器（无头模式）
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                ]
            )
            
            # 创建上下文
            self._context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )
            
            # 创建页面
            self._page = await self._context.new_page()
            
            # 设置超时
            self._page.set_default_timeout(30000)
            
            logger.info("浏览器初始化成功")
            return True
            
        except Exception as e:
            self._error_message = f"浏览器初始化失败: {str(e)}"
            logger.error(self._error_message)
            await self.terminate()
            return False
    
    async def terminate(self):
        """清理资源"""
        logger.info("正在清理浏览器资源...")
        
        try:
            if self._page:
                await self._page.close()
                self._page = None
        except Exception as e:
            logger.warning(f"关闭页面失败: {e}")
        
        try:
            if self._context:
                await self._context.close()
                self._context = None
        except Exception as e:
            logger.warning(f"关闭上下文失败: {e}")
        
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
        except Exception as e:
            logger.warning(f"关闭浏览器失败: {e}")
        
        try:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.warning(f"停止 playwright 失败: {e}")
        
        logger.info("浏览器资源清理完成")
    
    async def _safe_click(self, selector: str, timeout: int = 5000) -> bool:
        """安全点击元素"""
        if not self._page:
            return False
        
        try:
            element = await self._page.wait_for_selector(selector, timeout=timeout)
            if element:
                await element.click()
                return True
        except Exception as e:
            logger.debug(f"点击失败 {selector}: {e}")
        
        return False
    
    async def _find_and_click(self, selectors: list, timeout: int = 5000) -> bool:
        """查找并点击第一个匹配的元素"""
        for selector in selectors:
            if await self._safe_click(selector, timeout):
                logger.info(f"成功点击: {selector}")
                return True
        
        return False
    
    async def _wait_for_element(self, selectors: list, timeout: int = 10000):
        """等待任意一个元素出现"""
        if not self._page:
            return None

        for selector in selectors:
            try:
                element = await self._page.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except Exception as e:
                # 记录具体异常类型，便于调试
                logger.debug(f"等待元素 {selector} 失败: {type(e).__name__}: {e}")
                continue

        return None
    
    async def _save_screenshot(self, filename: str = "debug.png") -> Optional[str]:
        """保存页面截图"""
        if not self._page:
            return None
        
        try:
            path = str(self.output_dir / filename)
            await self._page.screenshot(path=path, full_page=True)
            logger.info(f"截图已保存: {path}")
            return path
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    async def generate_qr_code(self) -> Optional[str]:
        """
        生成二维码
        
        Returns:
            str: 二维码图片的 base64 编码
        """
        self._current_status = LoginStatus.QR_GENERATING
        
        # 初始化浏览器
        if not await self.initialize():
            self._current_status = LoginStatus.ERROR
            return None
        
        try:
            logger.info(f"正在访问: {self.LOGIN_URL}")
            
            # 访问官网
            await self._page.goto(self.LOGIN_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # 保存初始页面截图
            await self._save_screenshot("step1_initial.png")
            
            # 点击登录按钮
            logger.info("正在查找登录按钮...")
            if not await self._find_and_click(self.SELECTORS["login_button"]):
                # 尝试查找所有按钮
                buttons = await self._page.query_selector_all('button')
                logger.info(f"页面共有 {len(buttons)} 个按钮")
                
                for i, btn in enumerate(buttons[:3]):
                    try:
                        text = await btn.text_content()
                        logger.info(f"尝试点击按钮 {i}: {text}")
                        await btn.click()
                        await asyncio.sleep(1)
                        
                        # 检查是否有弹窗
                        dialogs = await self._page.query_selector_all('dialog, [role="dialog"], .modal, .popup, [class*="login" i]')
                        if dialogs:
                            logger.info("检测到弹窗")
                            break
                    except Exception as e:
                        logger.debug(f"点击按钮 {i} 失败: {e}")
            
            await asyncio.sleep(2)
            await self._save_screenshot("step2_after_login_click.png")
            
            # 点击 TapTap 登录选项
            logger.info("正在查找 TapTap 登录选项...")
            await self._find_and_click(self.SELECTORS["taptap_option"])
            
            await asyncio.sleep(3)
            await self._save_screenshot("step3_after_taptap_click.png")
            
            # 查找二维码
            logger.info("正在查找二维码...")
            qr_element = await self._wait_for_element(self.SELECTORS["qr_code"], timeout=10000)
            
            if qr_element:
                logger.info("找到二维码元素，正在截取...")
                await qr_element.screenshot(path=str(self.qr_code_path))
            else:
                logger.warning("未找到二维码元素，截取整个页面")
                await self._page.screenshot(path=str(self.qr_code_path))
            
            # 验证截图
            if not self.qr_code_path.exists():
                raise Exception("二维码截图未生成")
            
            # 转换为 base64
            with open(self.qr_code_path, 'rb') as f:
                qr_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            self._current_status = LoginStatus.QR_READY
            logger.info("二维码生成成功")
            
            return qr_base64
            
        except Exception as e:
            self._current_status = LoginStatus.ERROR
            self._error_message = f"生成二维码失败: {str(e)}"
            logger.error(self._error_message)
            await self._save_screenshot("error_generate_qr.png")
            return None
    
    async def wait_for_scan(self, timeout: int = 120, callback: Optional[Callable] = None) -> LoginResult:
        """
        等待用户扫码
        
        Args:
            timeout: 超时时间（秒）
            callback: 状态回调函数
            
        Returns:
            LoginResult: 登录结果
        """
        if not self._page:
            return LoginResult(success=False, error_message="页面未初始化")
        
        logger.info(f"开始等待扫码，超时时间: {timeout}秒")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        start_time = loop.time()
        check_interval = 2
        last_status = None

        while (loop.time() - start_time) < timeout:
            try:
                # 检查是否已登录 - 尝试多种方式获取 token
                session_token = await self._page.evaluate("""
                    () => {
                        // 尝试所有可能的 key
                        const keys = [
                            'sessionToken', 'session_token', 'token', 'accessToken', 'access_token',
                            'authToken', 'auth_token', 'userToken', 'user_token'
                        ];
                        
                        for (const key of keys) {
                            let value = localStorage.getItem(key);
                            if (value) {
                                console.log('Found token in localStorage:', key);
                                return value;
                            }
                            
                            value = sessionStorage.getItem(key);
                            if (value) {
                                console.log('Found token in sessionStorage:', key);
                                return value;
                            }
                        }
                        
                        // 尝试遍历所有 localStorage
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            const value = localStorage.getItem(key);
                            if (value && (key.toLowerCase().includes('token') || key.toLowerCase().includes('session'))) {
                                console.log('Found potential token:', key);
                                return value;
                            }
                        }
                        
                        return null;
                    }
                """)
                
                if session_token:
                    self._session_token = session_token
                    self._current_status = LoginStatus.SUCCESS
                    logger.info(f"登录成功，获取到 sessionToken: {session_token[:20]}...")
                    
                    # Token 已通过用户数据管理器保存，不再单独保存到文件
                    
                    if callback:
                        callback(LoginStatus.SUCCESS, "登录成功！")
                    
                    return LoginResult(
                        success=True,
                        session_token=session_token,
                        qr_code_path=str(self.qr_code_path) if self.qr_code_path.exists() else None
                    )
                
                # 检查页面 URL 变化（可能跳转到了登录后的页面）
                current_url = self._page.url
                if current_url != self.LOGIN_URL and '/login' not in current_url:
                    logger.info(f"页面已跳转: {current_url}")
                    # 页面跳转后再次尝试获取 token
                    await asyncio.sleep(1)
                    continue
                
                # 检查页面内容变化
                page_content = await self._page.content()
                
                # 检测已扫描状态
                if any(text in page_content for text in ['已扫描', '已扫码', 'scanned', '确认登录', '请在手机上确认']):
                    if last_status != LoginStatus.SCANNED:
                        last_status = LoginStatus.SCANNED
                        self._current_status = LoginStatus.SCANNED
                        logger.info("二维码已扫描，等待确认")
                        
                        if callback:
                            callback(LoginStatus.SCANNED, "二维码已扫描，请在手机上确认登录")
                
                # 检测确认中状态
                elif any(text in page_content for text in ['确认中', 'confirming', '处理中']):
                    if last_status != LoginStatus.CONFIRMING:
                        last_status = LoginStatus.CONFIRMING
                        self._current_status = LoginStatus.CONFIRMING
                        logger.info("正在确认登录...")
                        
                        if callback:
                            callback(LoginStatus.CONFIRMING, "正在确认登录...")
                
                # 等待中
                else:
                    remaining = int(timeout - (loop.time() - start_time))

                    if callback and remaining % 10 == 0:  # 每10秒更新一次
                        callback(LoginStatus.QR_READY, f"等待扫码... ({remaining}秒)")
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"检查登录状态出错: {e}")
                await asyncio.sleep(check_interval)
        
        # 超时
        self._current_status = LoginStatus.TIMEOUT
        logger.warning("登录超时")
        
        if callback:
            callback(LoginStatus.TIMEOUT, "登录超时，请重试")
        
        return LoginResult(success=False, error_message="登录超时")
    
    async def login(self, timeout: int = 120, callback: Optional[Callable] = None) -> LoginResult:
        """
        完整的登录流程
        
        Args:
            timeout: 超时时间
            callback: 状态回调函数，接收 (status: LoginStatus, message: str)
            
        Returns:
            LoginResult: 登录结果
        """
        try:
            # 生成二维码
            qr_base64 = await self.generate_qr_code()
            
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
        
        finally:
            await self.terminate()
    
    @property
    def current_status(self) -> LoginStatus:
        """获取当前状态"""
        return self._current_status
    
    @property
    def session_token(self) -> Optional[str]:
        """获取 session token"""
        return self._session_token


def check_playwright_installed() -> bool:
    """检查是否安装了 playwright"""
    return PLAYWRIGHT_AVAILABLE
