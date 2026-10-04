# CCPC Local：仓库现状与代码导航

## 1. 这个仓库做了什么

本仓库已经实现一个通过浏览器使用的本地 OJ：启动器加载题包和历史提交，在 localhost 提供页面与 API；用户开始 Virtual Participation（VP）后，与历史队伍同步比赛，阅读题面、复制样例、提交 C++ / Python 代码，并查看真实判定与比赛榜单。

项目实现了需求中定义的 CCPC 新榜单呈现机制：四小时前按通过队伍数阈值公开题目统计，其余题目汇总为“其他”；四小时起公开所有题目的四小时快照并封榜。个人提交在封榜后继续判定，赛后有独立的最终结果视图。

附带的 2025 ICPC 陕西邀请赛 A–M 共 13 道非交互题、352 组测试已接入。完整应用与验收材料均已落盘；当前 Windows 验收结论见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。本文件描述现有实现及其位置，安装和日常操作说明见 [README.md](README.md)。

运行链路如下：

```text
launcher.py
  → App 加载历史记录、题包、SQLite 和后台判题 worker
  → 同一 HTTP 服务提供 frontend 与 API
  → 网页开始 VP，持久化队伍、开始时间和固定人数
  → 历史事件按服务端比赛时钟回放
  → 接收源码，后台编译、逐 case 运行、调用原 checker
  → 持久化判定，更新本人记录和 ICPC 成绩
  → 后端生成经过阈值过滤 / 四小时封榜的公共快照
  → 比赛结束后保留记录，支持最终结果、旧会话和重新 VP
```

## 2. 哪里有什么

```text
仓库根目录/
├── AGENTS.md                         # 仓库现状、模块索引和行为说明
├── README.md                         # 安装、启动、使用、诊断与验证命令
├── launcher.py                       # Python 主启动入口
├── launcher.ps1                      # PowerShell 7 启动包装
├── requirements.txt                  # 运行依赖 psutil
├── requirements-dev.txt              # 运行依赖 + 浏览器验收 Playwright
├── LICENSE                           # GNU AGPL v3 开源协议
├── THIRD_PARTY.md                    # 第三方依赖、许可与 skill 来源
├── backend/
│   ├── __init__.py                   # Python 包入口
│   ├── contest_parser.py             # @ 格式历史文件解析和诊断
│   ├── problems.py                   # 题包、manifest、题面资源和内容摘要
│   ├── scoreboard.py                 # ICPC 计分、阈值投影和封榜视图
│   ├── contest.py                    # App：会话、时钟、提交和公共响应
│   ├── storage.py                    # SQLite 持久化及中断恢复
│   ├── judge.py                      # 编译、checker 缓存和单 worker 队列
│   ├── runner.py                     # 进程执行、资源监测和进程树清理
│   └── server.py                     # HTTP、会话身份、CSRF 和静态资源白名单
├── frontend/
│   ├── index.html                    # 页面骨架、导航与侧栏容器
│   ├── app.js                        # 路由、API、题面、提交、榜单与轮询
│   ├── style.css                     # 桌面与移动端样式
│   ├── icon.svg                      # 项目图标
│   └── vendor/                       # 离线 Marked、DOMPurify、KaTeX 与许可
├── scripts/                          # 验收、证据打包和静态依赖维护脚本
├── tests/
│   ├── test_core.py                  # 规则、解析、题包和实数据回归
│   ├── test_api.py                   # HTTP、会话、过滤与持久化测试
│   ├── test_runner.py                # 超时、内存、输出与进程清理测试
│   ├── contest.txt                   # 388 队、3537 条历史提交
│   └── ICPC-Shaanxi-2025-National-Invitational-Contest/
│       └── A/ ... M/                 # 13 个 skill 兼容题目工作区
├── image-assets/                     # 原始 Codeforces 页面参考截图
├── docs/
│   ├── ACCEPTANCE.md                 # 已执行验收的结论与复现入口
│   └── acceptance/                   # 7 份结果 JSON、测试日志、9 张截图
├── tmp/                              # 本机状态、评测产物和验收运行目录
└── bin/                              # 当前为空；应用不依赖此目录
```

