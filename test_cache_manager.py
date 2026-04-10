#!/usr/bin/env python3
"""
测试缓存管理器功能
"""
import asyncio
from pathlib import Path

# 模拟logger对象
class MockLogger:
    def debug(self, msg):
        print(f"DEBUG: {msg}")
    def info(self, msg):
        print(f"INFO: {msg}")
    def warning(self, msg):
        print(f"WARNING: {msg}")

# 替换astrbot.api.logger
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 创建模拟模块
class MockAstrbot:
    class api:
        logger = MockLogger()

# 将模拟模块添加到sys.modules
sys.modules['astrbot'] = MockAstrbot()

from core.cache_manager import HybridCache

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
    await cache.get_or_set("key1", lambda: {"data": "value1"})
    await cache.get_or_set("key2", lambda: {"data": "value2"})
    await cache.get_or_set("key3", lambda: {"data": "value3"})
    
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
