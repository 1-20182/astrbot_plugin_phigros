import sys
import random
import asyncio
from pathlib import Path
from phi_style_renderer import PhiStyleRenderer

def main():
    # 初始化渲染器
    renderer = PhiStyleRenderer(
        Path('/workspace'),
        Path('/workspace'),
        Path('/workspace/resources/img')
    )
    print('Renderer initialized successfully')
    
    # 测试1: 空数据
    print('\nTesting with no data:')
    test_data_empty = {
        'items': [],
        'currentRks': 15.0,
        'peakRks': 15.0,
        'total': 0
    }
    result_empty = asyncio.run(
        renderer.render_rks_history(
            test_data_empty, 
            Path('/workspace/test_rks_history_empty.png')
        )
    )
    print(f'Empty data test result: {result_empty}')
    
    # 测试2: 多数据点
    print('\nTesting with many data points:')
    many_items = []
    for i in range(30):
        many_items.append({
            'createdAt': f'2026-04-{i+1:02d}T00:00:00Z',
            'rks': 15.0 + i*0.1 + random.uniform(-0.05, 0.05)
        })
    test_data_many = {
        'items': many_items,
        'currentRks': 18.0,
        'peakRks': 18.0,
        'total': 30
    }
    result_many = asyncio.run(
        renderer.render_rks_history(
            test_data_many, 
            Path('/workspace/test_rks_history_many.png')
        )
    )
    print(f'Many data points test result: {result_many}')
    
    # 测试3: 正常数据
    print('\nTesting with normal data:')
    test_data_normal = {
        'items': [
            {'createdAt': '2026-04-01T00:00:00Z', 'rks': 15.5, 'rksJump': 0.2},
            {'createdAt': '2026-04-02T00:00:00Z', 'rks': 15.7, 'rksJump': 0.2},
            {'createdAt': '2026-04-03T00:00:00Z', 'rks': 15.9, 'rksJump': 0.2},
            {'createdAt': '2026-04-04T00:00:00Z', 'rks': 16.1, 'rksJump': 0.2},
            {'createdAt': '2026-04-05T00:00:00Z', 'rks': 16.3, 'rksJump': 0.2}
        ],
        'currentRks': 16.3,
        'peakRks': 16.3,
        'total': 5
    }
    result_normal = asyncio.run(
        renderer.render_rks_history(
            test_data_normal, 
            Path('/workspace/test_rks_history_normal.png')
        )
    )
    print(f'Normal data test result: {result_normal}')
    
    print('\nAll tests completed')

if __name__ == '__main__':
    main()
