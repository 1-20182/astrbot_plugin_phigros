"""
🎬 随机视频发送器

从 VideoClip 文件夹随机选择视频发送
"""

import os
import random
from pathlib import Path
from typing import Optional
from astrbot.api import logger


class VideoSender:
    """
    🎥 视频发送器
    
    随机挑选 Phigros 视频片段发送给群友~ 🎵
    """
    
    # 支持的视频格式
    SUPPORTED_FORMATS = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
    
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.video_dir = plugin_dir / "VideoClip"
        
    def get_random_video(self) -> Optional[Path]:
        """
        获取随机视频文件
        
        Returns:
            随机选择的视频路径，如果没有视频则返回 None
        """
        try:
            # 检查文件夹是否存在
            if not self.video_dir.exists():
                logger.error(f"❌ 视频文件夹不存在: {self.video_dir}")
                return None
            
            # 获取所有视频文件
            video_files = []
            for ext in self.SUPPORTED_FORMATS:
                video_files.extend(self.video_dir.glob(f"*{ext}"))
                video_files.extend(self.video_dir.glob(f"*{ext.upper()}"))
            
            if not video_files:
                logger.warning(f"⚠️ 视频文件夹为空: {self.video_dir}")
                return None
            
            # 随机选择一个
            selected = random.choice(video_files)
            logger.info(f"🎲 随机选择视频: {selected.name}")
            return selected
            
        except Exception as e:
            logger.error(f"❌ 获取随机视频失败: {e}")
            return None
    
    def get_video_list(self) -> list:
        """
        获取所有视频列表
        
        Returns:
            视频文件列表
        """
        try:
            if not self.video_dir.exists():
                return []
            
            video_files = []
            for ext in self.SUPPORTED_FORMATS:
                video_files.extend(self.video_dir.glob(f"*{ext}"))
                video_files.extend(self.video_dir.glob(f"*{ext.upper()}"))
            
            return sorted(video_files)
            
        except Exception as e:
            logger.error(f"❌ 获取视频列表失败: {e}")
            return []
    
    def get_video_info(self, video_path: Path) -> dict:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            stat = video_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            
            return {
                'name': video_path.stem,
                'filename': video_path.name,
                'size_mb': round(size_mb, 2),
                'path': str(video_path)
            }
        except Exception as e:
            logger.error(f"❌ 获取视频信息失败: {e}")
            return {
                'name': video_path.stem,
                'filename': video_path.name,
                'size_mb': 0,
                'path': str(video_path)
            }


# 便捷函数
def get_random_video_path(plugin_dir: Path) -> Optional[Path]:
    """获取随机视频的便捷函数"""
    sender = VideoSender(plugin_dir)
    return sender.get_random_video()
