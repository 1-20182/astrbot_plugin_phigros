"""
📊 监控模块

提供API调用监控和指标统计功能，帮助你了解插件的运行状态！
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from astrbot.api import logger


class APIMonitor:
    """
    API 监控器
    
    统计API调用的成功率、耗时等指标
    """
    
    def __init__(self, window_seconds: int = 3600):
        """
        Args:
            window_seconds: 统计时间窗口（秒）
        """
        self.window_seconds = window_seconds
        self._lock = asyncio.Lock()
        self._calls: Dict[str, list] = {}
        self._errors: Dict[str, int] = {}
        self._total_calls: Dict[str, int] = {}
        self._total_errors: Dict[str, int] = {}
    
    async def record_call(self, endpoint: str, success: bool, duration: float):
        """
        记录API调用
        
        Args:
            endpoint: API端点
            success: 是否成功
            duration: 耗时（秒）
        """
        async with self._lock:
            # 清理过期数据
            await self._cleanup_old_data()
            
            # 记录调用
            if endpoint not in self._calls:
                self._calls[endpoint] = []
            if endpoint not in self._errors:
                self._errors[endpoint] = 0
            if endpoint not in self._total_calls:
                self._total_calls[endpoint] = 0
            if endpoint not in self._total_errors:
                self._total_errors[endpoint] = 0
            
            self._calls[endpoint].append({
                "timestamp": datetime.now(),
                "success": success,
                "duration": duration
            })
            
            self._total_calls[endpoint] += 1
            
            if not success:
                self._errors[endpoint] += 1
                self._total_errors[endpoint] += 1
    
    async def _cleanup_old_data(self):
        """
        清理过期数据
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        for endpoint in list(self._calls.keys()):
            # 过滤出未过期的调用
            self._calls[endpoint] = [
                call for call in self._calls[endpoint]
                if call["timestamp"] > cutoff
            ]
            
            # 重新计算错误数
            self._errors[endpoint] = sum(
                1 for call in self._calls[endpoint] if not call["success"]
            )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        获取监控指标
        
        Returns:
            监控指标字典
        """
        async with self._lock:
            # 清理过期数据
            await self._cleanup_old_data()
            
            metrics = {}
            
            for endpoint in self._calls:
                calls = self._calls[endpoint]
                if not calls:
                    continue
                
                total = len(calls)
                errors = self._errors[endpoint]
                successes = total - errors
                
                # 计算成功率
                success_rate = (successes / total * 100) if total > 0 else 0
                
                # 计算平均耗时
                avg_duration = sum(call["duration"] for call in calls) / total if total > 0 else 0
                
                # 计算最大和最小耗时
                max_duration = max(call["duration"] for call in calls) if calls else 0
                min_duration = min(call["duration"] for call in calls) if calls else 0
                
                metrics[endpoint] = {
                    "total_calls": total,
                    "successes": successes,
                    "errors": errors,
                    "success_rate": round(success_rate, 2),
                    "avg_duration": round(avg_duration, 3),
                    "max_duration": round(max_duration, 3),
                    "min_duration": round(min_duration, 3),
                    "total_calls_all_time": self._total_calls[endpoint],
                    "total_errors_all_time": self._total_errors[endpoint]
                }
            
            # 计算总体指标
            total_all = sum(len(calls) for calls in self._calls.values())
            errors_all = sum(self._errors.values())
            successes_all = total_all - errors_all
            
            if total_all > 0:
                overall_success_rate = (successes_all / total_all * 100)
                overall_avg_duration = sum(
                    sum(call["duration"] for call in calls)
                    for calls in self._calls.values()
                ) / total_all
            else:
                overall_success_rate = 0
                overall_avg_duration = 0
            
            metrics["overall"] = {
                "total_calls": total_all,
                "successes": successes_all,
                "errors": errors_all,
                "success_rate": round(overall_success_rate, 2),
                "avg_duration": round(overall_avg_duration, 3),
                "total_calls_all_time": sum(self._total_calls.values()),
                "total_errors_all_time": sum(self._total_errors.values())
            }
            
            return metrics
    
    async def reset_metrics(self):
        """
        重置监控指标
        """
        async with self._lock:
            self._calls.clear()
            self._errors.clear()
            # 保留总调用数和总错误数
    
    async def log_metrics(self):
        """
        记录监控指标到日志
        """
        metrics = await self.get_metrics()
        
        if not metrics:
            logger.info("📊 暂无监控数据")
            return
        
        # 记录总体指标
        overall = metrics.pop("overall", {})
        if overall:
            logger.info(
                f"📊 API 监控指标（总体）: "
                f"成功率: {overall['success_rate']}%, "
                f"平均耗时: {overall['avg_duration']}s, "
                f"总调用: {overall['total_calls_all_time']}, "
                f"总错误: {overall['total_errors_all_time']}"
            )
        
        # 记录各端点指标
        for endpoint, data in metrics.items():
            logger.info(
                f"📊 API 监控指标 ({endpoint}): "
                f"成功率: {data['success_rate']}%, "
                f"平均耗时: {data['avg_duration']}s, "
                f"调用: {data['total_calls']}, "
                f"错误: {data['errors']}"
            )


# 全局监控器实例
api_monitor = APIMonitor()


def monitor_api_call(endpoint: str = None):
    """
    API调用监控装饰器
    
    Args:
        endpoint: API端点，如果为None则从方法参数中获取
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            
            # 尝试从参数中获取endpoint
            actual_endpoint = endpoint
            if actual_endpoint is None:
                # 检查是否有endpoint参数
                if 'endpoint' in kwargs:
                    actual_endpoint = kwargs['endpoint']
                # 或者检查位置参数
                elif len(args) > 1 and isinstance(args[1], str) and args[1].startswith('/'):
                    actual_endpoint = args[1]
                else:
                    actual_endpoint = "unknown"
            
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                await api_monitor.record_call(actual_endpoint, success, duration)
        
        return wrapper
    
    return decorator