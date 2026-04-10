import asyncio
import time
import statistics
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟logger
class MockLogger:
    def info(self, msg):
        print(f"INFO: {msg}")
    def error(self, msg):
        print(f"ERROR: {msg}")
    def debug(self, msg):
        pass

# 替换astrbot的logger
os.environ['PHIGROS_TEST'] = 'true'
import core.api_client
core.api_client.logger = MockLogger()

from core.api_client import PhigrosAPIClient

async def test_api_performance():
    """测试API响应时间"""
    print("开始API性能测试...")
    
    # 初始化API客户端
    client = PhigrosAPIClient()
    await client.initialize()
    
    # 测试用例：模拟API调用（实际会失败但可以测试响应时间）
    test_cases = [
        ("get_save", {"session_token": "test_token"}),
        ("get_leaderboard", {"page": 1, "limit": 10}),
        ("search_song", {"keyword": "Glaciaxion"}),
    ]
    
    for test_name, params in test_cases:
        print(f"\n测试 {test_name}...")
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            try:
                if test_name == "get_save":
                    await client.get_save(params["session_token"])
                elif test_name == "get_leaderboard":
                    await client.get_leaderboard(params["page"], params["limit"])
                elif test_name == "search_song":
                    await client.search_song(params["keyword"])
            except Exception as e:
                # 忽略错误，只记录时间
                pass
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            response_times.append(response_time)
            print(f"  第{i+1}次: {response_time:.2f}ms")
        
        # 计算统计数据
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            print(f"  平均响应时间: {avg_time:.2f}ms")
            print(f"  最小响应时间: {min_time:.2f}ms")
            print(f"  最大响应时间: {max_time:.2f}ms")
            print(f"  标准差: {std_dev:.2f}ms")
    
    await client.close()
    print("\nAPI性能测试完成！")

if __name__ == "__main__":
    asyncio.run(test_api_performance())