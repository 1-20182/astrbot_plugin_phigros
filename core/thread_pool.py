"""
🔧 线程池工具模块

使用线程池将同步 IO 操作异步化，防止事件循环被阻塞！
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional, TypeVar, Tuple
from functools import wraps

from astrbot.api import logger

T = TypeVar('T')


class ThreadPoolManager:
    """
    线程池管理器

    单例模式，全局共享一个线程池！
    """

    _instance: Optional['ThreadPoolManager'] = None
    _executor: Optional[ThreadPoolExecutor] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_workers: int = 4):
        """
        Args:
            max_workers: 最大线程数
        """
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
            logger.info(f"🔧 线程池初始化成功，最大线程数: {max_workers}")

    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        """获取线程池执行器"""
        if cls._instance is None:
            cls._instance = cls()
        if cls._instance._executor is None:
            cls._instance._executor = ThreadPoolExecutor(max_workers=4)
        return cls._instance._executor

    @classmethod
    def shutdown(cls, wait: bool = True):
        """
        关闭线程池

        Args:
            wait: 是否等待所有任务完成
        """
        if cls._instance and cls._instance._executor:
            cls._instance._executor.shutdown(wait=wait)
            cls._instance._executor = None
            logger.info("🔧 线程池已关闭")


async def run_in_executor(
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    在线程池中运行同步函数

    Args:
        func: 要运行的同步函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        T: 函数返回值
    """
    loop = asyncio.get_running_loop()
    executor = ThreadPoolManager.get_executor()

    # 使用 partial 处理关键字参数
    if kwargs:
        def wrapped_func():
            return func(*args, **kwargs)
        return await loop.run_in_executor(executor, wrapped_func)
    else:
        return await loop.run_in_executor(executor, func, *args)


def asyncify(func: Callable[..., T]) -> Callable[..., Any]:
    """
    装饰器：将同步函数转换为异步函数

    Args:
        func: 同步函数

    Returns:
        异步函数
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await run_in_executor(func, *args, **kwargs)
    return wrapper


# 常用的异步化装饰器
def pil_async(func: Callable) -> Callable:
    """
    专门用于 PIL 图片操作的异步化装饰器

    PIL 的图片操作都是同步 IO，使用这个装饰器可以防止阻塞事件循环！
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_executor(func, *args, **kwargs)
    return wrapper


def file_async(func: Callable) -> Callable:
    """
    专门用于文件操作的异步化装饰器

    文件读写都是同步 IO，使用这个装饰器可以防止阻塞事件循环！
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_executor(func, *args, **kwargs)
    return wrapper
