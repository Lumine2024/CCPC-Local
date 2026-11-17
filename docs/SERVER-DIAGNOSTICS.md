# 持续诊断与长时间运行验证

诊断默认关闭。使用仓库自带题包启用低频采样：

```powershell
pwsh launcher.ps1 -ProblemList tests/ICPC-Shaanxi-2025-National-Invitational-Contest -Submissions tests/contest.txt -DiagnosticsInterval 30
```

Python 启动器对应参数为 `--diagnostics-interval 30`。
诊断写入数据目录中运行时生成的 `diagnostics.jsonl`，按 8 MiB 轮转，保留 3 个备份。
记录服务 PID、线程、句柄、RSS、CPU 累计值、子进程、活动连接年龄、队列与 worker 状态。
HTTP 断连记录异常类型和 Windows 错误码；判题记录各阶段启动、结束及 TLE 终止前的
CPU、内存、线程和输出大小。异常长连接或 worker 异常时保存服务线程栈。
诊断不记录请求正文或源码，也不通过 HTTP 提供下载。

监测线程以 Event.wait 等待采样间隔，避免忙等。wall 为 Unix 时间，mono 为单调时钟。
日志中的进程、命令和文件路径描述运行现场，不表示这些本机产物随 Git 分发。

## 独立实测

```powershell
.\.venv\Scripts\python.exe scripts/server_soak.py --config docs/diagnostics/soak-shaanxi.json --output tmp/my-soak
```

[示例配置](diagnostics/soak-shaanxi.json) 的题包、历史及 A / L 主标程均在仓库中。
默认真实运行 3 小时，每 4 秒读取状态、每 10 分钟提交两份主标程、每 5 分钟主动断连。
没有注入比赛时钟，不依赖浏览器。配置中的路径按仓库根目录解析；间隔、期望判定及
输入均可在 JSON 中调整。输出目录必须不存在，使用独立端口、SQLite 和评测目录。

以下文件由脚本生成，不是克隆仓库后应当存在的输入文件：

| 输出目录内路径 | 内容 |
| --- | --- |
| `scenario.json` | 本次配置副本 |
| `launcher.log`、`server.log` | 启动器与 HTTP / 业务日志 |
| `diagnostics.jsonl` | 持续诊断及逐阶段事件 |
| `client.jsonl` | 请求时延、主动断连、判定与异常 |
| `judge/jobs/` | 真实编译、程序与 checker 输出 |
| `summary.json` | 结束后生成的起止时间、正常退出情况和提交结果 |

提前停止时，在该数据目录创建 `diagnostics-stop.request`。
监测线程会在下一次采样后正常关闭服务与判题进程。
提前结束会被客户端记为未完成，不能作为完整三小时通过。
再次运行请使用新目录。刻意构造的断连标为 intentional_disconnect，不能作为自然故障证据。

## 相关回归

- [API 测试](../tests/test_api.py)：空闲与半截请求头连接按 15 秒策略回收；
  断连后不重复发送 500，已入库提交仍保留。
- [进程测试](../tests/test_runner.py)：监测线程暂停调度后，超时判定前重新确认进程是否退出；
  同时覆盖真实超时、取消、内存、输出和进程树清理。
- [判题测试](../tests/test_judge.py)：一次 TLE 复核、两次输出隔离、持续超时和最早失败优先。

执行 `python -m unittest discover -s tests -p "test_*.py" -v` 可运行上述回归。
本页提供可复现方法；不把本机未随 Git 提交的历史诊断文件作为验收附件。
