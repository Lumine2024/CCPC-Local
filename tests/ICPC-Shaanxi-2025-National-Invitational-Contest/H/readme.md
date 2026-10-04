# H. subsequence

2025 Shaanxi National Invitational 题目 H。题面与两组样例按 `45844FDFEC28AF9ABEF01BD5B0A1465E.png`、`111364A52162D4BA6A911D6F1B1E4C25.png` 整理；第二组样例字符串是 `ddcbbbbbbc`。

运行 `pwsh -File scripts/run-all-tests.ps1 -Workspace examples/shaanxi-2025-h-subsequence` 进行完整本地校验。主解处理完整约束；独立 C++ 和 Python 参考解采用逐询问直接计数，只用于小数据交叉验证。生成器包含原图样例、小随机、同字母长段、交替字母、全同字母和满规模随机数据。
