#!/bin/bash

# Phigros Query 插件 Ubuntu 管理脚本
# 用法: ./manage.sh [command]
# 命令: install, update, clean, check, fix-permissions, help

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 显示帮助
show_help() {
    echo "=========================================="
    echo "  Phigros Query 插件 - Ubuntu 管理脚本"
    echo "=========================================="
    echo ""
    echo "用法: ./manage.sh [command]"
    echo ""
    echo "可用命令:"
    echo "  install         安装插件依赖"
    echo "  update          更新插件依赖"
    echo "  clean           清理缓存文件"
    echo "  check           检查环境配置"
    echo "  fix-permissions 修复文件权限"
    echo "  test-qr         测试二维码生成功能"
    echo "  help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  ./manage.sh install"
    echo "  ./manage.sh check"
    echo ""
}

# 安装依赖
cmd_install() {
    echo -e "${BLUE}📦 开始安装依赖...${NC}"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ 未找到 Python3${NC}"
        exit 1
    fi
    
    # 创建虚拟环境
    if [ ! -d ".venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv .venv
    fi
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装系统依赖
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
        python3-tk \
        fonts-noto-cjk \
        fonts-noto-color-emoji 2>/dev/null || true
    
    # 安装 Python 依赖
    echo "📥 安装 Python 依赖..."
    pip install -r requirements.txt
    
    # 创建目录
    mkdir -p cache output logs
    
    echo -e "${GREEN}✅ 安装完成！${NC}"
}

# 更新依赖
cmd_update() {
    echo -e "${BLUE}⬆️  更新依赖...${NC}"
    
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ 虚拟环境不存在，请先运行: ./manage.sh install${NC}"
        exit 1
    fi
    
    source .venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade -r requirements.txt
    
    echo -e "${GREEN}✅ 更新完成！${NC}"
}

# 清理缓存
cmd_clean() {
    echo -e "${BLUE}🧹 清理缓存...${NC}"
    
    # 清理 Python 缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # 清理缓存目录
    if [ -d "cache" ]; then
        rm -rf cache/*
        echo "✅ 清理 cache 目录"
    fi
    
    if [ -d "output" ]; then
        rm -rf output/*
        echo "✅ 清理 output 目录"
    fi
    
    echo -e "${GREEN}✅ 清理完成！${NC}"
}

# 检查环境
cmd_check() {
    echo "=========================================="
    echo "  🔍 环境检查"
    echo "=========================================="
    echo ""
    
    # 检查 Python
    echo "📋 Python 版本:"
    python3 --version 2>/dev/null || echo -e "${RED}❌ Python3 未安装${NC}"
    echo ""
    
    # 检查虚拟环境
    echo "📋 虚拟环境:"
    if [ -d ".venv" ]; then
        echo -e "${GREEN}✅ 虚拟环境已创建${NC}"
        source .venv/bin/activate
        echo "Python 路径: $(which python)"
    else
        echo -e "${YELLOW}⚠️ 虚拟环境未创建${NC}"
    fi
    echo ""
    
    # 检查依赖
    echo "📋 Python 依赖:"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        pip list 2>/dev/null | grep -E "aiohttp|Pillow|qrcode|PyYAML|aiofiles" || echo -e "${YELLOW}⚠️ 部分依赖未安装${NC}"
    else
        echo -e "${YELLOW}⚠️ 虚拟环境未创建，无法检查依赖${NC}"
    fi
    echo ""
    
    # 检查目录
    echo "📋 目录状态:"
    for dir in cache output logs; do
        if [ -d "$dir" ]; then
            echo -e "${GREEN}✅ $dir 目录存在${NC}"
        else
            echo -e "${YELLOW}⚠️ $dir 目录不存在${NC}"
        fi
    done
    echo ""
    
    # 检查字体
    echo "📋 字体检查:"
    if fc-list | grep -i "noto" > /dev/null; then
        echo -e "${GREEN}✅ Noto 字体已安装${NC}"
    else
        echo -e "${YELLOW}⚠️ Noto 字体未安装${NC}"
    fi
    echo ""
    
    # 检查权限
    echo "📋 权限检查:"
    if [ -w "." ]; then
        echo -e "${GREEN}✅ 当前目录可写${NC}"
    else
        echo -e "${RED}❌ 当前目录不可写${NC}"
    fi
    echo ""
    
    # 磁盘空间
    echo "📋 磁盘空间:"
    df -h . | tail -1
    echo ""
    
    echo "=========================================="
}

# 修复权限
cmd_fix_permissions() {
    echo -e "${BLUE}🔒 修复文件权限...${NC}"
    
    # 设置目录权限
    chmod -R 755 "$SCRIPT_DIR"
    
    # 设置脚本可执行
    chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/manage.sh" 2>/dev/null || true
    
    # 设置 Python 文件权限
    find "$SCRIPT_DIR" -type f -name "*.py" -exec chmod 644 {} \;
    
    # 设置缓存目录权限
    for dir in cache output logs; do
        if [ -d "$dir" ]; then
            chmod 755 "$dir"
        fi
    done
    
    echo -e "${GREEN}✅ 权限修复完成！${NC}"
}

# 测试二维码功能
cmd_test_qr() {
    echo -e "${BLUE}🧪 测试二维码生成功能...${NC}"
    
    if [ ! -d ".venv" ]; then
        echo -e "${RED}❌ 虚拟环境不存在${NC}"
        exit 1
    fi
    
    source .venv/bin/activate
    
    # 创建测试脚本
    python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    import qrcode
    from PIL import Image
    from pathlib import Path
    
    print("✅ qrcode 模块导入成功")
    print("✅ Pillow 模块导入成功")
    
    # 测试生成二维码
    test_path = Path("output/test_qr.png")
    test_path.parent.mkdir(exist_ok=True)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data("https://example.com")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(test_path)
    
    if test_path.exists():
        print(f"✅ 二维码生成成功: {test_path}")
        print(f"✅ 文件大小: {test_path.stat().st_size} bytes")
        # 删除测试文件
        test_path.unlink()
        print("✅ 测试文件已清理")
    else:
        print("❌ 二维码生成失败")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    sys.exit(1)

print("\n✅ 所有测试通过！")
EOF
}

# 主函数
main() {
    case "${1:-help}" in
        install)
            cmd_install
            ;;
        update)
            cmd_update
            ;;
        clean)
            cmd_clean
            ;;
        check)
            cmd_check
            ;;
        fix-permissions)
            cmd_fix_permissions
            ;;
        test-qr)
            cmd_test_qr
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
