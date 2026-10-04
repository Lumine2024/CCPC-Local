# M. kingdom

本工作区整理自 2025 ICPC 陕西邀请赛 M 题照片。`docs/statement.md` 是题面，`docs/tutorial.md` 包含正确性证明和复杂度分析。`src/solution.cpp` 与 `src/solution2.cpp` 分别使用多源 Dijkstra 和多源 BFS 计算王国领地，再用 LCA 计算路径上的领地边界数。

`config.json` 驱动样例、边界、随机和满规模测试，并交叉验证两份 C++ 解及小规模 Python 解。验证命令：

```powershell
./scripts/run-all-tests.ps1 -Workspace examples/shaanxi-2025-m-kingdom
```
