#!/usr/bin/env python3
"""
简化版缓存管理器测试
"""
import asyncio
import json
import os
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Generic, TypeVar, List
import aiofiles

# 模拟logger
class MockLogger:
    def debug(self, msg):
        print(f"DEBUG: {msg}")
    def info(self, msg):
        print(f"INFO: {msg}")
    def warning(self, msg):
        print(f"WARNING: {msg}")

logger = MockLogger()

# 模拟CacheError
class CacheError(Exception):
    pass

K = TypeVar('K')
V = TypeVar('V')

class LRUCache(Generic[K, V]):
    def __init__(
        self,
        capacity: int = 1000,
        ttl: Optional[int] = None
    ):
        self.capacity = capacity
        self.ttl = ttl
        self._cache: OrderedDict[K, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        # 缓存命中率监控
        self._hits = 0
        self._misses = 0

    async def get(self, key: K) -> Optional[V]:
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            # 移动到末尾（最新使用）
            self._cache.move_to_end(key)
            item = self._cache[key]

            # 检查是否过期
            if self.ttl is not None:
                if datetime.now() - item['timestamp'] > timedelta(seconds=self.ttl):
                    del self._cache[key]
                    logger.debug(f"🗑️  LRU 缓存已过期，移除键: {key}")
                    self._misses += 1
                    return None

            self._hits += 1
            return item['value']

    async def set(self, key: K, value: V) -> None:
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
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            logger.info("🧹 LRU 缓存已清空")

    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)

    async def get_hit_rate(self) -> float:
        async with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return self._hits / total

    async def get_stats(self) -> Dict[str, int]:
        async with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache)
            }

class DiskCache:
    def __init__(
        self,
        cache_dir: Path,
        ttl: Optional[int] = 3600,
        max_size: int = 1000
    ):
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()
        # 缓存命中率监控
        self._hits = 0
        self._misses = 0
        # 清理计数器，避免每次写入都清理
        self._cleanup_counter = 0
        self._cleanup_interval = 10  # 每10次写入执行一次清理

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 设置缓存目录权限为 700
        os.chmod(self.cache_dir, 0o700)

    def _get_cache_path(self, key: str) -> Path:
        import hashlib
        safe_key = hashlib.md5(str(key).encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self._misses += 1
            return None

        try:
            async with self._lock:
                # 检查文件是否过期
                if self.ttl is not None:
                    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                    if datetime.now() - mtime > timedelta(seconds=self.ttl):
                        cache_path.unlink()
                        logger.debug(f"🗑️  磁盘缓存已过期，移除: {cache_path}")
                        self._misses += 1
                        return None

                # 读取缓存
                async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self._hits += 1
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"⚠️  读取磁盘缓存失败: {e}")
            try:
                cache_path.unlink(missing_ok=True)
            except:
                pass
            self._misses += 1
            return None

    async def set(self, key: str, value: Any) -> None:
        try:
            async with self._lock:
                # 每10次写入执行一次清理
                self._cleanup_counter += 1
                if self._cleanup_counter >= self._cleanup_interval:
                    await self._cleanup()
                    self._cleanup_counter = 0

                cache_path = self._get_cache_path(key)

                # 写入缓存
                async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(value, ensure_ascii=False, indent=2))

                logger.debug(f"💾 磁盘缓存已写入: {cache_path}")
        except Exception as e:
            raise CacheError(f"写入磁盘缓存失败: {e}")

    async def delete(self, key: str) -> bool:
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
        try:
            async with self._lock:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                logger.info("🧹 磁盘缓存已清空")
        except Exception as e:
            logger.warning(f"⚠️  清空磁盘缓存失败: {e}")

    async def get_hit_rate(self) -> float:
        async with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return self._hits / total

    async def get_stats(self) -> Dict[str, int]:
        async with self._lock:
            # 计算磁盘缓存文件数量
            cache_files = list(self.cache_dir.glob("*.cache"))
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(cache_files)
            }

class HybridCache:
    def __init__(
        self,
        cache_dir: Path,
        lru_capacity: int = 1000,
        lru_ttl: Optional[int] = 300,
        disk_ttl: Optional[int] = 3600,
        disk_max_size: int = 1000
    ):
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
        await self.lru_cache.delete(key)
        await self.disk_cache.delete(key)

    async def clear(self) -> None:
        await self.lru_cache.clear()
        await self.disk_cache.clear()

    async def warmup(self, keys: List[str]) -> None:
        for key in keys:
            # 从磁盘缓存加载到内存缓存
            value = await self.disk_cache.get(key)
            if value is not None:
                await self.lru_cache.set(key, value)
                logger.debug(f"🔥 缓存预热成功: {key}")
        logger.info(f"🧹 缓存预热完成，共预热 {len(keys)} 个键")

    async def get_hit_rate(self) -> Dict[str, float]:
        lru_hit_rate = await self.lru_cache.get_hit_rate()
        disk_hit_rate = await self.disk_cache.get_hit_rate()
        
        # 获取统计信息计算整体命中率
        lru_stats = await self.lru_cache.get_stats()
        disk_stats = await self.disk_cache.get_stats()
        
        total_hits = lru_stats["hits"] + disk_stats["hits"]
        total_misses = lru_stats["misses"] + disk_stats["misses"]
        total = total_hits + total_misses
        
        overall_hit_rate = total_hits / total if total > 0 else 0.0
        
        return {
            "lru": lru_hit_rate,
            "disk": disk_hit_rate,
            "overall": overall_hit_rate
        }

async def test_cache_manager():
    """测试缓存管理器功能"""
    # 创建临时缓存目录
    cache_dir = Path("./test_cache")
    
    # 初始化混合缓存
    cache = HybridCache(cache_dir=cache_dir)
    
    # 测试基本功能
    print("测试基本功能...")
    
    # 测试get_or_set方法
    async def mock_api():
        print("调用API获取数据")
        return {"data": "test", "timestamp": "2023-01-01"}
    
    # 第一次调用，应该调用API
    value1 = await cache.get_or_set("test_key", mock_api)
    print(f"第一次获取值: {value1}")
    
    # 第二次调用，应该从缓存获取
    value2 = await cache.get_or_set("test_key", mock_api)
    print(f"第二次获取值: {value2}")
    
    # 测试删除功能
    print("\n测试删除功能...")
    await cache.delete("test_key")
    
    # 删除后再次获取，应该调用API
    value3 = await cache.get_or_set("test_key", mock_api)
    print(f"删除后获取值: {value3}")
    
    # 测试缓存预热
    print("\n测试缓存预热...")
    # 先设置一些缓存
    async def mock_api1():
        return {"data": "value1"}
    async def mock_api2():
        return {"data": "value2"}
    async def mock_api3():
        return {"data": "value3"}
    
    await cache.get_or_set("key1", mock_api1)
    await cache.get_or_set("key2", mock_api2)
    await cache.get_or_set("key3", mock_api3)
    
    # 预热缓存
    await cache.warmup(["key1", "key2", "key3"])
    
    # 测试缓存命中率
    print("\n测试缓存命中率...")
    hit_rate = await cache.get_hit_rate()
    print(f"缓存命中率: {hit_rate}")
    
    # 测试清空缓存
    print("\n测试清空缓存...")
    await cache.clear()
    
    # 清空后再次获取，应该调用API
    value4 = await cache.get_or_set("test_key", mock_api)
    print(f"清空后获取值: {value4}")
    
    # 清理测试目录
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)
    
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(test_cache_manager())
