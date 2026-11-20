# B1/B3 学生：源码增量 CR + 实际输入 A1 + 数值 A2-lite

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-B-retained-students-complete-path-CR-A1-A2-lite`
- **target_commit**：`0f0d78d3f5c0d38f121b073bbf4e02e7665deabf`（在 8bfdaada 上核对）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `05b8c123a3ed2b9eb6d7eff110d04fbc47b29ec2ff6f811c201aeeed4e9df7e3` |
| jobs_sha256 | `a4c5fc8f2fbf7e623e4292398c376786185366faae1f2f5d757cad6919838665`（只有 B_B1_s17_r1 和 B_B3_s17_r1） |
| source_files | 96 个，sha 全部一致。与已接受的 e723639f 相比只有 `scripts/p011_b_students_io.py` 不同 |
| failed_attempt_bindings_sha256 | `78051491dddd733cb2e59f169008e8ad7aa09a948bc6a8144c68f21f085a1282`（含两个长序列失败父任务和 B r1） |
| generation_actual_A3_report_sha256 | `885fce3707f712fc2156170c033b5e51e79072efe56e9174263ea394db6558e4` |
| student_input_CR_report_sha256 | `e1dbb3777dec87d1b26d8ff182aa7d1a9ed597416255ecddb5008e871caed90a` |
| student_input_manifest_sha256 | `ccd0bf33596e77acdc634d47ea1af404fb5adfa88242900c9470457a943c267d` |
| owner_B16 / budget_owner | `2e0c8af1…` / `364aaf6c…` |
| measurement_exceptions | 0 |
| 14 个 flag | **全部 true** |

## 源码增量（1 处）

`p011_b_students_io.py` 的本地 audit 原来要核对 base 模型除权重外的所有文件，现在只核对分词器加载所需的 5 个文件（config、tokenizer.json、tokenizer_config、vocab、merges），因为本地缓存里没有 README、LICENSE 和 generation_config。远端 worker 仍按完整清单校验模型，资产收据也不变。新增的测试在本机 OK。接受。

## 实际输入 A1（独立脚本 `b_input_a1.py`，结果见 `B_INPUT_A1.json`）

- 我自己解开归档 `ORIGINAL_INPUTS.tar.gz`（`d8063523…`），SPEC 中 B1/B3 各 6 个输入文件的 sha **全部一致**；GOLD.jsonl 为 `132582ca…` ✓，MATH_ENDPOINT 为 `8f9a0500…` ✓
- **B1 / B3 / B2（B2 只做核对，不会派发）逐条检查，0 处异常**：
  - path_id 顺序等于 A3 已核对的 SELECTION（K1 / K8 / K4）。
  - 每条 response 都等于我在 A3 中逐字验证过的 `answer_segment`。
  - 训练行中含未映射 token 的条数为 **0**。
  - 用我自己的 BPE 解码器解码 `input_ids[:-1]`，**完全等于** `prefix(prompt) + response`；prompt 段也逐字相等。
  - 最后一个 token 是 151643（base EOS），中间没有出现 EOS。
  - labels 的 prompt 部分为 −100，其余等于 ids；最长序列 1,282 / 1,300 ≤ 2048，没有截断。
- **P_cov**：B1 为 400（包含 1 题未验证回退，符合负责人的 B16 规则）；B3 为 399（回退题按规则不进 K8）。
- **剂量**：两者都是 1,024 次更新；Σ(暴露次数 × 监督 token) **恰好等于 2,097,148**；每次更新的出现次数与 `row_exposures` 一致；暴露次数 B1 为 11–12，B3 为 1–2（相差都不超过 1）。seed 17；LR 向量 sha 等于 P010 的 `LR_VECTOR_SHA256` ✓

## 数值 A2-lite

- **限额**：startup 600、platform 4,460、worker 4,400、评分 25,200、完整窗口 37,465 s，与已接受的预期一致。
- **计时**：情景估计为 4,321 s（保留训练最大值 43.3 s 和每批 22.95 s 的代理值，加 600 s 未校准余量和 20% 余量），低于 4,400 s。余量不大，超时就按硬计时失败，不重试。
- **预算**：B 已有预留 6.02。B1 6.18 ≤ 0.8 × 13.98 ✓；随后 B3 6.18 ≤ 0.8 × 7.80 = 6.24 ✓（余量 $0.06）。合计 18.38 ≤ 20。
- **截止时间**：05:00 UTC − 37,465 s = **18:35:35 UTC**，B1 和 B3 都要在此之前派发。
- **槽位**：F15 r2、基线 r2、B1、B3 正好占满 4 个。派发前仍要做新鲜的费率、D1、槽位、fence 和窗口检查。

## 不授权

B2 模型；重试；任何预留释放。