`.venv/` 是本机 Python 环境，`__pycache__/` 是 Python 自动生成的缓存。应用源码、只读比赛资料和可再生成的运行产物分别位于上述目录中。

原始页面参考位于 `image-assets/cf-index-page.png`、`cf-view-problem-1.png`、`cf-view-problem-2.png`、`cf-my-submission.png`、`cf-board.png`；实际应用截图位于 `docs/acceptance/`。

## 3. 启动入口与依赖

运行需要 Python 3.10+、支持 GNU++20 的 GCC / G++，编译器位于 `PATH`。Python 运行依赖是 `requirements.txt` 中的 `psutil==7.2.2`；PowerShell 包装使用 PowerShell 7。浏览器验收另使用 `playwright==1.58.0` 和 Chromium，正常使用不依赖 Playwright、Node 或 npm。

Python 启动命令：

```powershell
python launcher.py --problem-list tests/ICPC-Shaanxi-2025-National-Invitational-Contest --submissions tests/contest.txt
```

PowerShell 启动命令：

```powershell
pwsh launcher.ps1 -ProblemList tests/ICPC-Shaanxi-2025-National-Invitational-Contest -Submissions tests/contest.txt
```

`launcher.py` 默认绑定 `127.0.0.1:8765`，服务就绪后输出 URL 并打开浏览器；端口占用时自动分配其他端口。支持 `--port`（0 为自动分配）、`--data-dir`、`--no-browser`。PowerShell 对应参数为 `-Port`、`-DataDir`、`-NoBrowser`。

输入相对路径按调用工作目录解析，前端资源按启动器所在目录定位。主 Python 缺少 psutil 时，启动器尝试使用仓库 `.venv`；PowerShell 包装也优先使用该虚拟环境。启动阶段检查输入、离线脚本和编译器，报出历史越界事件；Ctrl+C / Windows SIGBREAK 进入服务与判题清理流程。

## 4. 前端页面与 API 在哪里

`frontend/app.js` 使用 hash 路由，每 4 秒读取服务端状态；倒计时每秒更新显示，计分和提交时间仍由后端决定。

| 页面 / 路由 | 已实现内容 | 主要函数 |
| --- | --- | --- |
| `#problems` | 13 题列表、配置限制、本人状态、公开通过数或 `?` | `problemList()` |
| `#problem/<题号>` | Markdown、LaTeX、相对配图、配对样例及复制按钮、提交表单 | `renderMarkdown()`、`renderRoute()` |
| `#submit`、`#submit/<题号>` | 题目和语言选择、粘贴代码、源文件上传、草稿保存与提交 | `submitForm()`、`wireSubmit()` |
| `#submissions`、`#submission/<ID>` | 本人记录、状态、源码与 CE 诊断；赛后增加耗时 / 内存 | `submissions()`、`renderRoute()` |
| `#board`、`#final` | 公共快照、公开题列、“其他”、队伍搜索、本人定位与最终结果 | `boardTable()`、`scoreboard()`、`wireBoard()` |
| 比赛侧栏 | 比赛时钟、VP、新建 / 选择会话、规则及待判快照提示 | `sidebar()`、`updateClock()` |

题面先经 Marked 解析、DOMPurify 清理，再由 KaTeX 渲染公式。`input` / `output` 和带编号围栏按编号配对；复制按钮读取样例原文，剪贴板失败时选中文本供手动复制。D、I 题的图片经后端允许的题面资源路由加载。

`backend/server.py` 的 `Server` / `Handler` 提供以下接口：

| 方法与路径 | 实际用途 |
| --- | --- |
| `GET /api/state?session_id=...&final=1` | 比赛信息、本人会话列表、题目、公开榜单和本人提交；`final=1` 仅赛后可用 |
| `POST /api/vp` | 接收 `name`，创建或继续 VP，返回 `session_id` |
| `POST /api/submissions` | 接收 `session_id`、`problem`、`language`（cpp / python）、`source`，返回提交 ID |
| `GET /api/submissions/<ID>` | 查询属于本人会话的提交、诊断和源码 |
| `GET /api/problems/<题号>` | 返回题面 Markdown |
| `GET /api/problems/<题号>/assets/<相对图片路径>` | 返回该题面引用的本地图片 |

