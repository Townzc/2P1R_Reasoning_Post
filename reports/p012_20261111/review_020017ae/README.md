# P012 审查落实：F1–F3 与修订 2

依据：[Claude 审查 020017ae](https://github.com/Townzc/2P1R_Reasoning_Post/blob/020017aeb2f4904fa1652d8ea970edbf3069ddd5/audit/claude/20261111c/CR_C2_C4_295091d9.md)。负责人已授权修改 F1–F3 后直接启动 Qwen G0-E，首个模型先做 20 题的 S1–S4 检查。

- F1：停止集合加入训练模板结束符，保留具体停止 token；四个实际模型分词器均已验证。
- F2：Llama 原生模板日期固定为 `26 Jul 2024`，写入运行 manifest。
- F3：默认生成批大小改为 1024，继续分块落盘；记录加载和生成耗时。
- S4：预渲染输入关闭额外特殊 token；Llama 输入必须自带 BOS。

39 项相关测试通过。首次日期测试发现本机缺少 jinja2；安装锁定的 3.1.6 后该项通过。原始失败记录保留。以上均为本地测试，没有模型生成。

[ACCEPTANCE.json](ACCEPTANCE.json)记录授权与测试，[TOKENIZER_STOP_CHECK.json](TOKENIZER_STOP_CHECK.json)记录实际停止 ID，[AMENDMENT_2.json](AMENDMENT_2.json)冻结训练前基线口径。G0 使用本目录 `configs/` 中含 `template_family` 的配置；旧候选配置保留为历史版本。

Δ_SFT 主基线为四个固定对话示例、同训练模板和同 OMI-2 协议，base 与 Instruct 一致；基线只测 MATH-500 和 GSM8K。其他主对比仍使用完整 MATH test。F4、F5 与 Modal 启动器在 C8 前一起送审。
