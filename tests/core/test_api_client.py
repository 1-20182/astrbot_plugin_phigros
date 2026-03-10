"""
测试API客户端模块
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
import sys

# 模拟astrbot模块
class MockLogger:
    def info(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
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
from core.api_client import PhigrosAPIClient, RateLimiter, retry


class TestRateLimiter(unittest.TestCase):
    """测试速率限制器"""

    async def test_rate_limiter_basic(self):
        """测试速率限制器的基本功能"""
        import time
        limiter = RateLimiter(max_requests=2, window_seconds=1)  # 每秒2个请求
        await limiter.initialize()
        
        # 第一个请求应该通过
        self.assertTrue(await limiter.acquire())
        # 第二个请求应该通过
        self.assertTrue(await limiter.acquire())
        # 第三个请求应该被限制
        self.assertFalse(await limiter.acquire())
        
        # 等待时间窗口过去
        time.sleep(1.1)
        # 新的时间窗口，应该可以通过
        self.assertTrue(await limiter.acquire())
    
    def test_rate_limiter_basic_sync(self):
        """同步测试速率限制器的基本功能"""
        asyncio.run(self.test_rate_limiter_basic())


class TestRetryDecorator(unittest.TestCase):
    """测试重试装饰器"""

    async def test_retry_success(self):
        """测试重试成功的情况"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "Success"
        
        result = await func()
        self.assertEqual(result, "Success")
        self.assertEqual(call_count, 3)
    
    async def test_retry_failure(self):
        """测试重试失败的情况"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        async def func():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent error")
        
        with self.assertRaises(Exception):
            await func()
        self.assertEqual(call_count, 3)
    
    def test_retry_success_sync(self):
        """同步测试重试成功的情况"""
        asyncio.run(self.test_retry_success())
    
    def test_retry_failure_sync(self):
        """同步测试重试失败的情况"""
        asyncio.run(self.test_retry_failure())


class TestPhigrosAPIClient(unittest.TestCase):
    """测试Phigros API客户端"""

    async def test_get_save_success(self):
        """测试get_save方法成功的情况"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "save": {
                    "user": {
                        "nickname": "Test User",
                        "avatar": "https://example.com/avatar.png"
                    },
                    "summaryParsed": {
                        "playerId": "12345"
                    }
                },
                "rks": {
                    "totalRks": 15.5
                }
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 创建API客户端
            client = PhigrosAPIClient(
                base_url="https://api.example.com",
                api_token="test_token"
            )
            await client.initialize()
            
            # 调用方法
            result = await client.get_save("session_token")
            
            # 验证结果
            self.assertIsNotNone(result)
            
            await client.terminate()
    
    async def test_get_save_failure(self):
        """测试get_save方法失败的情况"""
        # 模拟失败响应
        mock_response = Mock()
        mock_response.status = 500
        mock_response.json.return_value = {
            "code": 500,
            "message": "Internal server error"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 创建API客户端
            client = PhigrosAPIClient(
                base_url="https://api.example.com",
                api_token="test_token"
            )
            await client.initialize()
            
            # 调用方法，应该抛出异常
            with self.assertRaises(Exception):
                await client.get_save("session_token")
            
            await client.terminate()
    
    def test_get_save_success_sync(self):
        """同步测试get_save方法成功的情况"""
        asyncio.run(self.test_get_save_success())
    
    def test_get_save_failure_sync(self):
        """同步测试get_save方法失败的情况"""
        asyncio.run(self.test_get_save_failure())


if __name__ == '__main__':
    unittest.main()