`/api/state` 的主要字段是 `contest`、`session`、`sessions`、`languages`、`board`、`problems`、`submissions`、`csrf`。`board` 包含快照时间、封榜 / 结束标记、待判数、阈值、公开题号、过滤后的统计与队伍行。

写请求携带 cookie 和 `X-CSRF-Token`，令牌从状态接口取得。服务校验本机 Host、同来源 Origin 和会话所有权；源码上限 256 KiB，JSON 请求上限 2 MiB。赛时提交响应不含 `time_ms`、`memory_kb`；公共榜单中没有隐藏题的逐队格子，也没有原始历史事件接口。

静态入口只开放首页、应用脚本 / 样式 / 图标、本地 vendor 资源和题面图片白名单。题解、参考源码、隐藏输入 / 答案、配置、SQLite 与评测目录没有 HTTP 下载入口。

## 5. 比赛规则的实际实现

### 阈值、封榜与最终结果

`backend/scoreboard.py` 中 `threshold()` 计算 `min(50, ceil(N / 5))`，`score()` 计算完整 ICPC 成绩，`view()` 生成公共投影。`N` 按历史队伍加当前 VP 队伍固定，附带比赛为 389，阈值为 50。

四小时前，统计通过同一题的不同队伍数，重复 AC 不增加人数。达到阈值的题目同时公开人数和逐队列；其他题通过人数返回 `null`，页面显示 `?`，队伍行只保留隐藏题通过数量 `other`。总过题数和罚时包含隐藏题。例如通过 A/B/C/D/E、仅 C/D 公开时，该队显示总过题数 5、C/D 的 AC 和“其他3题”。首页仍列出所有题目，本人作答状态在本人响应中正常显示。

从 14400 秒起，公共统计、名次、总分、罚时和逐题格子都按 `[0,14400)` 计算，全部题目公开。封榜后可继续提交并查看个人真实判定。封榜前收到、封榜后判完的提交按接收时间归属快照；待判数用于提示快照尚有未完成判定。赛后显式进入最终结果时，按整个有效比赛区间计算，封榜视图仍保留。

### 计分与时间边界

| 事项 | 当前行为 |
| --- | --- |
| 比赛时长 | 从 `@contlen` 分钟转换为秒；附带比赛为 300 分钟 |
| 有效区间 | `[0,duration)`；恰好 14400 秒属于封榜后，恰好结束时间不计成绩 |
| 结束前回放 | 仅使用当前时刻已发生的历史事件，同秒按源行序处理 |
| 首次 AC | 该题计一次通过；罚时为 `floor(AC秒数/60) + 之前计罚失败次数 × 题目罚时` |
| 计罚失败 | 历史 RJ，本地 WA / TLE / MLE / RE / OLE |
| 不计罚 | CE、Judge Error、待判提交；始终未 AC 的题不贡献总罚时 |
| 排名 | 过题数降序、罚时升序；相同成绩并列，队伍 ID 只稳定显示顺序 |
| 公开格子 | 空白、`-k`、`+`、`+k`；AC 格子附通过时间 |
| 结束 | 拒绝新提交，结束前已接收任务继续判定 |
| 短于四小时 | 按实际结束时间停止事件，不额外制造四小时阶段 |

每题罚时来自历史 `@p`，当前均为 20 分钟。赛制是本项目采用的需求约定，文档未将其宣称为核实过的官方赛规。

### VP 与会话

`backend/contest.py` 的 `App` 统一处理服务端时钟、会话选择、提交接收与响应过滤。尚未开始时回放停在零时刻；创建会话后保存开始时间，刷新、多标签页和重启不重新计时，停服期间时间继续流逝。

同一浏览器身份重复开始返回正在进行的会话；结束后可新建，旧记录保留。浏览器身份使用 HttpOnly、SameSite=Strict cookie，数据库按 owner 与输入内容标识隔离。清除 cookie 会失去该浏览器对旧记录的访问身份。题包或历史内容改变后，应用使用新的输入标识。测试通过 `App(clock=...)` 注入时钟，生产 API 不提供调时入口。

