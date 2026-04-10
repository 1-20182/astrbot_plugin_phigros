#!/usr/bin/env python3
import os
import re
import gzip

# 压缩CSS文件
def compress_css(css_content):
    # 移除注释
    css_content = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # 移除多余的空白字符
    css_content = re.sub(r'\s+', ' ', css_content)
    # 移除分号前的空格
    css_content = re.sub(r'\s*;\s*', ';', css_content)
    # 移除花括号前后的空格
    css_content = re.sub(r'\s*{\s*', '{', css_content)
    css_content = re.sub(r'\s*}\s*', '}', css_content)
    # 移除冒号后的空格
    css_content = re.sub(r'\s*:\s*', ':', css_content)
    # 移除逗号后的空格
    css_content = re.sub(r'\s*,\s*', ',', css_content)
    # 移除最后一个分号
    css_content = re.sub(r';}', '}', css_content)
    return css_content

# 压缩JS文件
def compress_js(js_content):
    # 移除注释
    js_content = re.sub(r'//.*?$', '', js_content, flags=re.MULTILINE)
    js_content = re.sub(r'/\*[\s\S]*?\*/', '', js_content)
    # 移除多余的空白字符
    js_content = re.sub(r'\s+', ' ', js_content)
    # 移除分号前的空格
    js_content = re.sub(r'\s*;\s*', ';', js_content)
    # 移除花括号前后的空格
    js_content = re.sub(r'\s*{\s*', '{', js_content)
    js_content = re.sub(r'\s*}\s*', '}', js_content)
    # 移除冒号后的空格
    js_content = re.sub(r'\s*:\s*', ':', js_content)
    # 移除逗号后的空格
    js_content = re.sub(r'\s*,\s*', ',', js_content)
    # 移除括号前后的空格
    js_content = re.sub(r'\s*\(\s*', '(', js_content)
    js_content = re.sub(r'\s*\)\s*', ')', js_content)
    return js_content

# 压缩文件
def compress_file(input_path, output_path, compress_func):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    compressed_content = compress_func(content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(compressed_content)
    
    print(f'压缩完成: {input_path} -> {output_path}')

# 主函数
def main():
    # 压缩CSS文件
    css_input = 'frontend/assets/css/style.css'
    css_output = 'frontend/assets/css/style.min.css'
    if os.path.exists(css_input):
        compress_file(css_input, css_output, compress_css)
    
    # 压缩JS文件
    js_input = 'frontend/assets/js/main.js'
    js_output = 'frontend/assets/js/main.min.js'
    if os.path.exists(js_input):
        compress_file(js_input, js_output, compress_js)

if __name__ == '__main__':
    main()
