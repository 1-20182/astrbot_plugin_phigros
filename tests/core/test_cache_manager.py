"""
测试缓存管理模块
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import asyncio

# 模拟astrbot模块
class MockLogger:
    def info(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass
    def debug(self, msg):
        pass

class MockAPI:
    logger = MockLogger()

class MockAstrBot:
    api = MockAPI()

# 添加到sys.modules
sys.modules['astrbot'] = MockAstrBot()
sys.modules['astrbot.api'] = MockAPI()
sys.modules['astrbot.api.logger'] = MockLogger()

# 现在导入被测试模块
from core.cache_manager import LRUCache, DiskCache, HybridCache


class TestLRUCache(unittest.TestCase):
    """测试LRU缓存"""

    async def test_lru_cache_basic(self):
        """测试LRU缓存的基本功能"""
        cache = LRUCache(capacity=3, ttl=3600)
        
        # 添加数据
        await cache.set('key1', 'value1')
        await cache.set('key2', 'value2')
        await cache.set('key3', 'value3')
        
        # 验证数据存在
        self.assertEqual(await cache.get('key1'), 'value1')
        self.assertEqual(await cache.get('key2'), 'value2')
        self.assertEqual(await cache.get('key3'), 'value3')
        
        # 添加新数据，触发LRU淘汰
        await cache.set('key4', 'value4')
        
        # 验证key1被淘汰
        self.assertIsNone(await cache.get('key1'))
        self.assertEqual(await cache.get('key2'), 'value2')
        self.assertEqual(await cache.get('key3'), 'value3')
        self.assertEqual(await cache.get('key4'), 'value4')
        
        # 访问key2，使其成为最近使用
        await cache.get('key2')
        
        # 添加新数据，触发LRU淘汰
        await cache.set('key5', 'value5')
        
        # 验证key3被淘汰
        self.assertIsNone(await cache.get('key3'))
        self.assertEqual(await cache.get('key2'), 'value2')
        self.assertEqual(await cache.get('key4'), 'value4')
        self.assertEqual(await cache.get('key5'), 'value5')
    
    async def test_lru_cache_ttl(self):
        """测试LRU缓存的TTL功能"""
        import time
        cache = LRUCache(capacity=3, ttl=1)  # 1秒TTL
        
        # 添加数据
        await cache.set('key1', 'value1')
        self.assertEqual(await cache.get('key1'), 'value1')
        
        # 等待TTL过期
        time.sleep(1.5)
        
        # 验证数据已过期
        self.assertIsNone(await cache.get('key1'))
    
    def test_lru_cache_basic_sync(self):
        """同步测试LRU缓存的基本功能"""
        asyncio.run(self.test_lru_cache_basic())
    
    def test_lru_cache_ttl_sync(self):
        """同步测试LRU缓存的TTL功能"""
        asyncio.run(self.test_lru_cache_ttl())


class TestDiskCache(unittest.TestCase):
    """测试磁盘缓存"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    async def test_disk_cache_basic(self):
        """测试磁盘缓存的基本功能"""
        cache = DiskCache(cache_dir=self.cache_dir, ttl=3600, max_size=100)
        
        # 添加数据
        await cache.set('key1', 'value1')
        await cache.set('key2', {'nested': 'value2'})
        
        # 验证数据存在
        self.assertEqual(await cache.get('key1'), 'value1')
        self.assertEqual(await cache.get('key2'), {'nested': 'value2'})
        
        # 删除数据
        await cache.delete('key1')
        self.assertIsNone(await cache.get('key1'))
        
        # 清理缓存
        await cache.clear()
        self.assertIsNone(await cache.get('key2'))
    
    def test_disk_cache_basic_sync(self):
        """同步测试磁盘缓存的基本功能"""
        asyncio.run(self.test_disk_cache_basic())


class TestHybridCache(unittest.TestCase):
    """测试混合缓存"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    async def test_hybrid_cache_basic(self):
        """测试混合缓存的基本功能"""
        cache = HybridCache(
            cache_dir=self.cache_dir,
            lru_capacity=3,
            lru_ttl=3600,
            disk_ttl=3600,
            disk_max_size=100
        )
        
        # 添加数据（使用get_or_set）
        async def get_value1():
            return 'value1'
        
        async def get_new_value1():
            return 'new_value1'
        
        value1 = await cache.get_or_set('key1', get_value1)
        self.assertEqual(value1, 'value1')
        
        # 验证数据存在（内存缓存）
        value1_from_cache = await cache.get_or_set('key1', get_value1)
        self.assertEqual(value1_from_cache, 'value1')
        
        # 模拟内存缓存淘汰
        async def get_value2():
            return 'value2'
        
        async def get_value3():
            return 'value3'
        
        async def get_value4():
            return 'value4'
        
        await cache.get_or_set('key2', get_value2)
        await cache.get_or_set('key3', get_value3)
        await cache.get_or_set('key4', get_value4)  # 触发key1被淘汰出内存
        
        # 验证key1从磁盘缓存中读取
        value1_from_disk = await cache.get_or_set('key1', get_value1)
        self.assertEqual(value1_from_disk, 'value1')
        
        # 清理缓存
        await cache.clear()
        # 重新获取，应该调用lambda函数
        value1_after_clear = await cache.get_or_set('key1', get_new_value1)
        self.assertEqual(value1_after_clear, 'new_value1')
    
    def test_hybrid_cache_basic_sync(self):
        """同步测试混合缓存的基本功能"""
        asyncio.run(self.test_hybrid_cache_basic())


if __name__ == '__main__':
    unittest.main()