## 6. 比赛资料与题包如何加载

### 历史记录

`tests/contest.txt` 是 `@` 记录文本导出，解析入口为 `backend/contest_parser.py::parse_contest()`。当前数据包含 13 题、388 队、3537 条事件，历史判定只有 OK / RJ，映射 AC / 计罚失败。

| 记录 | 已读取信息 |
| --- | --- |
| `@contest`、`@contlen` | 比赛标题、时长分钟数 |
| `@problems`、`@teams`、`@submissions` | 声明数量，与实际数量核对 |
| `@p` | 题号、可含逗号的题名、计罚分钟、保留的附加字段 |
| `@t` | 队伍 ID、两个保留的附加字段、可含逗号的显示名 |
| `@s` | 队伍、题号、该队该题提交序号、经过秒数、判定；事件保留源行序 |

解析器兼容 UTF-8 BOM 与 CRLF / LF，检查重复声明、ID / 事件、非法时间、未知引用 / 判定、数量不符。当前有 186 条事件发生在 18000 秒结束时或之后：原事件完整保留，诊断明确报告，计分层排除这些事件。

### 题目工作区

`backend/problems.py::load_problems()` 遍历集合目录直接子目录的 `config.json`，按目录题号关联历史 `@p`，由 `App` 核对题号集合。题名大小写或前缀差异不影响关联。

每题的现有文件按以下职责使用：

| 题目内路径 | 内容与用途 |
| --- | --- |
| `config.json` | 标题、题型、时限 / 内存、标准、checker 与构建配置 |
| `readme.md` | 原题目工作区说明，部分维护命令引用外部 skill |
| `docs/statement.md` | 网页题面；实际入口以 `config.statement` 为准 |
| `docs/tutorial.md`、文档 `.tex` | 内部题解与文档副本，OJ 不提供下载 |
| `docs/assets/` | D / I 的本地配图和图形维护用 HTML |
| `include/testlib.h` | checker 等程序的头文件 |
| `src/checker/checker.cpp` | 实际输出判定程序 |
| `src/solution*.cpp`、部分题目的 `.py` | 主标程和参考解，供验收使用 |
| `src/wrong/` | 刻意错误的实现，供拒绝错解验收使用 |
| `src/validator/`、`src/generator/` | 题包维护工具，用户提交判题不重建数据 |
| `exported-tests/manifest.json` | 导出 case 清单、分组与 input / answer 配对 |
| `exported-tests/sample/`、`secret/` | 已导出的样例和隐藏 `.in` / `.ans` |

当前题包均为非交互、GNU++20，时限 1000–6000 ms、内存 256–1024 MiB；manifest 合计 352 组。配置路径从题目根解析，测试路径从 `exported-tests` 解析，`inside()` 统一 Windows 反斜杠并检查文件存在和目录边界。manifest 中原机器的 `workspace` / `outputRoot` 不参与定位。

题面、checker、testlib、manifest、配置、图片及全部输入 / 答案参与内容摘要；`App` 再结合历史内容生成 `input_id`。实际文件决定导入和隔离，截图中的标题、人数与日期不覆盖比赛输入。

## 7. 真实判题与 skill 的关系

