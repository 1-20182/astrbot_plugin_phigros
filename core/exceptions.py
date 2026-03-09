"""
🎯 自定义异常类模块

包含 Phigros Query 插件所有的自定义异常类，让错误处理更清晰！
"""


class PhigrosError(Exception):
    """Phigros 插件基异常类，所有自定义异常的父类"""

    def __init__(self, message: str = "发生未知错误", *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self) -> str:
        return f"⚠️  {self.message}"


class PhigrosAPIError(PhigrosError):
    """API 异常，用于处理 API 返回的错误"""

    def __init__(
        self,
        message: str = "API 请求失败",
        status_code: int = None,
        endpoint: str = None,
        *args
    ):
        super().__init__(message, *args)
        self.status_code = status_code
        self.endpoint = endpoint

    def __str__(self) -> str:
        if self.status_code and self.endpoint:
            return f"🔌 API错误: {self.message} (状态码: {self.status_code}, 端点: {self.endpoint})"
        elif self.status_code:
            return f"🔌 API错误: {self.message} (状态码: {self.status_code})"
        return f"🔌 API错误: {self.message}"


class RenderError(PhigrosError):
    """渲染异常，用于处理图片渲染相关的错误"""

    def __init__(
        self,
        message: str = "图片渲染失败",
        renderer_name: str = None,
        *args
    ):
        super().__init__(message, *args)
        self.renderer_name = renderer_name

    def __str__(self) -> str:
        if self.renderer_name:
            return f"🎨 渲染错误: {self.message} (渲染器: {self.renderer_name})"
        return f"🎨 渲染错误: {self.message}"


class CacheError(PhigrosError):
    """缓存异常，用于处理缓存相关的错误"""

    def __init__(
        self,
        message: str = "缓存操作失败",
        cache_key: str = None,
        *args
    ):
        super().__init__(message, *args)
        self.cache_key = cache_key

    def __str__(self) -> str:
        if self.cache_key:
            return f"📦 缓存错误: {self.message} (键: {self.cache_key})"
        return f"📦 缓存错误: {self.message}"


class AuthError(PhigrosError):
    """认证异常，用于处理登录和认证相关的错误"""

    def __init__(
        self,
        message: str = "认证失败",
        auth_type: str = None,
        *args
    ):
        super().__init__(message, *args)
        self.auth_type = auth_type

    def __str__(self) -> str:
        if self.auth_type:
            return f"🔐 认证错误: {self.message} (类型: {self.auth_type})"
        return f"🔐 认证错误: {self.message}"


class ValidationError(PhigrosError):
    """验证异常，用于处理参数验证相关的错误"""

    def __init__(
        self,
        message: str = "参数验证失败",
        param_name: str = None,
        param_value = None,
        *args
    ):
        super().__init__(message, *args)
        self.param_name = param_name
        self.param_value = param_value

    def __str__(self) -> str:
        if self.param_name and self.param_value is not None:
            return f"✅ 验证错误: {self.message} (参数: {self.param_name} = {self.param_value})"
        elif self.param_name:
            return f"✅ 验证错误: {self.message} (参数: {self.param_name})"
        return f"✅ 验证错误: {self.message}"


class NetworkError(PhigrosError):
    """网络异常，用于处理网络连接相关的错误"""

    def __init__(
        self,
        message: str = "网络连接失败",
        url: str = None,
        *args
    ):
        super().__init__(message, *args)
        self.url = url

    def __str__(self) -> str:
        if self.url:
            return f"🌐 网络错误: {self.message} (URL: {self.url})"
        return f"🌐 网络错误: {self.message}"


class RateLimitError(PhigrosAPIError):
    """限流异常，专门用于处理 API 限流的情况"""

    def __init__(
        self,
        message: str = "API 请求频率过高，请稍后重试",
        retry_after: int = None,
        *args
    ):
        super().__init__(message, 429, *args)
        self.retry_after = retry_after

    def __str__(self) -> str:
        if self.retry_after:
            return f"⏰ 限流错误: {self.message} (建议等待 {self.retry_after} 秒后重试)"
        return f"⏰ 限流错误: {self.message}"
