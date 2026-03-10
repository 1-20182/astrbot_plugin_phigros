"""
🚀 API 客户端模块

包含带重试机制、连接池和限流的 Phigros API 客户端，稳定又高效！
"""
import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, Callable, Tuple
from functools import wraps
from datetime import datetime, timedelta

from astrbot.api import logger
from .exceptions import (
    PhigrosAPIError,
    NetworkError,
    RateLimitError,
    ValidationError
)
from .cache_manager import HybridCache
from .monitoring import monitor_api_call, api_monitor
from pathlib import Path


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[type, ...] = (
        NetworkError,
        aiohttp.ClientError,
        asyncio.TimeoutError
    )
):
    """
    重试装饰器，用于自动重试失败的操作

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff_factor: 指数退避因子
        retryable_exceptions: 可重试的异常类型
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(f"⚠️  操作失败，已重试 {max_attempts} 次: {e}")
                        raise

                    logger.warning(f"⚠️  第 {attempt} 次尝试失败，{current_delay:.1f} 秒后重试: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor

            raise last_exception

        return wrapper
    return decorator


class RateLimiter:
    """
    限流器，使用令牌桶算法

    防止 API 请求频率过高被ban，保护你的API访问！
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60
    ):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = None

    async def initialize(self):
        """初始化异步锁"""
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        获取请求许可

        Returns:
            bool: 是否获得许可
        """
        if not self._lock:
            await self.initialize()

        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)

            # 清理过期的请求记录
            self.requests = [
                req_time for req_time in self.requests
                if req_time > window_start
            ]

            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False

            # 记录新请求
            self.requests.append(now)
            return True

    async def wait_for_slot(self) -> None:
        """等待获取请求许可，直到成功"""
        while not await self.acquire():
            await asyncio.sleep(0.5)


class PhigrosAPIClient:
    """
    🎮 Phigros API 客户端

    带重试机制、连接池和限流的高级 API 客户端，稳定又高效！
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        pool_size: int = 50,
        pool_per_host: int = 20,
        max_requests: int = 60,
        window_seconds: int = 60,
        cache_dir: Optional[Path] = None
    ):
        """
        Args:
            base_url: API 基础 URL
            api_token: API 令牌（可选）
            timeout: 请求超时时间（秒）
            pool_size: 连接池大小
            pool_per_host: 每个主机的连接数
            max_requests: 限流最大请求数
            window_seconds: 限流时间窗口（秒）
            cache_dir: 缓存目录
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = timeout
        self.pool_size = pool_size
        self.pool_per_host = pool_per_host
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.cache: Optional[HybridCache] = None
        self.cache_dir = cache_dir

    async def initialize(self):
        """初始化 API 客户端，建立连接池"""
        await self.rate_limiter.initialize()

        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=20
        )
        connector = aiohttp.TCPConnector(
            limit=self.pool_size,
            limit_per_host=self.pool_per_host,
            enable_cleanup_closed=True,
            force_close=False
        )

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "PhigrosQueryBot/2.0.0"}
        )

        # 初始化缓存
        if self.cache_dir:
            self.cache = HybridCache(
                cache_dir=self.cache_dir,
                lru_capacity=1000,
                lru_ttl=300,  # 5分钟
                disk_ttl=3600,  # 1小时
                disk_max_size=1000
            )
            logger.info("💾 API 缓存初始化成功")

        logger.info("🚀 Phigros API 客户端初始化成功")

    async def terminate(self):
        """关闭 API 客户端，释放资源"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔌 Phigros API 客户端已关闭")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["X-OpenApi-Token"] = self.api_token
        return headers

    @retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
    @monitor_api_call()
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        return_raw: bool = False
    ) -> Any:
        """
        发起 HTTP 请求（带重试和限流）

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: URL 参数
            json_data: JSON 请求体
            return_raw: 是否返回原始响应内容

        Returns:
            Any: 响应数据

        Raises:
            PhigrosAPIError: API 错误
            NetworkError: 网络错误
            RateLimitError: 限流错误
        """
        if not self.session or self.session.closed:
            raise PhigrosAPIError("API 客户端未初始化")

        # 等待限流槽位
        await self.rate_limiter.wait_for_slot()

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                params=params,
                json=json_data
            ) as response:
                # 处理 429 限流
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    raise RateLimitError(retry_after=retry_after)

                # 处理其他错误状态码
                if response.status != 200:
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("detail", f"请求失败，状态码: {response.status}")
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        error_text = await response.text()
                        error_msg = f"请求失败，状态码: {response.status}，响应: {error_text[:200]}"
                    raise PhigrosAPIError(
                        message=error_msg,
                        status_code=response.status,
                        endpoint=endpoint
                    )

                # 返回原始内容或解析 JSON
                if return_raw:
                    return await response.text()

                try:
                    return await response.json()
                except json.JSONDecodeError as e:
                    raise PhigrosAPIError(f"解析响应数据失败: {str(e)}")

        except aiohttp.ClientError as e:
            raise NetworkError(message=f"网络请求错误: {str(e)}", url=url)
        except asyncio.TimeoutError:
            raise NetworkError(message="请求超时，请稍后重试", url=url)

    async def get_save(
        self,
        session_token: str,
        taptap_version: str = "cn",
        calculate_rks: bool = True
    ) -> Dict[str, Any]:
        """
        获取用户存档数据

        Args:
            session_token: 用户会话令牌
            taptap_version: TapTap 版本 (cn/global)
            calculate_rks: 是否计算 RKS

        Returns:
            Dict[str, Any]: 存档数据
        """
        if not session_token:
            raise ValidationError("session_token 不能为空", "session_token")

        if taptap_version not in ["cn", "global"]:
            raise ValidationError(
                "taptap_version 必须是 'cn' 或 'global'",
                "taptap_version",
                taptap_version
            )

        # 生成缓存键
        cache_key = f"save_{session_token[:8]}_{taptap_version}_{calculate_rks}"

        # 如果有缓存，尝试从缓存获取
        if self.cache:
            try:
                async def fetch_data():
                    return await self._make_request(
                        method="POST",
                        endpoint="/save",
                        params={"calculate_rks": "true" if calculate_rks else "false"},
                        json_data={
                            "sessionToken": session_token,
                            "taptapVersion": taptap_version
                        }
                    )

                return await self.cache.get_or_set(cache_key, fetch_data)
            except (NetworkError, PhigrosAPIError) as e:
                # API 故障，尝试从缓存获取
                logger.warning(f"API 故障，尝试从缓存获取数据: {e}")
                cached_data = await self.cache.lru_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从缓存成功获取数据")
                    return cached_data
                cached_data = await self.cache.disk_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从磁盘缓存成功获取数据")
                    return cached_data
                # 缓存也没有数据，重新抛出异常
                raise
        else:
            # 没有缓存，直接调用 API
            return await self._make_request(
                method="POST",
                endpoint="/save",
                params={"calculate_rks": "true" if calculate_rks else "false"},
                json_data={
                    "sessionToken": session_token,
                    "taptapVersion": taptap_version
                }
            )

    async def get_rks_history(
        self,
        session_token: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取 RKS 历史记录

        Args:
            session_token: 用户会话令牌
            limit: 记录数量
            offset: 偏移量

        Returns:
            Dict[str, Any]: RKS 历史数据
        """
        if not session_token:
            raise ValidationError("session_token 不能为空", "session_token")

        if limit < 1 or limit > 100:
            raise ValidationError("limit 范围应为 1-100", "limit", limit)

        if offset < 0:
            raise ValidationError("offset 不能为负数", "offset", offset)

        # 生成缓存键
        cache_key = f"rks_history_{session_token[:8]}_{limit}_{offset}"

        # 如果有缓存，尝试从缓存获取
        if self.cache:
            try:
                async def fetch_data():
                    return await self._make_request(
                        method="POST",
                        endpoint="/rks/history",
                        json_data={
                            "auth": {"sessionToken": session_token},
                            "limit": limit,
                            "offset": offset
                        }
                    )

                return await self.cache.get_or_set(cache_key, fetch_data)
            except (NetworkError, PhigrosAPIError) as e:
                # API 故障，尝试从缓存获取
                logger.warning(f"API 故障，尝试从缓存获取 RKS 历史数据: {e}")
                cached_data = await self.cache.lru_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从缓存成功获取 RKS 历史数据")
                    return cached_data
                cached_data = await self.cache.disk_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从磁盘缓存成功获取 RKS 历史数据")
                    return cached_data
                # 缓存也没有数据，重新抛出异常
                raise
        else:
            # 没有缓存，直接调用 API
            return await self._make_request(
                method="POST",
                endpoint="/rks/history",
                json_data={
                    "auth": {"sessionToken": session_token},
                    "limit": limit,
                    "offset": offset
                }
            )

    async def get_bestn_image(
        self,
        session_token: str,
        taptap_version: str = "cn",
        n: int = 30,
        theme: str = "black",
        format: str = "svg"
    ) -> str:
        """
        获取 BestN 成绩图

        Args:
            session_token: 用户会话令牌
            taptap_version: TapTap 版本
            n: 成绩数量
            theme: 主题 (black/white)
            format: 格式 (svg/png)

        Returns:
            str: 图片内容
        """
        if not session_token:
            raise ValidationError("session_token 不能为空", "session_token")

        if n < 1 or n > 50:
            raise ValidationError("n 范围应为 1-50", "n", n)

        if theme not in ["black", "white"]:
            raise ValidationError("theme 必须是 'black' 或 'white'", "theme", theme)

        # 生成缓存键
        cache_key = f"bestn_image_{session_token[:8]}_{taptap_version}_{n}_{theme}_{format}"

        # 如果有缓存，尝试从缓存获取
        if self.cache:
            try:
                async def fetch_data():
                    return await self._make_request(
                        method="POST",
                        endpoint="/image/bn",
                        params={"format": format},
                        json_data={
                            "sessionToken": session_token,
                            "taptapVersion": taptap_version,
                            "n": n,
                            "theme": theme
                        },
                        return_raw=True
                    )

                return await self.cache.get_or_set(cache_key, fetch_data)
            except (NetworkError, PhigrosAPIError) as e:
                # API 故障，尝试从缓存获取
                logger.warning(f"API 故障，尝试从缓存获取 BestN 图片: {e}")
                cached_data = await self.cache.lru_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从缓存成功获取 BestN 图片")
                    return cached_data
                cached_data = await self.cache.disk_cache.get(cache_key)
                if cached_data:
                    logger.info("✅ 从磁盘缓存成功获取 BestN 图片")
                    return cached_data
                # 缓存也没有数据，重新抛出异常
                raise
        else:
            # 没有缓存，直接调用 API
            return await self._make_request(
                method="POST",
                endpoint="/image/bn",
                params={"format": format},
                json_data={
                    "sessionToken": session_token,
                    "taptapVersion": taptap_version,
                    "n": n,
                    "theme": theme
                },
                return_raw=True
            )
