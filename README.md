# CCPC Local

在浏览器中进行本地 VP：回放历史队伍提交，真实编译判题，体验 CCPC 新榜单的阈值隐藏与四小时封榜。附带 2025 ICPC 陕西邀请赛 A–M 共 13 题、352 组评测数据。

## 安装和启动

需要 Python 3.10+、支持 GNU++20 的 GCC / G++。PowerShell 包装需要 PowerShell 7；Python 启动方式不需要 PowerShell。编译器须在 `PATH` 中。运行依赖只有 psutil，Markdown / 数学公式资源已经随仓库提供，无需 Node、npm 或联网 CDN。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
python launcher.py --problem-list tests/ICPC-Shaanxi-2025-National-Invitational-Contest --submissions tests/contest.txt
```

启动器在主 Python 缺少 psutil 时自动使用仓库 `.venv`。也可以直接使用虚拟环境 Python；Windows 下可用：

```powershell
pwsh launcher.ps1 -ProblemList tests/ICPC-Shaanxi-2025-National-Invitational-Contest -Submissions tests/contest.txt
```

Linux / macOS 环境准备：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python launcher.py --problem-list tests/ICPC-Shaanxi-2025-National-Invitational-Contest --submissions tests/contest.txt
```

默认在 `http://127.0.0.1:8765/` 开服务并打开浏览器。端口占用时自动换端口，以终端实际输出为准。`--port 0` 自动分配，`--no-browser` 禁止自动打开，`--data-dir "路径"` 指定状态目录。输入的相对路径按执行命令时的工作目录解释，路径含空格时加引号。

## 使用

1. 在首页设置队伍名，点击“开始 VP”。历史队伍从零时刻与您同步回放。
2. 点击题号阅读题面，使用每个样例的复制按钮。题目页和提交标签均可粘贴代码或上传 `.cpp` / `.py` 源文件。
3. 提交进入后台队列；“我的提交”与提交详情显示编译、运行和最终结果。支持 C++（按题包标准）和 Python 3，使用相同题目时限，不额外放宽 Python 时限。
4. 打开榜单，可搜索队伍或定位本人。未达到阈值的题目不公开逐队详情，通过数汇总在“其他”。
5. 四小时后榜单保持封榜快照，但本人判定继续更新。比赛结束后可显式查看最终结果、重新 VP，并通过侧栏查看旧会话。

开始按钮重复点击会返回当前比赛，不生成多场。刷新、打开第二个同浏览器标签页、停止服务再启动均不会重置计时。**关闭服务期间时间仍流逝。** Ctrl+C 停止服务并终止评测进程；未完成的提交在下次启动时重新排队。

会话身份保存在浏览器 HttpOnly cookie 中；不同浏览器有独立的本地队伍。清除 cookie 后无法在该浏览器访问原记录，但磁盘中的记录仍在。不同题包 / 历史文件内容使用不同的比赛标识，避免误用旧会话。

## 赛制约定

本项目按 [AGENTS.md](AGENTS.md) 的需求实现，没有将这些规则宣称为已核实的官方赛规。

- 开赛时固定队伍总数：历史队伍 + 本地 VP 队伍，附带比赛为 389。公开阈值为 `min(50, ceil(N / 5))`，本比赛为 50。
- 四小时前，题目通过的不同队伍数达到阈值才公开人数和逐队格子，零通过也显示 `?`。所有题目始终可以阅读与提交。
- 总过题数和罚时包括隐藏题。“其他”只显示通过的隐藏题数量，不显示题号、错交次数或时间。过滤在后端完成。
- 四小时起公开所有题目在 `[0,14400)` 的成绩并封榜。恰好 14400 秒的提交属于封榜后；封榜前接收、稍后判完的提交仍归属四小时快照，待判期间会提示。
- 比赛有效区间是 `[0, duration)`，时长从历史文件读取；附带比赛为 300 分钟。186 条发生在结束时或之后的历史事件完整保留，但不计成绩，启动时报告。
- 首次 AC 贡献 `floor(秒数 / 60) + 失败次数 × 题目罚时`；未通过题不加罚时，重复 AC 不改变成绩。历史 RJ，以及 WA / TLE / MLE / RE / OLE 计罚，CE / Judge Error 不计罚。
- 先按过题数降序、再按罚时升序排名，分数罚时相同并列。赛后最终结果单独查看，不覆盖封榜视图。
- 赛时 API 和页面不提供提交的耗时 / 内存；题目配置的时限 / 内存仍公开。本人题目状态和判定正常可见。

## 判题与资源限制

所有样例与隐藏测试来自 `exported-tests/manifest.json`，路径兼容 Windows 反斜杠。程序正常退出后运行 `checker input user-output answer`。checker 的选手输出错误映射 WA，内部错误映射 Judge Error；不会使用简单字符串比较或“样例通过即 AC”。非交互题受支持，交互题在导入时明确拒绝。

每个 case 使用配置时限；时间按进程创建完成、恢复执行至退出的墙钟时间计量，不计操作系统创建进程和 Job 初始化开销。编译最多 120 秒，checker 最多 10 秒。stdout 上限 16 MiB，stderr 上限 1 MiB，超限为 OLE。各提交使用隔离工作目录和独立文件；后台单 worker 使判题不阻塞网页，也避免本地并发争用导致不稳定成绩。

