#!/bin/bash

# Phigros Query 插件 Ubuntu 安装脚本
# 用法: chmod +x install.sh && ./install.sh [--no-venv]
# 选项:
#   --no-venv  不使用虚拟环境（不推荐，除非你知道你在做什么）

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  Phigros Query 插件 - Ubuntu 安装脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 解析参数
USE_VENV=true
if [ "$1" == "--no-venv" ]; then
    USE_VENV=false
    echo -e "${YELLOW}⚠️  警告: 已禁用虚拟环境${NC}"
    echo "这可能会与系统 Python 包产生冲突"
    echo ""
fi

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
   echo -e "${YELLOW}⚠️  警告: 正在使用 root 用户运行此脚本${NC}"
   echo ""
   echo "这可能会导致以下问题:"
   echo "  • 虚拟环境的所有者变为 root，普通用户无法访问"
   echo "  • 文件权限问题"
   echo ""
   echo "建议:"
   echo "  1. 使用普通用户运行此脚本"
   echo "  2. 如需安装系统依赖，脚本会自动使用 sudo"
   echo ""
   read -p "是否继续? (y/N): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       echo "已取消安装"
       exit 1
   fi
   echo ""
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 安装目录: $SCRIPT_DIR"
echo ""

# 检查 Python 版本
echo "🔍 检查 Python 版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ 找到 Python: $PYTHON_VERSION"
else
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python3${NC}"
    echo "安装命令: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

# 检查 pip
echo ""
echo "🔍 检查 pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ 找到 pip3"
else
    echo -e "${YELLOW}⚠️ 未找到 pip3，尝试安装...${NC}"
    sudo apt update
    sudo apt install -y python3-pip
fi

# 创建虚拟环境（推荐）
if [ "$USE_VENV" = true ]; then
    echo ""
    echo "📦 创建 Python 虚拟环境..."
    
    # 检查虚拟环境是否完整
    VENV_COMPLETE=false
    if [ -d ".venv" ] && [ -f ".venv/bin/activate" ] && [ -f ".venv/bin/python" ]; then
        VENV_COMPLETE=true
        echo "✅ 虚拟环境已存在且完整"
    elif [ -d ".venv" ]; then
        echo -e "${YELLOW}⚠️ 虚拟环境目录存在但不完整，重新创建...${NC}"
        rm -rf .venv
    fi
    
    # 创建虚拟环境
    if [ "$VENV_COMPLETE" = false ]; then
        python3 -m venv .venv
        if [ $? -eq 0 ]; then
            echo "✅ 虚拟环境创建成功"
        else
            echo -e "${RED}❌ 虚拟环境创建失败${NC}"
            echo "尝试使用系统 Python 环境..."
            USE_VENV=false
        fi
    fi

    # 激活虚拟环境
    if [ "$USE_VENV" = true ]; then
        echo ""
        echo "🔄 激活虚拟环境..."
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
            if [ $? -eq 0 ]; then
                echo -e "${BLUE}ℹ️  虚拟环境路径: $(which python)${NC}"
            else
                echo -e "${YELLOW}⚠️ 激活虚拟环境失败，使用系统 Python${NC}"
                USE_VENV=false
            fi
        else
            echo -e "${YELLOW}⚠️ 虚拟环境激活文件不存在，使用系统 Python${NC}"
            USE_VENV=false
        fi
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  使用系统 Python 环境${NC}"
    echo -e "${YELLOW}   Python 路径: $(which python3)${NC}"
fi

# 升级 pip
echo ""
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 安装系统依赖（Pillow 需要）
echo ""
echo "📥 安装系统依赖..."
sudo apt update
sudo apt install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk

echo "✅ 系统依赖安装完成"

# 安装 Python 依赖
echo ""
echo "📥 安装 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python 依赖安装完成"
else
    echo -e "${YELLOW}⚠️ 未找到 requirements.txt，安装默认依赖...${NC}"
    pip install aiohttp Pillow qrcode PyYAML aiofiles
fi

# 创建必要的目录
echo ""
echo "📁 创建必要的目录..."
mkdir -p cache
mkdir -p output
mkdir -p logs
chmod 755 cache output logs
echo "✅ 目录创建完成"

# 检查字体
echo ""
echo "🔍 检查字体..."
if fc-list | grep -i "noto\|source.*sans" > /dev/null; then
    echo "✅ 已安装合适的字体"
else
    echo -e "${YELLOW}⚠️ 建议安装中文字体以获得最佳显示效果${NC}"
    echo "安装命令: sudo apt install -y fonts-noto-cjk fonts-noto-color-emoji"
fi

# 设置权限
echo ""
echo "🔒 设置文件权限..."
chmod -R 755 "$SCRIPT_DIR"
find "$SCRIPT_DIR" -type f -name "*.py" -exec chmod 644 {} \;
chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/manage.sh" 2>/dev/null || true
echo "✅ 权限设置完成"

echo ""
echo "=========================================="
echo -e "${GREEN}  ✅ 安装完成！${NC}"
echo "=========================================="
echo ""

if [ "$USE_VENV" = true ]; then
    echo -e "${BLUE}📦 已使用虚拟环境 (.venv)${NC}"
    echo ""
    echo "🔧 常用命令:"
    echo "   激活虚拟环境: source .venv/bin/activate"
    echo "   退出虚拟环境: deactivate"
    echo "   查看插件帮助: /phi_help"
    echo ""
    echo "📋 注意事项:"
    echo "   • 虚拟环境已自动激活，依赖已安装到虚拟环境中"
    echo "   • 这避免了与系统 Python 包的冲突"
    echo "   • AstrBot 会自动使用虚拟环境中的依赖"
else
    echo -e "${YELLOW}⚠️  未使用虚拟环境${NC}"
    echo ""
    echo "📋 注意事项:"
    echo "   • 依赖已安装到系统 Python 环境中"
    echo "   • 可能会与其他 Python 应用产生冲突"
    echo "   • 如需卸载依赖，请手动执行: pip uninstall [包名]"
fi

echo ""
echo "📖 更多信息请查看 README.md"
echo ""
