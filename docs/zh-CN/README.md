# 中文上手

这是本地AI辅助测试工作台，不是独立大模型服务。先验证框架和历史用例，再接入TRAE
体验新场景生成。当前是未发布的v0.1开发版本。

在项目根目录执行：

```sh
make setup
make check
AUTO_BASE_URL=http://127.0.0.1:8765 make baseline
AUTO_BASE_URL=http://127.0.0.1:8765 make replay
AUTO_BASE_URL=http://127.0.0.1:8765 make bug-demo
make report
```

setup安装锁定依赖并下载Chromium；report额外需要Allure CLI，其余步骤不需要。
replay执行待维护者审阅的历史迁移候选，不代表新的AI生成。bug-demo外层成功表示抓到
指定缺陷，内层测试仍保留failed。

先看终端输出run_dir下的summary.md，再看manifest.json和各attempt的JUnit、截图、
Trace、录像及源码。不要把原始报告目录直接上传GitHub。

按[TRAE指南](../how-to/trae.md)配置项目MCP和两个角色：内置Agent协调，生成器负责
计划、探索、生成与执行，数据增强器只负责CSV。探索用8000端口，正式测试用8765，
两者不共享数据。MCP探索是真实预演，不等于正式用例通过；Skill不会自行启动第二个Agent。

继续阅读：[架构与目录](../concepts/architecture.md)、[排错](../how-to/troubleshooting.md)、
[实测版本](../reference/tool-versions.md)。公开发布仍需维护者审阅样例、真实TRAE验收、
最终隐私复查和GitHub CI结果。

## 新版 2.1 验收

新 run 使用结构化检查：每条预期关联检查 ID，框架从冻结计划读取比较方式和预期值。
测试只提供真实观察值；“信息非空”不能替代“包含指定内容”。定位器自动修复也只允许
已登记的动作参数和有限等待时间，不能添加包装类、替换变量对象或改业务预期。

接入官方 Playwright MCP 前，执行：

```sh
npm ci --prefix integrations/trae --ignore-scripts
uv run --frozen python -m scripts.configure_trae
```

这会生成忽略提交的 `.trae/mcp.json`，不会覆盖现有配置。重载后应能看到官方
`browser_*` 工具。完整 MCP 包含脚本和文件操作能力，只能用于无敏感信息的本地练习
环境；隔离浏览器、回环地址和输出上限不是操作系统沙箱。

现在报告会分别显示“执行门禁”和“AI 流程验收”。全绿只说明测试执行通过；MCP探索
不是独立认证证据，缺少真实Agent宿主截图或人工语义审阅时，流程仍是 `unverified`。
旧 run 及其生成源码保持只读，不会被升级或重写。详见
[结构化检查](../how-to/check-contracts.md)和[验收与重试](../how-to/workflow-acceptance.md)。
