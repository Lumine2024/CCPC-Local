# 第三方材料与来源

- **Marked 15.0.12**：Markdown 渲染，MIT；来源 `https://registry.npmjs.org/marked/15.0.12`，许可见 `frontend/vendor/marked/LICENSE.md`。
- **DOMPurify 3.3.1**：清理 Markdown HTML，Apache-2.0 或 MPL-2.0；来源 `https://registry.npmjs.org/dompurify/3.3.1`，完整许可见 `frontend/vendor/dompurify/LICENSE`。
- **KaTeX 0.16.33**：离线数学公式、样式、字体和 auto-render，MIT；来源 `https://registry.npmjs.org/katex/0.16.33`，许可见 `frontend/vendor/katex/LICENSE`，字体信息见包内许可。
- **psutil 7.2.2**：跨平台进程监测，BSD-3-Clause；由 `requirements.txt` 安装，项目与许可：<https://github.com/giampaolo/psutil>。
- **Playwright 1.58.0**：仅浏览器验收使用，Apache-2.0；由 `requirements-dev.txt` 安装，项目：<https://github.com/microsoft/playwright-python>。
- 仓库原有 **testlib.h**、题包与历史资料保持原样和原始声明，未重新授权；testlib 来源与许可见各题 `include/testlib.h`。

配置语义、testlib checker 调用与题包维护方式参考 [ICPC-Problem-Creator.skill](https://github.com/Lumine2024/ICPC-Problem-Creator.skill)。本项目的 Python 运行时自行实现，未复制该 skill 的 PowerShell 脚本，也不依赖 `C:\Users\123\.claude`。

前端分发文件来源、精确版本和 npm tarball integrity 记录于 `frontend/vendor/manifest.json`，可用 `scripts/vendor_assets.py` 重建。运行时无需联网下载任何前端依赖。
