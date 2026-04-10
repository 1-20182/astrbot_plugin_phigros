#!/usr/bin/env python3
from bs4 import BeautifulSoup

# 检查HTML文件
def check_html(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # 检查基本结构
        html_tag = soup.find('html')
        head_tag = soup.find('head')
        body_tag = soup.find('body')
        
        if html_tag and head_tag and body_tag:
            print(f'HTML文件 {file_path} 基本结构正确')
            return True
        else:
            print(f'HTML文件 {file_path} 基本结构有问题')
            return False
    except Exception as e:
        print(f'检查HTML文件时出错: {e}')
        return False

if __name__ == '__main__':
    check_html('frontend/index.html')
