"""
测试命令模块
"""

import unittest
from unittest.mock import Mock, patch

# 模拟astrbot模块
class MockAstrMessageEvent:
    def __init__(self):
        self.get_platform_name = lambda: "qq"
        self.get_sender_id = lambda: "123456"
        self.plain_result = lambda msg: msg

# 模拟导入
with patch('commands.auth_commands.filter'):
    with patch('commands.auth_commands.AstrMessageEvent', MockAstrMessageEvent):
        with patch('commands.query_commands.filter'):
            with patch('commands.query_commands.AstrMessageEvent', MockAstrMessageEvent):
                with patch('commands.other_commands.filter'):
                    with patch('commands.other_commands.AstrMessageEvent', MockAstrMessageEvent):
                        from commands.auth_commands import AuthCommands
                        from commands.query_commands import QueryCommands
                        from commands.other_commands import OtherCommands


class TestAuthCommands(unittest.TestCase):
    """测试认证命令"""

    def setUp(self):
        """设置测试环境"""
        self.plugin = Mock()
        self.plugin.user_data = Mock()
        self.plugin.API_LOGIN_AVAILABLE = True
        self.auth_commands = AuthCommands(self.plugin)
    
    @patch('commands.auth_commands.TapTapLoginManagerAPI')
    async def test_bind_user(self, mock_login_manager):
        """测试绑定用户命令"""
        # 模拟事件对象
        event = Mock()
        event.get_platform_name.return_value = "qq"
        event.get_sender_id.return_value = "123456"
        event.plain_result = lambda msg: msg
        
        # 模拟用户数据管理器
        self.plugin.user_data.bind_user.return_value = True
        
        # 调用方法
        result = await self.auth_commands.bind_user(event, "session_token")
        
        # 验证结果
        self.assertIn("绑定成功", result)
        self.plugin.user_data.bind_user.assert_called_once_with("qq", "123456", "session_token", "cn")
    
    async def test_unbind_user(self):
        """测试解绑用户命令"""
        # 模拟事件对象
        event = Mock()
        event.get_platform_name.return_value = "qq"
        event.get_sender_id.return_value = "123456"
        event.plain_result = lambda msg: msg
        
        # 模拟用户数据管理器
        self.plugin.user_data.unbind_user.return_value = True
        
        # 调用方法
        result = await self.auth_commands.unbind_user(event)
        
        # 验证结果
        self.assertIn("解绑成功", result)
        self.plugin.user_data.unbind_user.assert_called_once_with("qq", "123456")


class TestQueryCommands(unittest.TestCase):
    """测试查询命令"""

    def setUp(self):
        """设置测试环境"""
        self.plugin = Mock()
        self.plugin.user_data = Mock()
        self.plugin.api_client = Mock()
        self.plugin.renderer = Mock()
        self.query_commands = QueryCommands(self.plugin)
    
    async def test_get_save(self):
        """测试获取存档命令"""
        # 模拟事件对象
        event = Mock()
        event.get_platform_name.return_value = "qq"
        event.get_sender_id.return_value = "123456"
        event.plain_result = lambda msg: msg
        
        # 模拟用户数据
        self.plugin.user_data.get_user_data.return_value = {
            "session_token": "test_token",
            "taptap_version": "cn"
        }
        
        # 模拟API客户端
        self.plugin.api_client.get_save.return_value = {
            "data": {
                "save": {
                    "user": {
                        "nickname": "Test User"
                    }
                }
            }
        }
        
        # 调用方法
        result = await self.query_commands.get_save(event)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.plugin.api_client.get_save.assert_called_once_with("test_token")


class TestOtherCommands(unittest.TestCase):
    """测试其他命令"""

    def setUp(self):
        """设置测试环境"""
        self.plugin = Mock()
        self.other_commands = OtherCommands(self.plugin)
    
    async def test_get_help(self):
        """测试获取帮助命令"""
        # 模拟事件对象
        event = Mock()
        event.plain_result = lambda msg: msg
        
        # 调用方法
        result = await self.other_commands.get_help(event)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIn("帮助", result)


if __name__ == '__main__':
    unittest.main()
