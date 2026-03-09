"""
📦 缓存管理器模块

包含 LRU 缓存淘汰策略和混合缓存系统，内存 + 磁盘双重缓存，性能杠杠的！
"""
import asyncio
import json
import pickle
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Generic, TypeVar
from pathlib import Path
from collections import OrderedDict

from astrbot.api import logger
from .exceptions import CacheError

K = TypeVar('K')
V = TypeVar('V')


class LRUCache(Generic[K, V]):
    """
    LRU (Least Recently Used) 缓存实现

    使用 OrderedDict 实现高效的 LRU 缓存淘汰策略！
    """

    def __init__(
        self,
        capacity: int = 1000,
        ttl: Optional[int] = None
    ):
        """
        Args:
            capacity: 缓存容量（最大键值对数量）
            ttl: 缓存过期时间（秒），None 表示不自动过期
        """
        self.capacity = capacity
        self.ttl = ttl
        self._cache: OrderedDict[K, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> Optional[V]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            Optional[V]: 缓存值，如果不存在或已过期则返回 None
        """
        async with self._lock:
            if key not in self._cache:
                return None

            # 移动到末尾（最新使用）
            self._cache.move_to_end(key)
            item = self._cache[key]

            # 检查是否过期
            if self.ttl is not None:
                if datetime.now() - item['timestamp'] > timedelta(seconds=self.ttl):
                    del self._cache[key]
                    logger.debug(f"🗑️  LRU 缓存已过期，移除键: {key}")
                    return None

            return item['value']

    async def set(self, key: K, value: V) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        async with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]
            # 如果达到容量，移除最旧的
            elif len(self._cache) >= self.capacity:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"🗑️  LRU 缓存已满，移除最旧键: {oldest_key}")

            # 添加新值
            self._cache[key] = {
                'value': value,
                'timestamp': datetime.now()
            }

    async def delete(self, key: K) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("🧹 LRU 缓存已清空")

    async def size(self) -> int:
        """获取当前缓存大小"""
        async with self._lock:
            return len(self._cache)


class DiskCache:
    """
    磁盘缓存

    使用文件系统存储缓存，支持跨进程持久化！
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl: Optional[int] = 3600,
        max_size: int = 1000
    ):
        """
        Args:
            cache_dir: 缓存目录
            ttl: 缓存过期时间（秒）
            max_size: 最大缓存文件数量
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用安全的文件名
        import hashlib
        safe_key = hashlib.md5(str(key).encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """
        从磁盘读取缓存

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存值
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            async with self._lock:
                # 检查文件是否过期
                if self.ttl is not None:
                    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                    if datetime.now() - mtime > timedelta(seconds=self.ttl):
                        cache_path.unlink()
                        logger.debug(f"🗑️  磁盘缓存已过期，移除: {cache_path}")
                        return None

                # 读取缓存
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"⚠️  读取磁盘缓存失败: {e}")
            try:
                cache_path.unlink(missing_ok=True)
            except:
                pass
            return None

    async def set(self, key: str, value: Any) -> None:
        """
        写入缓存到磁盘

        Args:
            key: 缓存键
            value: 缓存值
        """
        try:
            async with self._lock:
                # 先清理过期文件
                await self._cleanup()

                cache_path = self._get_cache_path(key)

                # 写入缓存
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)

                logger.debug(f"💾 磁盘缓存已写入: {cache_path}")
        except Exception as e:
            raise CacheError(f"写入磁盘缓存失败: {e}", key)

    async def delete(self, key: str) -> bool:
        """
        删除磁盘缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        cache_path = self._get_cache_path(key)
        try:
            async with self._lock:
                if cache_path.exists():
                    cache_path.unlink()
                    return True
                return False
        except Exception as e:
            logger.warning(f"⚠️  删除磁盘缓存失败: {e}")
            return False

    async def _cleanup(self) -> None:
        """清理过期和超出数量限制的缓存"""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))

            # 按修改时间排序
            cache_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # 删除过期文件
            if self.ttl is not None:
                now = datetime.now()
                for cache_file in cache_files[:]:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if now - mtime > timedelta(seconds=self.ttl):
                        cache_file.unlink()
                        cache_files.remove(cache_file)
                        logger.debug(f"🗑️  清理过期缓存: {cache_file}")

            # 删除超出数量限制的文件
            if len(cache_files) > self.max_size:
                for cache_file in cache_files[self.max_size:]:
                    cache_file.unlink()
                    logger.debug(f"🗑️  清理超出限制缓存: {cache_file}")

        except Exception as e:
            logger.warning(f"⚠️  清理磁盘缓存失败: {e}")

    async def clear(self) -> None:
        """清空所有磁盘缓存"""
        try:
            async with self._lock:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                logger.info("🧹 磁盘缓存已清空")
        except Exception as e:
            logger.warning(f"⚠️  清空磁盘缓存失败: {e}")


class HybridCache:
    """
    混合缓存系统

    三级缓存：内存 LRU -> 磁盘 -> API，性能最优！
    """

    def __init__(
        self,
        cache_dir: Path,
        lru_capacity: int = 1000,
        lru_ttl: Optional[int] = 300,
        disk_ttl: Optional[int] = 3600,
        disk_max_size: int = 1000
    ):
        """
        Args:
            cache_dir: 缓存目录
            lru_capacity: LRU 缓存容量
            lru_ttl: LRU 缓存过期时间（秒）
            disk_ttl: 磁盘缓存过期时间（秒）
            disk_max_size: 磁盘缓存最大文件数
        """
        self.lru_cache = LRUCache[str, Any](capacity=lru_capacity, ttl=lru_ttl)
        self.disk_cache = DiskCache(
            cache_dir=cache_dir,
            ttl=disk_ttl,
            max_size=disk_max_size
        )

    async def get_or_set(
        self,
        key: str,
        coro_func: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存或设置新值

        Args:
            key: 缓存键
            coro_func: 生成值的协程函数
            ttl: 可选的自定义 TTL

        Returns:
            Any: 缓存值
        """
        # 1. 先从 LRU 缓存获取
        value = await self.lru_cache.get(key)
        if value is not None:
            logger.debug(f"✅ 内存缓存命中: {key}")
            return value

        # 2. 从磁盘缓存获取
        value = await self.disk_cache.get(key)
        if value is not None:
            logger.debug(f"✅ 磁盘缓存命中: {key}")
            # 回填到 LRU 缓存
            await self.lru_cache.set(key, value)
            return value

        # 3. 调用协程获取新值
        logger.debug(f"🔄 缓存未命中，调用 API: {key}")
        value = await coro_func()

        # 4. 保存到缓存
        await self.lru_cache.set(key, value)
        await self.disk_cache.set(key, value)

        return value

    async def delete(self, key: str) -> None:
        """删除缓存"""
        await self.lru_cache.delete(key)
        await self.disk_cache.delete(key)

    async def clear(self) -> None:
        """清空所有缓存"""
        await self.lru_cache.clear()
        await self.disk_cache.clear()
