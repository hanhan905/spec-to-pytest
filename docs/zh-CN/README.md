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
最终隐私复查、许可证确认和GitHub CI结果。
