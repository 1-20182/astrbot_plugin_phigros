"""
存档管理器 - AstrBot 适配版本
基于 phi-plugin 的 SaveManager.js 移植
支持国服和国际服
"""
import base64
import requests
from typing import Dict, List, Optional, Tuple
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class SaveManager:
    """Phigros 存档管理器（国服）"""
    
    # LeanCloud 配置
    BASE_URL = "https://rak3ffdi.cloud.tds1.tapapis.cn/1.1"
    CLIENT_ID = "rAK3FfdieFob2Nn8Am"
    CLIENT_KEY = "Qr9AEqtuoSVS3zeD6iVbM4ZC0AtkJcQ89tywVyi0"
    
    # AES 密钥和 IV（从 JavaScript Buffer 转换，负数转为无符号字节）
    KEY = bytes([232, 150, 154, 210, 165, 64, 37, 155, 151, 145, 144, 139, 136, 230, 191, 3, 30, 109, 33, 149, 110, 250, 214, 138, 80, 221, 85, 214, 122, 176, 146, 75])
    IV = bytes([42, 79, 240, 138, 200, 13, 99, 7, 0, 87, 197, 149, 24, 200, 50, 83])
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "X-LC-Id": self.CLIENT_ID,
            "X-LC-Key": self.CLIENT_KEY,
            "User-Agent": "LeanCloud-CSharp-SDK/1.0.3",
            "Accept": "application/json"
        })
    
    def _make_request(self, method: str, endpoint: str, session_token: str = None, data: Dict = None) -> Dict:
        """发送请求到 LeanCloud"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {}
        if session_token:
            headers["X-LC-Session"] = session_token
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            else:
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")
    
    def get_player_id(self, session_token: str) -> Dict:
        """获取玩家 ID"""
        return self._make_request("GET", "/users/me", session_token)
    
    def save_array(self, session_token: str) -> List[Dict]:
        """获取存档列表"""
        response = self._make_request("GET", "/classes/_GameSave", session_token)
        return response.get("results", [])
    
    def save_check(self, session_token: str) -> List[Dict]:
        """
        检查并获取存档信息
        
        Args:
            session_token: sessionToken
            
        Returns:
            存档信息列表
            
        Raises:
            Exception: 存档列表为空时抛出异常
        """
        array = self.save_array(session_token)
        
        if not array:
            raise Exception("TK 对应存档列表为空，请检查是否同步存档QAQ！")
        
        results = []
        player_info = self.get_player_id(session_token)
        
        for item in array:
            # 解析 summary
            summary = item.get("summary", {})
            if isinstance(summary, str):
                try:
                    import json
                    summary = json.loads(summary)
                except:
                    summary = {}
            
            # 合并玩家信息
            item["summary"] = summary
            item.update(player_info)
            
            # 格式化更新时间
            updated_at = item.get("updatedAt", "")
            if updated_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    item["updatedAt"] = dt.strftime("%Y %b.%d %H:%M:%S")
                except:
                    pass
            
            # 设置 PlayerId
            item["PlayerId"] = player_info.get("nickname", "Unknown")
            
            if item.get("gameFile"):
                results.append(item)
        
        return results
    
    def decrypt(self, data: bytes) -> bytes:
        """
        解密存档数据
        
        Args:
            data: 加密的数据（base64 编码）
            
        Returns:
            解密后的数据
        """
        try:
            # 如果输入是 base64 字符串，先解码
            if isinstance(data, str):
                data = base64.b64decode(data)
            
            cipher = AES.new(self.KEY, AES.MODE_CBC, self.IV)
            decrypted = cipher.decrypt(data)
            
            # 去除 PKCS7 填充
            try:
                decrypted = unpad(decrypted, AES.block_size)
            except:
                pass  # 可能没有填充
            
            return decrypted
        except Exception as e:
            raise Exception(f"解密失败: {str(e)}")
    
    def encrypt(self, data: bytes) -> bytes:
        """
        加密数据
        
        Args:
            data: 原始数据
            
        Returns:
            加密后的数据
        """
        try:
            from Crypto.Util.Padding import pad
            
            cipher = AES.new(self.KEY, AES.MODE_CBC, self.IV)
            padded_data = pad(data, AES.block_size)
            encrypted = cipher.encrypt(padded_data)
            
            return encrypted
        except Exception as e:
            raise Exception(f"加密失败: {str(e)}")
    
    def download_save(self, url: str) -> bytes:
        """
        下载存档文件
        
        Args:
            url: 存档下载链接
            
        Returns:
            存档文件内容（加密）
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise Exception(f"下载存档失败: {str(e)}")


class SaveManagerGB(SaveManager):
    """Phigros 存档管理器（国际服）"""
    
    # 国际服 LeanCloud 配置
    BASE_URL = "https://kviehlel.cloud.ap-sg.tapapis.com/1.1"
    CLIENT_ID = "kviehleldgxsagpozb"
    CLIENT_KEY = "tG9CTm0LDD736k9HMM9lBZrbeBGRmUkjSfNLDNib"


# 便捷函数
def get_save_manager(use_global: bool = False) -> SaveManager:
    """
    获取存档管理器实例
    
    Args:
        use_global: 是否使用国际服
        
    Returns:
        SaveManager 实例
    """
    if use_global:
        return SaveManagerGB()
    return SaveManager()
