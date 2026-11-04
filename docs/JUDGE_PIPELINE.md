# checker 预构建与判题流水线

2026-10-05：服务启动时即准备全部 checker，提交处理只编译选手程序，并重叠执行上一点 checker 与下一点选手程序。

## 启动与提交

`App` 启动后台 `Judge.worker()` 后，worker 首先执行 `prepare_checkers()`，利用内容摘要缓存加载 checker；缺少缓存时最多两个编译器并行构建。网页和 API 正常启动，提交可进入队列，但在全部 checker 准备完成前保持 Queued，预构建期间不运行选手程序。重启后的未完成提交也遵循同样顺序。

checker 构建到临时文件，成功后才发布缓存，避免关停留下半成品。单题构建失败记入服务端日志，该题返回 Judge Error，其余题仍可判题。预构建在服务启动时开始，早于用户点击 VP。

处理提交时只读取已经准备好的 checker 路径，不按需编译 checker。独立调用 `Judge.evaluate()` 的脚本应先调用 `Judge.prepare_checkers()`；仓库验收和性能脚本已同步更新。

## 每次提交的流程

1. 构建选手程序；C++ 编译失败或 Python 语法错误直接返回 CE。
2. 运行第一个测试点，按题包的时限、内存及输出限制保存结果。
3. 将该点交给独立 checker 线程，同时开始运行下一点。
4. 按 manifest 顺序确认判定；上一点成功且下一点正常退出后，再检查下一点并运行后续点。
5. 最早失败立即触发提交局部取消，清理提前运行点的进程树；所有点通过才返回 AC。

```text
选手程序： run(1) ── run(2) ── run(3) ── ...
checker ：           check(1) ─ check(2) ─ ... ─ check(last)
```

最多一个选手程序和一个 checker 并行，最多提前运行一个点。如果选手程序比上一点 checker 更早结束，会等待上一点结果，不继续扩大提前运行范围。一个后台 worker 仍依次处理不同提交。

每点独立保存到 `judge/jobs/<提交ID>/cases/<五位序号>/`，包含 `program.out`、`program.err`、`checker.out`、`checker.err`。checker 读取该点自己的输出，下一点不会覆盖它。选手及 checker 的工作目录仍为该提交根目录。

上一点 WA / checker 异常优先于提前运行点的 RE / TLE；弃用点在 `result.json` 中标记 `discarded: true`，不增加 checked，不影响最终资源峰值。局部取消不会停止整个服务。关停会取消两个阶段并将提交保留为 Queued，重启后重新评测。

## 验证与测量

60 项单元测试通过，覆盖预构建先于恢复队列执行、构建失败隔离、中断缓存、两个阶段实际重叠、输出隔离、fail fast、最早失败优先、最后一点失败、checker 异常、关停以及真实子进程清理。结果见 [单元测试](pipeline/unit-results.json)、[完整日志](pipeline/unit-tests.log)。13 题主标程全部 352 组数据 AC，全部错解正确拒绝，六类异常探针符合预期，输入摘要前后一致，见 [判题验收](pipeline/judge-results.json)。真实网页提交流程通过，首次使用全新数据目录成功构建全部 13 个 checker 后得到 L 题 AC，见 [预构建日志](pipeline/prepare.log)、[浏览器验收](pipeline/browser-results.json)。

真实 A 题错解的 [fail fast 记录](pipeline/fail-fast-example.json) 显示：第一点 checker 返回 WA，已提前启动的第二点返回 Cancelled 并标记 `discarded`，最终结果保持 WA、checked=0。

Windows 本机 A / L 各两轮完整提交测量全部 AC；不含预构建、排队和页面刷新耗时：

| 题目 / 语言 | case 数 | 两轮提交耗时 |
| --- | ---: | --- |
| A / C++ | 30 | 13.810 s、14.027 s |
| L / C++ | 38 | 14.250 s、13.150 s |
| A / Python | 30 | 13.314 s、12.843 s |
| L / Python | 38 | 12.522 s、12.984 s |

原始 [性能数据](pipeline/benchmark.json) 分别累计编译、选手运行、checker 耗时。并行阶段有重叠，分阶段耗时相加可能大于整次提交耗时，不能直接相加作为延迟。测量受系统负载、进程启动和缓存影响，前一轮串行测量保留在 [Windows 监控优化报告](JUDGE_PERFORMANCE.md)。

```powershell
.\.venv\Scripts\python.exe scripts/unit_acceptance.py
.\.venv\Scripts\python.exe scripts/acceptance.py --output tmp/judge-pipeline-acceptance
.\.venv\Scripts\python.exe scripts/judge_benchmark.py --problems A L --rounds 2 --output tmp/judge-pipeline-benchmark
.\.venv\Scripts\python.exe scripts/browser_acceptance.py
```
