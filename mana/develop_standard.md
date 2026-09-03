# 生成测试开发规范

## 文件与标识

- 生成测试写入 `tests/generated/test_<scenario_id>_<case_id>.py`；
- 每个测试文件顶部注明 `scenario_id`、`case_id` 和 `run_id`；
- 使用 `@pytest.mark.generated` 和 `@pytest.mark.ai_demo`；
- 使用 Allure 的 epic、feature、story 和 title；
- 每个业务步骤使用 `allure.step()`。

## 代码结构

- 优先复用 `framework/pages/`、`framework/workflows/` 和 `framework/data/`；
- 不在测试中复制登录、等待、证据采集和清理框架；
- 测试函数独立运行，不依赖用例执行顺序；
- 需要唯一数据时，把 `run_id` 或 `case_id` 放进标题/标签；
- 不使用固定 `sleep`；等待用户可见状态、URL、网络响应或元素状态；
- 不捕获并吞掉断言异常。

## 定位器

优先级如下：

1. `get_by_role()` + accessible name；
2. `get_by_label()`；
3. `get_by_test_id()`；
4. 稳定、局部的 CSS 定位器。

禁止把绝对 XPath、动态 class、元素序号或当前屏幕坐标作为首选定位器。

## 自动纠错

允许最多 3 轮：

- 定位器修复；
- 等待条件修复；
- 测试数据唯一性或清理修复；
- 导入、格式和明显语法修复。

不允许：

- 修改或删除业务断言；
- 把失败测试改成 skip 或 xfail；
- 放宽标题、正文、图片、权限、点赞和评论业务规则；
- 修改 `practice_app/` 业务实现来消除测试失败。

## 结果

- 每条候选用例必须写入 run manifest；
- 失败必须包含分类、最终原因和证据路径；
- 不可执行用例使用 `skipped` 并说明缺少的功能或数据；
- 环境/MCP/浏览器不可用时使用 `blocked`；
- 不得静默删除候选用例。
