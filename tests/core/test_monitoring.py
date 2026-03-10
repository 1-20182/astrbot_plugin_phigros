"""
测试监控模块
"""

import unittest
import asyncio
import sys

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
from core.monitoring import APIMonitor, monitor_api_call


class TestAPIMonitor(unittest.TestCase):
    """测试API监控器"""

    def setUp(self):
        """设置测试环境"""
        self.monitor = APIMonitor()
    
    async def test_record_call(self):
        """测试记录API调用"""
        # 记录成功调用
        await self.monitor.record_call("/test", True, 0.1)
        # 记录失败调用
        await self.monitor.record_call("/test", False, 0.2)
        
        # 获取监控数据
        metrics = await self.monitor.get_metrics()
        
        # 验证监控数据
        self.assertIn("/test", metrics)
        self.assertEqual(metrics["/test"]["total_calls"], 2)
        self.assertEqual(metrics["/test"]["errors"], 1)
        self.assertGreater(metrics["/test"]["avg_duration"], 0)
    
    async def test_get_metrics(self):
        """测试获取监控指标"""
        # 记录多个调用
        await self.monitor.record_call("/test1", True, 0.05)
        await self.monitor.record_call("/test2", False, 0.1)
        
        # 获取监控数据
        metrics = await self.monitor.get_metrics()
        
        # 验证监控数据
        self.assertIn("/test1", metrics)
        self.assertIn("/test2", metrics)
        self.assertIn("overall", metrics)
        
        # 验证总体指标
        overall = metrics["overall"]
        self.assertEqual(overall["total_calls_all_time"], 2)
        self.assertEqual(overall["total_errors_all_time"], 1)
        self.assertEqual(overall["success_rate"], 50.0)
    
    def test_record_call_sync(self):
        """同步测试记录API调用"""
        asyncio.run(self.test_record_call())
    
    def test_get_metrics_sync(self):
        """同步测试获取监控指标"""
        asyncio.run(self.test_get_metrics())
    
    async def test_log_metrics(self):
        """测试记录监控指标"""
        # 记录一些调用
        await self.monitor.record_call("/test", True, 0.05)
        
        # 记录指标（应该不会抛出异常）
        try:
            await self.monitor.log_metrics()
        except Exception as e:
            self.fail(f"log_metrics() raised {e} unexpectedly")
    
    def test_log_metrics_sync(self):
        """同步测试记录监控指标"""
        asyncio.run(self.test_log_metrics())


if __name__ == '__main__':
    unittest.main()
