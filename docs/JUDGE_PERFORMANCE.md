# 判题性能优化记录

本页保留 Windows 监控优化阶段的测量与验收快照。当前 checker 预构建和逐点流水线的实现、结果见 [判题流水线说明](JUDGE_PIPELINE.md)。

2026-10-05 在本机 Windows 11、Python 3.12.5、GCC 上执行真实题目测量。优化针对 Windows 进程监控与清理的固定开销，测试组数、原 checker、编译参数、时限和内存限制保持一致。

## 完整提交耗时

测量包括选手编译、所有样例 / 隐藏数据运行、checker 调用及结果记录，不包括排队和浏览器轮询。checker 在测量提交前加载；首次构建耗时另存于 JSON 的 `checker_setup_seconds`。优化前每项测量一次，优化后每项连续测量两次，下面取优化后的平均值。性能测量与完整判题验收串行执行，均开启相同的 cProfile 分析。

| 题目 / 语言 | case 数 | 优化前 | 优化后平均 | 耗时减少 |
| --- | ---: | ---: | ---: | ---: |
| A / C++ | 30 | 19.986 s | 14.505 s | 27.4% |
| L / C++ | 38 | 20.268 s | 14.698 s | 27.5% |
| A / Python | 30 | 19.552 s | 15.510 s | 20.7% |
| L / Python | 38 | 19.523 s | 14.898 s | 23.7% |

原始数据：[优化前](performance/before.json)、[优化后](performance/after.json)。每次提交都得到 AC，且通过对应题目的全部 case。不同题包、硬件、系统负载及缓存状态会影响耗时；本次测量没有复现一分钟的单次提交。

## 实现

- Windows 通过 `QueryInformationJobObject` 查询当前 Job 的进程 ID，并复用仍在 Job 内的进程对象；内存监控继续汇总工作集 / 私有内存，并查询 Job 的内存峰值。
- 全系统进程树兼容扫描降为最多每 50 ms 一次，Python 启动时立即扫描，保留 Windows Store / 虚拟环境启动代理的跟踪。
- Job 统一终止和等待成员，Job 内已退出进程不再重复交给 psutil 杀死、等待。Job 外代理仍按创建身份清理。
- C++ 编译失败、Python 语法错误直接返回 CE，成功后才加载或构建 checker，省去无效提交的首次 checker 编译等待。
- 页面通常仍每 4 秒读取状态，有 Queued / Compiling / Running 提交时每秒读取，让完成结果更快显示。

原始分析：[优化前 profile](performance/before-profile.txt)、[优化后 profile](performance/after-profile.txt)。优化前四次提交及首次 checker 构建中，系统进程树扫描累计约 43 秒，psutil 等待累计约 13 秒。优化后八次提交中，这两项分别约 17 秒、4 秒；两份 profile 的提交次数和 checker 初始缓存状态不同，应结合完整提交表比较。

## 验证与复现

新增测试覆盖 Windows 多子进程内存汇总、超过初始容量的 Job 成员列表、父进程退出后的全部子进程清理，以及 CE 不构建 checker。完整 50 项单元测试通过，结果见 [日志](performance/unit-tests.log)、[JSON](performance/unit-results.json)。全量题目 / 错解 / 异常判定结果见 [判题验收](performance/judge-results.json)，浏览器交互结果见 [浏览器验收](performance/browser-results.json)。

最终全量验收中，B–M 主标程、全部 13 个错解和六类异常判定均符合预期；A 的 `random-small-6` 曾一次 TLE（1 秒，内存峰值 5596 KiB），所以原始全量报告的 `success` 为 `false`。随后 A 主标程独立复测两轮，均通过 30/30 case；此前的性能测量也全部通过。该次 TLE 的原因尚未确认，低内存峰值提示进程可能在启动阶段受阻。没有放宽时限，原始失败 [逐 case 记录](performance/A-first-run.json) 与 [独立复测结果](performance/A-recheck.json) 一并保留。

```powershell
.\.venv\Scripts\python.exe scripts/judge_benchmark.py --problems A L --rounds 2 --profile
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe scripts/acceptance.py --output tmp/judge-performance-acceptance
.\.venv\Scripts\python.exe scripts/browser_acceptance.py
```

性能脚本默认写入 `tmp/judge-benchmark/results.json`，记录每次提交的编译 / 程序 / checker 实测时间；使用 `--profile` 时另外保存 `profile.txt`。本页快照中的实现由一个后台 worker 串行执行提交和逐点 checker；当前实现保持提交串行，逐点运行与 checker 检查使用流水线并行。
