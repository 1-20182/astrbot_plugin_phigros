#!/usr/bin/env python3
"""
Phigros Query 插件安装脚本
自动安装依赖并检查环境
"""

import subprocess
import sys
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("🔍 检查 Python 版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低，需要 3.8+")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")


def install_requirements():
    """安装依赖"""
    print("\n📦 安装依赖...")
    req_file = Path(__file__).parent / "requirements.txt"
    
    if not req_file.exists():
        print("❌ 未找到 requirements.txt")
        return False
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True,
            capture_output=False
        )
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def check_illustrations():
    """检查曲绘文件"""
    print("\n🎨 检查曲绘文件...")
    illust_path = Path(__file__).parent / "illustrations"
    
    if not illust_path.exists():
        print(f"⚠️ 曲绘目录不存在: {illust_path}")
        print("   请手动将曲绘文件放入 illustrations 目录")
        return False
    
    png_files = list(illust_path.glob("*.png"))
    print(f"✅ 找到 {len(png_files)} 个曲绘文件")
    return True


def create_directories():
    """创建必要目录"""
    print("\n📁 创建目录...")
    base_path = Path(__file__).parent
    
    dirs = ["output", "output/cache", "illustrations"]
    for d in dirs:
        (base_path / d).mkdir(parents=True, exist_ok=True)
    
    print("✅ 目录创建完成")


def main():
    """主函数"""
    print("=" * 50)
    print("🎮 Phigros Query 插件安装程序")
    print("=" * 50)
    
    check_python_version()
    create_directories()
    
    if install_requirements():
        print("\n✅ 安装成功！")
    else:
        print("\n⚠️ 安装可能不完整")
    
    check_illustrations()
    
    print("\n" + "=" * 50)
    print("📖 使用说明:")
    print("   1. 将插件文件夹复制到 AstrBot 的 plugins 目录")
    print("   2. 重启 AstrBot 或重新加载插件")
    print("   3. 使用 /phi_help 查看帮助")
    print("=" * 50)


if __name__ == "__main__":
    main()
