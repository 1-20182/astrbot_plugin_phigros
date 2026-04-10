import time
import statistics
import os
import pickle
from datetime import datetime, timedelta

class LRUCache:
    """LRU 内存缓存"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_order = []
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'expire_at': datetime.now() + timedelta(seconds=self.ttl)
        }
        self.access_order.append(key)
    
    def get(self, key: str):
        """获取缓存"""
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if datetime.now() > item['expire_at']:
            del self.cache[key]
            self.access_order.remove(key)
            return None
        
        self.access_order.remove(key)
        self.access_order.append(key)
        return item['value']

class DiskCache:
    """磁盘缓存"""
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
        with open(cache_file, 'wb') as f:
            pickle.dump(value, f)
    
    def get(self, key: str):
        """获取缓存"""
        cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except:
            return None

class HybridCache:
    """混合缓存（内存 + 磁盘）"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600, cache_dir: str = "./cache"):
        self.memory_cache = LRUCache(max_size, ttl)
        self.disk_cache = DiskCache(cache_dir)
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        self.memory_cache.set(key, value)
        self.disk_cache.set(key, value)
    
    def get(self, key: str):
        """获取缓存"""
        # 先从内存缓存获取
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 再从磁盘缓存获取
        value = self.disk_cache.get(key)
        if value is not None:
            # 回写到内存缓存
            self.memory_cache.set(key, value)
        return value

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
    from typing import Any
    test_cache_performance()