"""
🔒 安全模块

包含加密、解密和安全相关的工具函数，保护敏感信息！
"""
import os
import json
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Optional

from astrbot.api import logger


class TokenEncryptor:
    """
    🔐 API 令牌加密器
    
    使用 Fernet 对称加密算法加密和解密 API 令牌
    """
    
    def __init__(self, key_file: Path):
        """
        初始化加密器
        
        Args:
            key_file: 密钥文件路径
        """
        self.key_file = key_file
        self._key = self._load_or_generate_key()
        self._cipher = Fernet(self._key)
    
    def _load_or_generate_key(self) -> bytes:
        """
        加载或生成加密密钥
        
        Returns:
            bytes: 加密密钥
        """
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"加载密钥文件失败: {e}")
                # 生成新密钥
                return self._generate_key()
        else:
            return self._generate_key()
    
    def _generate_key(self) -> bytes:
        """
        生成新的加密密钥
        
        Returns:
            bytes: 新的加密密钥
        """
        key = Fernet.generate_key()
        # 确保目录存在
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        # 保存密钥
        try:
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限为 600
            os.chmod(self.key_file, 0o600)
            logger.info(f"✅ 生成并保存新的加密密钥: {self.key_file}")
        except Exception as e:
            logger.error(f"保存密钥文件失败: {e}")
        return key
    
    def encrypt(self, token: str) -> str:
        """
        加密 API 令牌
        
        Args:
            token: 原始 API 令牌
            
        Returns:
            str: 加密后的令牌
        """
        try:
            encrypted = self._cipher.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"加密令牌失败: {e}")
            return token
    
    def decrypt(self, encrypted_token: str) -> str:
        """
        解密 API 令牌
        
        Args:
            encrypted_token: 加密后的令牌
            
        Returns:
            str: 原始 API 令牌
        """
        try:
            decrypted = self._cipher.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密令牌失败: {e}")
            return encrypted_token


def get_encryptor(config_dir: Path) -> TokenEncryptor:
    """
    获取令牌加密器实例
    
    Args:
        config_dir: 配置目录路径
        
    Returns:
        TokenEncryptor: 加密器实例
    """
    key_file = config_dir / "encryption_key.bin"
    return TokenEncryptor(key_file)
