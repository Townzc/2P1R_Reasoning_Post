# P012 — C1 清单与首轮代码审查材料

依据：[v1](https://github.com/Townzc/2P1R_Reasoning_Post/blob/2e481b7d/audit/claude/20261111a/P012_PLAN_v1.md)、[修订 1](https://github.com/Townzc/2P1R_Reasoning_Post/blob/cbaa41fd/audit/claude/20261111b/P012_PLAN_v1_AMENDMENT_1.md)、[GPT Pro R1–R5](../../audit/gpt_pro/20261111/R1_R5_EVIDENCE_HANDOFF.md)。原文 commit 和 SHA256 见 [PLAN_SOURCES.json](c1/PLAN_SOURCES.json)。本目录是内部实验记录；课程报告、展示和对外讨论文字由负责人撰写。

| 项目 | 当前状态 | 证据 |
|---|---|---|
| Llama 官方访问 | 1B、1B-Instruct、3B、3B-Instruct 全部通过；本轮采用官方仓库 | [访问验证](c1/LLAMA_ACCESS_CHECK.json) |
| 主网格模型 | Qwen 1.5B 与 Llama 1B 的 base / Instruct 权重、分词器已下载，revision 与文件 SHA 已固定 | [Hub 元数据](c1/HF_ASSET_METADATA.json)、各 `*_FILES.json` |
| Li 数据与公开模型 | 长、短链数据各 5,383 行；两个 Qwen 1.5B SFT 检查点已下载 | [行数](c1/DOWNLOADED_ROW_COUNTS.json)、各 `*_FILES.json` |
| UWNSL 清单 | 论文 collection 为 6 个数据集、24 个模型；组织全部资源另列 | [论文 collection](c1/UWNSL_COLLECTIONS.json)、[全组织清单](c1/UWNSL_ORGANIZATION_INVENTORY.json) |
| Tinker M2 | 实际 API 返回 38 个模型条目；无 Llama-3.2-3B / 3B-Instruct，也无 Qwen2.5 | [原始响应](c1/TINKER_CAPABILITIES.json) |
| 环境 | LLaMA-Factory 与 lm-eval 固定在 Li 发布仓库 commit；训练、评测分别锁定 Linux 依赖 | [环境](c1/ENVIRONMENT_MANIFEST.json)、[默认值与覆盖项](c1/REFERENCE_CONFIG_PROVENANCE.json) |
| 评测器 C2 | 40 个本地测试通过；包括 20 个手工解析样例、完整落盘模拟和评分汇总 | [测试记录](TEST_RESULTS.json)、[审查请求](C2_C4_CODE_REVIEW_REQUEST.md) |
| G0-T 配置 | R1、R2、R3 YAML 已准备；有效 batch 8，G0 seed 42，主网格 seed 17 / 29 | [配置目录](candidate_configs/) |

M2 的条件不成立，因此不启动 Tinker 3B LoRA 轨道。E1 保留 v1 的 Modal 路线，11/15 根据实际结余决定；Tinker 的 OMI-2 后备教师和 OH 后 E4 保持原条件。

MATH 主指标和去污染范围均已改为完整 5,000 题 test；4 次采样只在 MATH-500 与 GSM8K test 上做。[网格契约](c1/GRID_CONTRACT.json)记录所有剂量和对比。P、K8、K4、R 均为 8,192 次样本呈现、1,024 个更新，L 为 1,024 次呈现、128 个更新。token 数、FLOPs 与费用仍须实测，不能把样本呈现相等写成这些量相等。

下一步：Claude 按 v1 §12 审查共享评测路径和训练配置，固定 G0 的提示词与评分口径；随后完成 GPU 环境验证、启动器和费用预测，先执行 Qwen 的 G0。主网格等待 G0 通过。当前没有 P012 模型推理、训练或实验准确率。

Built with Llama.
