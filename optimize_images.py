#!/usr/bin/env python3
import os
from PIL import Image

# 图像优化函数
def optimize_image(input_path, output_path, max_width=200, max_height=200, quality=85):
    try:
        # 打开图像
        img = Image.open(input_path)
        
        # 调整大小
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # 保存优化后的图像
        img.save(output_path, 'PNG', optimize=True, quality=quality)
        
        # 计算文件大小
        original_size = os.path.getsize(input_path)
        optimized_size = os.path.getsize(output_path)
        
        print(f'优化完成: {input_path} -> {output_path}')
        print(f'原始大小: {original_size / 1024:.2f} KB')
        print(f'优化后大小: {optimized_size / 1024:.2f} KB')
        print(f'减少了: {((original_size - optimized_size) / original_size * 100):.2f}%')
        print()
        
    except Exception as e:
        print(f'优化图像时出错: {e}')

# 主函数
def main():
    # 图像目录
    image_dir = 'frontend/assets/images'
    
    # 优化avatar.png
    avatar_input = os.path.join(image_dir, 'avatar.png')
    avatar_output = os.path.join(image_dir, 'avatar.png')  # 覆盖原文件
    if os.path.exists(avatar_input):
        optimize_image(avatar_input, avatar_output, max_width=100, max_height=100, quality=80)
    
    # 优化logo.png
    logo_input = os.path.join(image_dir, 'logo.png')
    logo_output = os.path.join(image_dir, 'logo.png')  # 覆盖原文件
    if os.path.exists(logo_input):
        optimize_image(logo_input, logo_output, max_width=150, max_height=150, quality=80)
    
    # 优化song-placeholder.png
    placeholder_input = os.path.join(image_dir, 'song-placeholder.png')
    placeholder_output = os.path.join(image_dir, 'song-placeholder.png')  # 覆盖原文件
    if os.path.exists(placeholder_input):
        optimize_image(placeholder_input, placeholder_output, max_width=300, max_height=300, quality=80)

if __name__ == '__main__':
    main()
