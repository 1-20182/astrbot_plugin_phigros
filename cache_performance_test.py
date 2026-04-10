import time
import statistics
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟必要的模块
class MockLogger:
    def info(self, msg):
        pass
    def error(self, msg):
        pass
    def debug(self, msg):
        pass

# 替换logger
import core.cache_manager
core.cache_manager.logger = MockLogger()

from core.cache_manager import LRUCache, DiskCache, HybridCache

def test_cache_performance():
    """测试缓存性能"""
    print("开始缓存性能测试...")
    
    # 测试LRU缓存
    print("\n测试LRU缓存...")
    lru_cache = LRUCache(max_size=1000, ttl=3600)
    lru_times = []
    
    for i in range(1000):
        start_time = time.time()
        lru_cache.set(f"key_{i}", f"value_{i}")
        end_time = time.time()
        lru_times.append((end_time - start_time) * 1000)
    
    for i in range(1000):
        start_time = time.time()
        lru_cache.get(f"key_{i}")
        end_time = time.time()
        lru_times.append((end_time - start_time) * 1000)
    
    print(f"  LRU缓存操作平均时间: {statistics.mean(lru_times):.4f}ms")
    
    # 测试磁盘缓存
    print("\n测试磁盘缓存...")
    disk_cache = DiskCache(cache_dir="./test_cache")
    disk_times = []
    
    for i in range(100):
        start_time = time.time()
        disk_cache.set(f"key_{i}", f"value_{i}")
        end_time = time.time()
        disk_times.append((end_time - start_time) * 1000)
    
    for i in range(100):
        start_time = time.time()
        disk_cache.get(f"key_{i}")
        end_time = time.time()
        disk_times.append((end_time - start_time) * 1000)
    
    print(f"  磁盘缓存操作平均时间: {statistics.mean(disk_times):.4f}ms")
    
    # 测试混合缓存
    print("\n测试混合缓存...")
    hybrid_cache = HybridCache(max_size=1000, ttl=3600, cache_dir="./test_cache")
    hybrid_times = []
    
    for i in range(100):
        start_time = time.time()
        hybrid_cache.set(f"key_{i}", f"value_{i}")
        end_time = time.time()
        hybrid_times.append((end_time - start_time) * 1000)
    
    for i in range(100):
        start_time = time.time()
        hybrid_cache.get(f"key_{i}")
        end_time = time.time()
        hybrid_times.append((end_time - start_time) * 1000)
    
    print(f"  混合缓存操作平均时间: {statistics.mean(hybrid_times):.4f}ms")
    
    # 清理测试缓存
    import shutil
    if os.path.exists("./test_cache"):
        shutil.rmtree("./test_cache")
    
    print("\n缓存性能测试完成！")

if __name__ == "__main__":
    test_cache_performance()