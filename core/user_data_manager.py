"""
👤 用户数据管理器模块

管理用户绑定数据，支持自动备份和恢复功能
"""

import json
import shutil
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

from astrbot.api import logger


class UserDataManager:
    """
    👤 用户数据管理器
    
    帮你保管 sessionToken，绑定一次，永久免输！
    数据存在本地，安全又可靠~ 🔒
    支持自动备份功能，防止数据丢失
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_file = data_dir / "user_data.json"
        self.backup_dir = data_dir / "backups"
        self._data: Dict[str, Dict[str, str]] = {}
        self._lock = None  # 异步锁，在 initialize 中初始化
        self._load_data()
        # 初始化备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化异步锁"""
        import asyncio
        self._lock = asyncio.Lock()

    def _load_data(self):
        """从文件加载用户数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.info(f"已加载 {len(self._data)} 个用户的数据")
            except Exception as e:
                logger.error(f"加载用户数据失败: {e}")
                # 尝试从备份恢复
                if self._restore_from_backup():
                    logger.info("从备份恢复数据成功")
                else:
                    self._data = {}
        else:
            # 尝试从备份恢复
            if self._restore_from_backup():
                logger.info("从备份恢复数据成功")
            else:
                self._data = {}

    def _create_backup(self):
        """创建用户数据备份"""
        try:
            if not self.data_file.exists():
                return
            
            # 确保备份目录存在
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成备份文件名，包含时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"user_data_{timestamp}.json"
            
            # 复制数据到备份文件
            shutil.copy2(self.data_file, backup_file)
            logger.info(f"✅ 创建用户数据备份: {backup_file.name}")
            
            # 清理旧备份
            self._clean_old_backups()
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
    
    def _clean_old_backups(self):
        """清理旧备份，保留最近7天的备份"""
        try:
            # 获取所有备份文件
            backup_files = []
            for file in self.backup_dir.iterdir():
                if file.is_file() and file.name.startswith("user_data_") and file.name.endswith(".json"):
                    backup_files.append(file)
            
            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 保留最近7天的备份
            days_to_keep = 7
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            for file in backup_files:
                if file.stat().st_mtime < cutoff_time:
                    os.remove(file)
                    logger.info(f"🗑️ 清理旧备份: {file.name}")
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
    def _restore_from_backup(self):
        """从最新备份恢复数据"""
        try:
            # 获取所有备份文件
            backup_files = []
            for file in self.backup_dir.iterdir():
                if file.is_file() and file.name.startswith("user_data_") and file.name.endswith(".json"):
                    backup_files.append(file)
            
            if not backup_files:
                logger.warning("没有找到备份文件")
                return False
            
            # 按修改时间排序，取最新的备份
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_backup = backup_files[0]
            
            logger.info(f"🔄 从备份恢复数据: {latest_backup.name}")
            
            # 读取备份数据
            with open(latest_backup, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # 保存到主文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            # 重新加载数据
            self._data = backup_data
            logger.info(f"✅ 从备份恢复成功，加载了 {len(self._data)} 个用户的数据")
            return True
        except Exception as e:
            logger.error(f"从备份恢复失败: {e}")
            return False

    def _save_data(self):
        """保存用户数据到文件"""
        try:
            # 确保目录存在
            self.data_dir.mkdir(parents=True, exist_ok=True)
            # 设置文件权限为仅所有者可读写 (Unix/Linux)
            if os.name != 'nt':  # 非 Windows 系统
                import stat
                old_umask = os.umask(0o077)
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                # 设置文件权限
                if os.name != 'nt':
                    os.chmod(self.data_file, stat.S_IRUSR | stat.S_IWUSR)
                
                # 创建备份
                self._create_backup()
            finally:
                if os.name != 'nt':
                    os.umask(old_umask)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")

    def _encrypt_token(self, token: str) -> str:
        """对 token 进行简单混淆（非加密，仅增加读取难度）"""
        # 使用简单的 base64 编码 + 前缀混淆
        import base64
        encoded = base64.b64encode(token.encode()).decode()
        return f"enc:{encoded}"

    def _decrypt_token(self, encrypted: str) -> str:
        """解密 token"""
        import base64
        if encrypted.startswith("enc:"):
            encoded = encrypted[4:]
            return base64.b64decode(encoded.encode()).decode()
        return encrypted  # 兼容旧数据

    async def bind_user(self, platform: str, user_id: str, session_token: str, taptap_version: str = "cn") -> bool:
        """
        绑定用户数据

        Args:
            platform: 平台标识 (如 qq, wechat 等)
            user_id: 用户ID
            session_token: Phigros sessionToken
            taptap_version: TapTap 版本 (cn/global)

        Returns:
            bool: 是否绑定成功
        """
        async with self._lock:
            key = f"{platform}:{user_id}"
            self._data[key] = {
                "session_token": self._encrypt_token(session_token),
                "taptap_version": taptap_version,
                "bind_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_data()
        return True

    async def unbind_user(self, platform: str, user_id: str) -> bool:
        """
        解绑用户数据

        Args:
            platform: 平台标识
            user_id: 用户ID

        Returns:
            bool: 是否解绑成功
        """
        async with self._lock:
            key = f"{platform}:{user_id}"
            if key in self._data:
                del self._data[key]
                self._save_data()
                return True
            return False

    def get_user_data(self, platform: str, user_id: str) -> Optional[Dict[str, str]]:
        """
        获取用户绑定的数据

        Args:
            platform: 平台标识
            user_id: 用户ID

        Returns:
            Dict 或 None: 包含 session_token 和 taptap_version 的字典
        """
        key = f"{platform}:{user_id}"
        data = self._data.get(key)
        if data:
            # 解密 token
            return {
                "session_token": self._decrypt_token(data["session_token"]),
                "taptap_version": data.get("taptap_version", "cn"),
                "bind_time": data.get("bind_time", "")
            }
        return None

    def is_user_bound(self, platform: str, user_id: str) -> bool:
        """检查用户是否已绑定"""
        key = f"{platform}:{user_id}"
        return key in self._data
