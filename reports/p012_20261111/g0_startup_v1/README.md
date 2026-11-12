# Qwen G0-E 首次启动

首个模型为固定 revision 的 Qwen2.5-1.5B-Instruct。按 MATH-500 原始顺序取前 20 题，以 n=4、temperature=0.7 做 S1–S4；这 80 条输出仅作启动检查。检查通过、按实测耗时更新费用预测后，完整 500 题以已冻结的 greedy 配置评测。

[输入清单](INPUT_MANIFEST.json)固定数据来源、文件哈希和 ID 顺序。[首次配置](FIRST20_CONFIG.json)不随检查结果修改。[费用预测](FORECAST.json)使用此次实际 Modal 费率，首次执行尚无实测吞吐；启动预算估计为 $0.9953（包括环境构建、缓存和杂项预留），计入 G0-E 的 $4 上限。

共享工具：`experiments/p012/g0_tools.py` 冻结输入并执行 S1–S4；`modal_g0.py` 使用标准 Modal/vLLM 调用，CPU 缓存模型、L4 执行，每次保留原始记录和日志。平台超时为 24 小时，没有自定义预算终止器，没有自动重试。启动器按负责人决定与 F4/F5 一起在 C8 前送审。
