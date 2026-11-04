# Polygon 包转换为 CCPC Local 工作区

`polygon_to_workspace.py` 是可复用入口，支持包含 `contest.xml` 的比赛 ZIP，也支持只有一个 `problem.xml` 的单题 ZIP。从 XML 按比赛题号关联题目，而非按文件夹名字排序。依赖仓库已有的 psutil，以及支持 GNU++23 的 G++；导入过程不需要联网。

```powershell
.\.venv\Scripts\python.exe scripts/polygon_to_workspace.py contest.zip --output output/contest-workspace
```

输出目录必须不存在。默认保留包中已经导出的输入和答案；缺失的生成器输入会按 XML 的 `cmd` 编译源文件并执行，缺失答案则运行 `tag="main"` 的标程。`--regenerate` 可重跑已有的生成器输入，并同步重建相应答案。命令参数保留原样，不额外添加测试序号作为 seed，也不执行包中 `.exe`、`.bat`、`.sh`。生成命令不经过 shell。

每组数据运行原 validator（如有），非交互题答案通过原 checker 自检。`--timeout 120` 控制导入阶段单个生成器、validator、标程的超时秒数；checker 固定最多 10 秒。这个限制与选手程序的赛时限制分开。编译默认最多 120 秒，使用仓库的进程树清理器。完成后通过 `backend.problems.load_problems()` 验证目录。

```text
contest-workspace/
├── problems/A/ ...                  # 非交互题，直接传给 --problem-list
│   ├── config.json                 # 时限、内存、GNU++23 与原 checker
│   ├── include/testlib.h
│   ├── src/checker/checker.cpp
│   ├── docs/statement.md            # 尽力转换，样例来自导出数据
│   ├── exported-tests/manifest.json
│   ├── exported-tests/sample/*.in, *.ans
│   ├── exported-tests/secret/*.in, *.ans
│   ├── polygon/                    # 原 XML、题面、生成器、validator、解法及资源
│   └── conversion.json             # 逐 case 生成来源、验证与资源记录
├── unsupported/M/ ...              # 交互题，输入、checker、interactor 独立归档
├── build/                          # 本地重新编译的二进制与原始日志
└── conversion-report.json
```

交互题不放进 `problems/`，保留 `interactive: true`，只物化输入，不伪造静态答案。当前 CCPC Local 不能判交互题。文件型提交 I/O、多 testset、不支持的源码语言、缺失手工数据、越界路径等会明确报错。失败结果保留在 `*.building-*` 目录供检查，不发布为成功的工作区；再次运行须使用另一个输出目录。源 ZIP 始终不修改。

HTML 题面去掉在线脚本并把公式改为本地可渲染格式，图片复制到 `docs/assets/`；仅有 LaTeX 的题面进行部分转换。原始文件保留在 `polygon/`，不保证所有 LaTeX 宏和复杂版式都完整转换。原题包的许可声明随源文件保留。

新导出的样例使用 `input1` / `output1`、`input2` / `output2` 等带编号围栏。网页也兼容已有题面的多组未编号 `input` / `output`，按各自出现次序配对并保留样例顺序。

## 从最终榜单生成近似历史

`standings_to_history.py` 用标准库只读解析 xlsx 的共享字符串、单元格、填色与合并范围。默认仅导出 AC；`--rj-distribution uniform` 或 `exponential` 可根据已确认的尝试次数补入近似 RJ。

```powershell
.\.venv\Scripts\python.exe scripts/standings_to_history.py board.xlsx --workspace output/contest-workspace --layout layout.json --source-duration-minutes 720 --warmup-minutes 20 --window-minutes 300 --rj-distribution uniform
```

表头完整、单工作表的常规表格可以省略 `--layout`；多工作表用 `--sheet` 指定。AI/OCR 生成的表格通常需要人工核对 `problemColumns`、`teamColumns`、`acceptedColors`、`headerRows` 和 `ignoredRows`。这些布局字段的实例见 [standings-layout.json](../uestc-school-contest-prelimery/standings-layout.json)。不要对未知表格直接套用这个布局。

本次按用户约定计算：原比赛为 720 分钟；每队以最早确认 AC 作为未知首投时间的近似，`估计开始分钟 = 最早 AC 分钟 - 20`，只保留 `0 <= AC 分钟 - 估计开始分钟 < 300` 的记录。开始分钟可能为负，遵循公式不额外截断。没有 AC 的队伍仍计入人数，开始时间记为未知。交互题的 AC 可用于估计开始时间，但从可加载历史中排除。

通过题报告总尝试次数为 k 时，在上一个严格早于该题 AC 的 AC 时间 x 与当前 AC 时间 y 之间插入 k−1 条 RJ；第一题的 x 为 0。同分钟 AC 使用相同的前一个时间。`uniform` 均匀插值；`exponential` 使用指数权重，时间集中在区间前段。先重建完整时间线，再截取五小时，因此窗口外 AC 之前的失败也可能保留。计分会按保留的失败次数增加每次 20 分钟罚时。

未通过题的尝试全部视为 RJ；已知最后失败时间时堆到该时间，未知时堆到五小时窗口的最后一秒。这些失败不会给未通过题增加罚时。无法确认尝试次数的格子写入未知报告，不猜测数量。失败发生时间无法从最终榜单恢复；窗口末尾堆放也无法判断原十二小时里哪些失败实际发生在五小时内。

输出为 `contest.txt` 和 `standings/` 内的结构化队伍、原始单元格、未知记录及报告。`reconstructed-events.json` 逐条记录插值依据、区间和窗口判定，`reconstruction-unresolved.json` 保存尝试次数未知项。真实 AC 秒数未知，分钟按分钟起点转换为秒。导出文件是五小时近似回放，原始十二小时结果保留在 JSON 中。

## 核对没有文本层的 PDF

`pdf_outline_standings.py` 针对本次 DOMjudge PDF 的矢量数字轮廓，在已目视确认的数字格子上建立模板，匹配绿色 AC 格子的时间，以及绿色/红色格子的总尝试次数。布局中需要提供位置、时间及小字号尝试次数的数字模板、颜色和可选汇总人数；无法明确匹配的数字列入未知项。脚本不调用在线 OCR。

```powershell
.\.venv\Scripts\python.exe -m pip install pymupdf
.\.venv\Scripts\python.exe scripts/pdf_outline_standings.py board.pdf --workbook board.xlsx --layout layout.json --output pdf-verified-ac.json
.\.venv\Scripts\python.exe scripts/standings_to_history.py board.xlsx --workspace output/contest-workspace --layout layout.json --verified-ac pdf-verified-ac.json --rj-distribution uniform
```

`--verified-ac` 使用 PDF 确认的 AC 时间、尝试次数和未通过格子替代对应 xlsx 识别结果，保留修复记录，并校验 xlsx 的 SHA-256 与队伍数量。该 PDF 脚本依赖 PyMuPDF；题包转换、已有 JSON 的榜单转换和 OJ 日常运行不依赖它。针对其他 PDF，需要重新核对模板和页面几何，无法通用于任意扫描件。

## 验证导出工作区

```powershell
.\.venv\Scripts\python.exe scripts/workspace_acceptance.py --workspace output/contest-workspace --output tmp/import-acceptance
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

`workspace_acceptance.py` 通过实际 App 加载题包与历史，再按题目配置的赛时时限、内存限制跑主标程，输出逐题 AC 结果、输入摘要前后对比，并检查空输出错解是否被拒绝。