项目兼容 [ICPC-Problem-Creator.skill](https://github.com/Lumine2024/ICPC-Problem-Creator.skill) 的题包配置、导出数据和 testlib checker 调用方式。运行时由本仓库 Python 实现，不依赖作者机器的 `.claude` 路径，也未复制其 PowerShell 脚本。来源和许可记录见 [THIRD_PARTY.md](THIRD_PARTY.md)。

原题包维护所参考的本机 skill 入口是 `C:\Users\123\.claude\skills\icpc-problem-creator\SKILL.md`，其 `scripts/run-all-tests.ps1`、`scripts/export-testdata.ps1`、`scripts/lib/icpc-common.ps1` 和 `subskills/judge-validator/SKILL.md` 属于外部 skill。出题、重建测试与 Hydro 导出不在 OJ 用户提交链路中。

`backend/judge.py::Judge` 的实际工作流：

1. 启动时解析各题编译器，HTTP 接收提交后写库并立即返回 ID。
2. 单后台 worker 取队列任务，将状态更新为 Compiling；源码写入独立任务目录。
3. checker 按源码、testlib、编译配置、标准和编译器路径摘要缓存；C++ 按 `build.cppFlags` 和标准模板编译，并添加 include 路径。Windows 编译设置 256 MiB 栈。
4. 编译失败 / 超时判 CE，重新评测前移除旧提交二进制；Python 用语法编译检查映射 CE，再由当前 Python 的 `-I` 模式执行。
5. 状态更新为 Running，按 manifest 顺序运行全部样例和隐藏 case，输入通过文件重定向，保存 stdout / stderr。
6. 用户程序正常结束后运行 `checker input-file contestant-output-file answer-file`；成功才进入下一组，失败提前停止，全部通过判 AC。
7. 结果和资源峰值写库，内部逐 case 记录写入任务目录，再由业务层生成个人记录与公共成绩。

状态包括 Queued、Compiling、Running，以及 AC / WA / TLE / MLE / RE / CE / OLE / Judge Error。checker 的选手输出错误码 1、2、4、8 映射 WA，内部失败、超时等映射 Judge Error；checker 诊断、隐藏答案与逐 case 内部日志不返回选手。

`backend/runner.py::run()` 使用文件 I/O、墙钟超时、进程树内存监测和输出上限：单 case 使用题目配置限制，编译最多 120 秒，checker 最多 10 秒，stdout 上限 16 MiB、stderr 上限 1 MiB。计时从创建完成、恢复执行至退出，不包含 OS 创建进程和 Job 初始化开销。

Windows 使用挂起启动、Job Object 和派生进程跟踪，退出 / 超时 / 取消时终止并等待进程树，包括 Windows Store Python 的派生代理。Linux / macOS 使用独立进程组和 RSS 采样。监测约每 3 ms 一次，度量受系统调度与硬件影响；这是本地资源控制，源码仍以当前用户权限运行，未建立不可信代码的系统沙箱。

## 8. 状态、缓存和日志保存在哪里

`backend/storage.py::Storage` 使用 SQLite、WAL、外键和锁串行化数据库操作。`settings` 保存服务密钥，`sessions` 保存 owner、输入标识、队伍、开始时间和固定人数，`submissions` 保存接收时间、经过时间、源码、判定、诊断、已通过 case 数及内部资源数据。`recover()` 将同一输入的未完成提交恢复为 Queued。

默认数据根目录为 `tmp/ccpc-local/`，也可由启动参数替换：

| 数据根目录内路径 | 保存内容 |
| --- | --- |
| `state.sqlite3`、`-wal`、`-shm` | 持久化身份关联、会话、源码和判定 |
| `server.log` | HTTP 访问与服务内部错误 |
| `judge/cache/<题号>/<摘要>/` | checker 二进制及编译日志，可重建缓存 |
| `judge/jobs/<提交ID>/` | 提交源码、编译产物、运行输出、checker 输出、`result.json` 或异常日志 |

题包、历史和参考图作为只读输入使用，应用状态不写回题包。清理 checker 缓存不会删除提交历史；源码也在数据库保存，SQLite 是会话恢复的持久化入口。任务与日志长期保留，评测目录不通过 HTTP 开放。

## 9. 验证脚本与已保存的证据

| 入口 | 验证内容 / 输出位置 |
| --- | --- |
| `tests/test_core.py` | 阈值与去重、“其他3题”、ICPC、封榜边界、延迟判定、解析、路径、真实数据与样例一致性 |
| `tests/test_api.py` | 开始幂等、提交验证、会话隔离、Host / Origin / CSRF、资源白名单、封榜与结束、重启恢复 |
| `tests/test_runner.py` | 超时、取消、RE、MLE、OLE，以及根进程退出后的子进程清理 |
| `scripts/unit_acceptance.py` | 运行测试并保存 `tmp/acceptance/unit-results.json`、`unit-tests.log` |
| `scripts/acceptance.py` | 13 题主标程全量、每题错解、六类异常探针、输入摘要复核；`tmp/acceptance/judge-results.json` |
| `scripts/reference_acceptance.py` | 独立 C++ 参考解按 `cases` / `groups` / `checkWith` 范围交叉验证；`tmp/acceptance/reference-results.json` |
| `scripts/python_acceptance.py` | Python L 题 38 组 AC 与语法错误 CE；`tmp/acceptance/python-results.json` |
| `scripts/browser_acceptance.py` | 真实启动、VP、样例复制、公式 / 图片、上传与 AC、刷新、隐藏榜单、桌面 / 手机；`tmp/browser-acceptance/` |
| `scripts/phase_acceptance.py` | 注入时钟的两小时 / 四小时 / 五小时浏览器验收、最终结果与旧会话；`tmp/phase-acceptance/` |
| `scripts/launcher_acceptance.py` | Python 环境回退、空格路径、占用端口、错误环境与正常退出；`tmp/acceptance/launcher-results.json` |
| `scripts/package_acceptance.py` | 读取已通过结果，将报告、JSON、日志和截图整理到 `docs/` |
| `scripts/vendor_assets.py` | 下载固定 npm 版本、校验 integrity、重建 `frontend/vendor/`；仅依赖维护时联网 |

快速规则 / API / 进程回归入口：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

各验收脚本以同一 Python 执行，例如 `.\.venv\Scripts\python.exe scripts/acceptance.py`。浏览器环境准备、完整复现命令和逐题结果位于 [README.md](README.md) 与 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。

已保存的 2026-10-04 Windows 验收包含：30 项自动化测试通过、13 题主标程全部 352 组 AC、每题错解拒绝、六类异常判定、13 题适用范围内独立参考解、Python L 题，以及完整浏览器 / 启动 / 阶段流程。题包摘要前后一致。`docs/acceptance/` 中 7 份 JSON、原始测试日志和 9 张截图提供对应证据；这是一份已执行的验收快照。

两小时时，真实历史达到阈值并公开的题目为 A/G/L。严格早于四小时的历史通过人数基线如下，本地 AC 会在相应题目上增加人数：

| A | B | C | D | E | F | G | H | I | J | K | L | M |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 290 | 6 | 0 | 0 | 1 | 2 | 253 | 0 | 182 | 108 | 14 | 386 | 83 |

阶段截图使用服务端注入时钟和真实历史，未等待实际五小时，也未增加生产调时接口。H / K 的部分参考解限定小数据，参考解验收按配置范围运行；主标程仍覆盖各题全部 case。

## 10. 后续维护的定位与当前边界

| 关注点 | 代码入口与关联验证 |
| --- | --- |
| 阈值、罚时、封榜和最终结果 | `scoreboard.py` → `test_core.py`、`test_api.py`、`phase_acceptance.py` |
| 导入格式、题包路径与内容标识 | `contest_parser.py`、`problems.py` → `test_core.py` |
| 会话、提交时间与赛时信息过滤 | `contest.py`、`storage.py`、`server.py` → `test_api.py` |
| 编译、checker 和结果分类 | `judge.py` → `acceptance.py`、`reference_acceptance.py`、`python_acceptance.py` |
| 资源限制与进程清理 | `runner.py` → `test_runner.py` 和真实判题验收 |
| 页面、题面和交互 | `frontend/` → `browser_acceptance.py`、`phase_acceptance.py` |
| 启动和环境诊断 | `launcher.py`、`launcher.ps1` → `launcher_acceptance.py` |

当前实现支持本地非交互题训练，交互题导入明确拒绝；没有账号系统、云部署、Codeforces 登录抓取或出题编辑器。不同浏览器有独立 VP 身份，各自与历史队伍比较，公共成绩不合并其他浏览器的 VP 队伍。

Windows 已完成真实启动和判题验收；Linux / macOS 有路径与进程组适配，尚未运行验收。前端所需 Marked 15.0.12、DOMPurify 3.3.1、KaTeX 0.16.33 及字体已内置，正常运行可离线使用；精确来源和 integrity 在 `frontend/vendor/manifest.json`，许可在各 vendor 目录与 `THIRD_PARTY.md`。项目代码协议见 `LICENSE`，原题包与第三方材料保留各自声明。
