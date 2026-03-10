"""
🔄 重试机制模块

提供异步函数的重试装饰器，增强API调用的稳定性
"""

import asyncio
import functools
from typing import Callable, Optional, Type, List, Any
from .exceptions import NetworkError, RateLimitError, PhigrosAPIError


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: List[Type[Exception]] = None,
    max_delay: float = 30.0
) -> Callable:
    """
    异步函数重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff_factor: 退避因子
        exceptions: 要捕获并重试的异常类型列表
        max_delay: 最大延迟（秒）

    Returns:
        装饰后的函数
    """
    if exceptions is None:
        exceptions = [
            NetworkError,
            RateLimitError,
            PhigrosAPIError,
            asyncio.TimeoutError,
            ConnectionError
        ]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # 最后一次尝试失败，抛出异常
                        raise

                    # 计算下一次延迟
                    wait_time = min(current_delay, max_delay)
                    # 对于RateLimitError，使用其建议的等待时间
                    if isinstance(e, RateLimitError) and e.retry_after:
                        wait_time = e.retry_after

                    # 等待后重试
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff_factor

            # 理论上不会执行到这里，因为最后一次尝试会抛出异常
            raise last_exception

        return wrapper

    return decorator


class RetryManager:
    """
    重试管理器
    """

    @staticmethod
    @retry(max_attempts=3, delay=1, backoff_factor=2)
    async def execute_with_retry(func: Callable, *args, **kwargs) -> Any:
        """
        使用重试机制执行异步函数

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        return await func(*args, **kwargs)
