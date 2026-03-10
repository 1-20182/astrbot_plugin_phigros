# 基于 Python 3.10 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \n    git \n    wget \n    curl \n    libgomp1 \n    libglib2.0-0 \n    libnss3 \n    libnspr4 \n    libatk1.0-0 \n    libatk-bridge2.0-0 \n    libcups2 \n    libxkbcommon0 \n    libxcomposite1 \n    libxdamage1 \n    libxfixes3 \n    libxrandr2 \n    libgbm1 \n    libxcb1 \n    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /app/ILLUSTRATION /app/AVATAR /app/VideoClip /app/output/cache /app/output/api_cache /app/backups

# 设置环境变量
ENV PHIGROS_BASE_URL=https://r0semi.xtower.site/api/v1/open
ENV PHIGROS_ENABLE_RENDERER=true
ENV PHIGROS_ILLUSTRATION_PATH=/app/ILLUSTRATION
ENV PHIGROS_IMAGE_QUALITY=95
ENV PHIGROS_DEFAULT_TAPTAP_VERSION=cn
ENV PHIGROS_DEFAULT_SEARCH_LIMIT=5
ENV PHIGROS_DEFAULT_HISTORY_LIMIT=10

# 暴露端口（如果需要）
# EXPOSE 8080

# 运行命令
CMD ["python", "-m", "astrbot_plugin_phigros"]