# Phigros 插件语法错误修复 - 实施计划

## [x] Task 1: 修复 _get_updates_text 方法
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 将 _get_updates_text 方法从生成器函数改为普通函数
  - 将 `yield Plain("" .join(msg_parts))` 改为 `return Plain("" .join(msg_parts))`
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-1.1: 代码不再包含 'yield from' 语法
  - `programmatic` TR-1.2: 代码语法正确，无语法错误
- **Notes**: 这是修复的第一步，将生成器函数改为普通函数

## [x] Task 2: 修复调用 _get_updates_text 的地方
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 将 `yield from self._get_updates_text(data, count)` 改为 `yield self._get_updates_text(data, count)`
  - 这是因为 _get_updates_text 现在返回单个 Plain 对象，而不是生成器
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-2.1: 代码不再包含 'yield from' 语法
  - `programmatic` TR-2.2: 代码语法正确，无语法错误
- **Notes**: 这是修复的第二步，更新调用方式

## [x] Task 3: 验证修复结果
- **Priority**: P0
- **Depends On**: Task 1, Task 2
- **Description**: 
  - 检查代码是否还有其他 'yield from' 语法错误
  - 确保插件能够正常加载
  - 测试插件的功能完整性
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-3.1: 代码中无 'yield from' 语法
  - `programmatic` TR-3.2: 插件能够正常加载
  - `human-judgment` TR-3.3: 插件功能正常运行
- **Notes**: 这是验证步骤，确保修复成功