Windows 在挂起进程上先附加 Job Object，再恢复运行，退出 / 取消时终止整个 Job；内存按进程树的工作集 / 私有提交内存监测，并查询 Job 峰值。Linux / macOS 使用独立进程组和进程树 RSS 采样。采样间隔约 3 ms，实际调度和度量随平台变化，极短的峰值可能不被采样捕获；同一代码在不同机器的成绩可能不同。

评测程序以当前本地用户权限运行，资源控制和 HTTP 文件隔离不构成不可信代码的系统沙箱。适用于本人编写的训练代码；本机文件访问权限不被另外收窄。服务器仅绑定 loopback，并校验 Host、Origin、CSRF 和会话所有权，不公开题解、源码参考实现、配置或隐藏数据的下载接口。

当前真实验收平台为 Windows；Linux / macOS 路径及进程组实现已提供，未在这些系统进行运行验收。

## 状态、缓存和日志

默认位于 `tmp/ccpc-local/`，也可用 `--data-dir` 更改：

| 路径 | 用途 |
| --- | --- |
| `state.sqlite3`、`-wal`、`-shm` | VP 会话、源码、提交与判定；请保留 |
| `server.log` | HTTP 和服务内部错误 |
| `judge/cache/<题号>/<摘要>/` | 编译后的 checker，摘要覆盖源码、testlib 与编译配置 |
| `judge/jobs/<提交ID>/` | 本人提交源码、编译诊断、最后一组输出、逐 case 判定日志 |

运行不改写题包、历史文件或参考图。临时评测目录不通过 HTTP 开放。停服后可删除 `judge/cache` 重建编译缓存，删除 `judge/jobs` 不影响数据库中的源码和记录；不要删除 SQLite 文件来清理缓存。日志和任务目录会保留，长期训练可在停服后自行归档。

## 验收与开发

规则、导入、API、持久化和进程资源测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

运行全部 13 题主标程和每题一个错解、CE / TLE / RE / MLE / OLE / Judge Error 探针：

```powershell
.\.venv\Scripts\python.exe scripts/acceptance.py
```

结果位于 `tmp/acceptance/judge-results.json`，逐 case 日志位于相应 `judge/jobs/`，最后复查题包摘要证明未改写数据。过程需要几分钟，按题目逐项输出。

`scripts/reference_acceptance.py` 对 13 题独立 C++ 参考解按配置范围交叉验证；`scripts/python_acceptance.py` 验证 Python L 题全量 AC 和语法错误 CE。

浏览器验收与桌面 / 手机截图（额外开发依赖）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/browser_acceptance.py
```

浏览器检查实际启动器、VP、精确复制样例、公式与图片、源文件上传和真实 AC、刷新恢复、隐藏榜单、移动布局、本地资源与控制台错误；结果和截图保存到 `tmp/browser-acceptance/`。不提供正常比赛可用的调试时钟接口，四小时边界由注入时钟的业务 / API 测试验证。

还可执行 `scripts/phase_acceptance.py`，用注入的服务端时钟在浏览器验证真实历史事件的两小时、四小时封榜、赛后解榜、重新 VP 与旧会话；不伪造判定、不提供生产调时接口。`scripts/launcher_acceptance.py` 检查主 Python 回退、空格路径、端口占用、退出及环境错误。`scripts/unit_acceptance.py` 保存自动化测试日志与 JSON。

项目验收结论见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。前端依赖已内置；仅在维护时用 `scripts/vendor_assets.py` 从固定 npm 版本下载并校验 integrity，版本、来源和许可证见 `frontend/vendor/manifest.json` 和 [THIRD_PARTY.md](THIRD_PARTY.md)。判题配置和 checker 协议参考 [ICPC-Problem-Creator.skill](https://github.com/Lumine2024/ICPC-Problem-Creator.skill)，运行不依赖其本机安装目录。

## API

| 方法与路径 | 用途 |
| --- | --- |
| `GET /api/state?session_id=...&final=1` | 当前或本人旧会话、公开榜单、题目列表和个人记录；`final=1` 仅赛后可用 |
| `POST /api/vp` | `{"name":"队伍名"}` 创建 / 继续 VP |
| `POST /api/submissions` | `session_id`、`problem`、`language`（cpp / python）、`source` |
| `GET /api/submissions/<id>` | 本人提交详情和源码；赛时无耗时 / 内存 |
| `GET /api/problems/<题号>` | 题面 Markdown |
| `GET /api/problems/<题号>/assets/<相对图片路径>` | 仅题面引用的本地图片 |

写请求需 cookie 和从 `/api/state` 取得的 `X-CSRF-Token`。API 不接受客户端指定比赛时间。无全量历史事件接口。提交源代码最多 256 KiB，JSON 请求最多 2 MiB。

常见错误：找不到 `g++` 时安装编译器并检查 `g++ --version`；缺少 psutil 时用实际启动 Python 安装 requirements；题包缺文件 / 数量不一致时修复输入，不能跳过测试；Judge Error 查看内部日志，checker 诊断不会发给选手；无法恢复旧会话时确认浏览器 cookie 与题包内容未改变。

## 开源协议

本项目采用 GNU Affero General Public License 开源。开源协议详见 [LICENSE](LICENSE)。
