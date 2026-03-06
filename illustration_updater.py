"""
🎨 曲绘自动更新器

> "曲绘不够？我来帮你自动下载！" ✨

自动检测 GitHub 仓库更新，下载最新曲绘
支持代理、断点续传、增量更新，超贴心的！
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from astrbot.api import logger


class IllustrationUpdater:
    """
    🎨 曲绘自动更新器
    
    帮你自动从 GitHub 下载最新曲绘
    支持代理、定时检查、增量更新
    """
    
    # GitHub 仓库信息
    GITHUB_REPO = "NanLiang-Works-Inc/Phigros_Resource"
    GITHUB_API_URL = "https://api.github.com/repos/{repo}/commits?path={path}&page=1&per_page=1"
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/{repo}/main/{path}"
    
    # 曲绘路径
    ILLUSTRATION_PATH = "ILLUSTRATION"
    
    def __init__(self, plugin_dir: Path, illustration_path: Optional[Path] = None):
        """
        初始化更新器
        
        Args:
            plugin_dir: 插件目录
            illustration_path: 曲绘存放路径（可选）
        """
        self.plugin_dir = Path(plugin_dir)
        self.illustration_path = illustration_path or (self.plugin_dir / self.ILLUSTRATION_PATH)
        
        # 确保目录存在
        self.illustration_path.mkdir(parents=True, exist_ok=True)
        
        # 状态文件路径
        self.state_file = self.plugin_dir / ".illustration_update_state.json"
        
        # 加载状态
        self._state = self._load_state()
        
        # 代理设置
        self.proxy: Optional[str] = None
        
        logger.info(f"🎨 曲绘更新器初始化完成: {self.illustration_path}")
    
    def _load_state(self) -> Dict:
        """加载更新状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载更新状态失败: {e}")
        
        return {
            "last_check": None,
            "last_commit_sha": None,
            "last_update": None,
            "total_downloaded": 0,
            "is_first_run": True
        }
    
    def _save_state(self):
        """保存更新状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存更新状态失败: {e}")
    
    def should_check_update(self) -> bool:
        """
        检查是否需要更新
        
        Returns:
            bool: 是否需要检查更新
        """
        # 首次运行，需要更新
        if self._state.get("is_first_run", True):
            logger.info("🎨 首次运行，需要下载曲绘！")
            return True
        
        # 检查上次检查时间
        last_check = self._state.get("last_check")
        if not last_check:
            return True
        
        try:
            last_check_time = datetime.fromisoformat(last_check)
            # 7天检查一次
            if datetime.now() - last_check_time >= timedelta(days=7):
                logger.info("🎨 已经7天没检查更新了，去看看有没有新曲绘~")
                return True
        except:
            return True
        
        return False
    
    async def _fetch_with_proxy(self, url: str, headers: Optional[Dict] = None) -> Optional[aiohttp.ClientResponse]:
        """
        带代理的 HTTP 请求
        
        Args:
            url: 请求URL
            headers: 请求头
            
        Returns:
            响应对象或None
        """
        # 尝试直接连接
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        return resp
        except Exception as e:
            logger.debug(f"直接连接失败: {e}")
        
        # 尝试代理
        if self.proxy:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            logger.info(f"✅ 通过代理成功访问: {url}")
                            return resp
            except Exception as e:
                logger.debug(f"代理连接失败: {e}")
        
        return None
    
    async def check_update(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        检查是否有更新
        
        Returns:
            (是否有更新, 最新commit SHA, 更新信息)
        """
        logger.info("🔍 正在检查曲绘更新...")
        
        api_url = self.GITHUB_API_URL.format(
            repo=self.GITHUB_REPO,
            path=self.ILLUSTRATION_PATH
        )
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Phigros-Plugin-Illustration-Updater"
        }
        
        try:
            resp = await self._fetch_with_proxy(api_url, headers)
            if not resp:
                logger.warning("❌ 无法连接到 GitHub，跳过更新检查")
                return False, None, None
            
            commits = await resp.json()
            if not commits:
                logger.info("ℹ️ 没有找到曲绘提交记录")
                return False, None, None
            
            latest_commit = commits[0]
            latest_sha = latest_commit.get("sha", "")
            commit_msg = latest_commit.get("commit", {}).get("message", "")
            commit_date = latest_commit.get("commit", {}).get("committer", {}).get("date", "")
            
            # 更新检查时间
            self._state["last_check"] = datetime.now().isoformat()
            
            # 检查是否有新提交
            last_sha = self._state.get("last_commit_sha")
            if last_sha == latest_sha:
                logger.info("✅ 曲绘已经是最新的啦！")
                self._save_state()
                return False, latest_sha, None
            
            # 有新更新
            update_info = f"最新提交: {commit_msg[:50]}... ({commit_date[:10]})"
            logger.info(f"🎉 发现新曲绘！{update_info}")
            
            return True, latest_sha, update_info
            
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            return False, None, None
    
    async def _get_file_list(self) -> List[Dict]:
        """
        获取曲绘文件列表
        
        Returns:
            文件列表
        """
        # 使用 GitHub API 获取目录内容
        api_url = f"https://api.github.com/repos/{self.GITHUB_REPO}/contents/{self.ILLUSTRATION_PATH}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Phigros-Plugin-Illustration-Updater"
        }
        
        try:
            resp = await self._fetch_with_proxy(api_url, headers)
            if not resp:
                return []
            
            files = await resp.json()
            if isinstance(files, list):
                return [f for f in files if f.get("type") == "file" and f.get("name", "").endswith(".png")]
            return []
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {e}")
            return []
    
    async def _download_file(self, file_info: Dict, progress_callback=None) -> bool:
        """
        下载单个文件
        
        Args:
            file_info: 文件信息
            progress_callback: 进度回调函数
            
        Returns:
            是否成功
        """
        file_name = file_info.get("name", "")
        download_url = file_info.get("download_url", "")
        
        if not file_name or not download_url:
            return False
        
        # 检查本地是否已存在且大小相同
        local_path = self.illustration_path / file_name
        if local_path.exists():
            local_size = local_path.stat().st_size
            remote_size = file_info.get("size", 0)
            if local_size == remote_size:
                logger.debug(f"⏭️ 跳过已存在的文件: {file_name}")
                return True
        
        try:
            resp = await self._fetch_with_proxy(download_url)
            if not resp:
                logger.warning(f"❌ 无法下载: {file_name}")
                return False
            
            # 保存文件
            content = await resp.read()
            async with aiofiles.open(local_path, 'wb') as f:
                await f.write(content)
            
            logger.debug(f"✅ 下载完成: {file_name}")
            
            if progress_callback:
                await progress_callback(file_name)
            
            return True
            
        except Exception as e:
            logger.warning(f"下载失败 {file_name}: {e}")
            return False
    
    async def update_illustrations(self, progress_callback=None) -> Tuple[int, int, str]:
        """
        更新曲绘
        
        Args:
            progress_callback: 进度回调函数 (file_name) -> None
            
        Returns:
            (成功数, 失败数, 状态信息)
        """
        logger.info("🚀 开始更新曲绘...")
        
        # 检查更新
        has_update, latest_sha, update_info = await self.check_update()
        
        if not has_update and not self._state.get("is_first_run", True):
            return 0, 0, "已经是最新版本"
        
        # 获取文件列表
        files = await self._get_file_list()
        if not files:
            logger.warning("⚠️ 没有找到曲绘文件")
            return 0, 0, "没有找到曲绘文件"
        
        logger.info(f"📦 发现 {len(files)} 个曲绘文件")
        
        # 下载文件
        success_count = 0
        fail_count = 0
        
        # 限制并发数
        semaphore = asyncio.Semaphore(5)
        
        async def download_with_limit(file_info):
            nonlocal success_count, fail_count
            async with semaphore:
                if await self._download_file(file_info, progress_callback):
                    success_count += 1
                else:
                    fail_count += 1
        
        # 并发下载
        await asyncio.gather(*[download_with_limit(f) for f in files])
        
        # 更新状态
        if success_count > 0:
            self._state["last_commit_sha"] = latest_sha
            self._state["last_update"] = datetime.now().isoformat()
            self._state["total_downloaded"] = self._state.get("total_downloaded", 0) + success_count
            self._state["is_first_run"] = False
            self._save_state()
        
        status = f"成功: {success_count}, 失败: {fail_count}"
        if update_info:
            status = f"{update_info}\n{status}"
        
        logger.info(f"🎉 曲绘更新完成！{status}")
        return success_count, fail_count, status
    
    def set_proxy(self, proxy_url: str):
        """
        设置代理
        
        Args:
            proxy_url: 代理地址，如 "http://127.0.0.1:7890"
        """
        self.proxy = proxy_url
        logger.info(f"🌐 已设置代理: {proxy_url}")
    
    def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        # 统计本地曲绘数量
        local_count = len(list(self.illustration_path.glob("*.png")))
        
        return {
            "local_count": local_count,
            "last_check": self._state.get("last_check"),
            "last_update": self._state.get("last_update"),
            "total_downloaded": self._state.get("total_downloaded", 0),
            "is_first_run": self._state.get("is_first_run", True)
        }


# 便捷函数
async def auto_update_illustrations(plugin_dir: Path, illustration_path: Optional[Path] = None, 
                                   proxy: Optional[str] = None) -> Tuple[int, int, str]:
    """
    自动更新曲绘（便捷函数）
    
    Args:
        plugin_dir: 插件目录
        illustration_path: 曲绘路径（可选）
        proxy: 代理地址（可选）
        
    Returns:
        (成功数, 失败数, 状态信息)
    """
    updater = IllustrationUpdater(plugin_dir, illustration_path)
    
    if proxy:
        updater.set_proxy(proxy)
    
    # 检查是否需要更新
    if not updater.should_check_update():
        stats = updater.get_stats()
        return 0, 0, f"跳过检查（上次检查: {stats['last_check'][:10] if stats['last_check'] else '无'}）"
    
    return await updater.update_illustrations()
