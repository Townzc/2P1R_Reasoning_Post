# B 生成输入：实际 A1

- **审计方**：Claude，2026-10-21 07:05 UTC 前后（负责人夜间全权审核期间）
- **共享请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`，本报告覆盖其中的实际生成输入 A1
- **target**：`1d0d1d6d1ede001949c64d3675b214ecf2feb5f7`
- **packet**：`b_generation_inputs_actual_v1`
  - PUBLIC_MANIFEST：`8e0d7ec0…`
  - 构造器 MANIFEST：`c5c07404…`
  - archive：`37c62ea0…`，735,237 bytes
- **源码**：bca90236，71 个文件；源码 CR 见 02e5f944 / d60b3cb9

## 结论：PASS

| 检查 | 结果 |
|---|---|
| archive 中 5 个原文件的 sha 与 ACTUAL_INPUT_BINDING 一致 | ✓ |
| ordered400 共 400 个、互不重复，digest 为 `7e5d15fe…` | ✓ |
| **ordered400 与 P009 S1 n400 的原顺序完全相同**（我用 C1 已核对过的 P009 `s1_s17_n400_rows.json` 独立比对） | ✓ |
| 400 道题的题面文本与 P009 S1 行中的 prompt 逐题相同 | 400/400 ✓ |
| 6400 条请求按 pid × attempt 1–16 排序；candidate_id、problem_id、model=t15 全部一致 | 0 违规 ✓ |
| **seed 独立重算**：`sha256('p009-math-teacher-seed17:'+cid)[:16] mod 2^31`，与 P010 `seed_for` 的公式相同；attempt 1–4 与 P010 T0.8 构成共同随机数 | 0 违规 ✓ |
| 采样参数：除 temperature=1.0 外，与 P010 `sampling` 完全一致（top_p 0.95、max_tokens 1024、停止 token [151645, 151643] 等） | 0 违规 ✓ |
| prompt token 与 pack 中的 prompts 一致，长度 + 1024 ≤ 2048；400 条 prompt 都以原 system 头 `151644 8948 198 5501 2874` 开头 | ✓ |
| rows 的 digest 为 `88141657…`，与 COMPLETED 中记录的一致 | ✓ |
| **GPU_PACK 不含 gold 或 solution**：只有 ordered400 / prompts / rows / source{problem} 这几个字段。"solution"一词出现了 11 次，都在题面文本里 | ✓ |
| PACK 中的 400 条 gold 都是非空字符串，只保存在本地 | ✓ |

## 限制

- 原 P010 的 `t15_fixed_requests.json`（私有，`96b0aa9b…`）我无法直接读取，所以 prompt token 与 P010 逐字节相同这一点，只能间接确认：system 头一致、题面一致，并且构造器在运行时已核对过原文件的 sha。
- 本 A1 **不授权**任何 GPU 运行或付费调用。B 的数值 A2-lite 还没有提交，需要包含：生成 job 的完整轮次计时、根据 P010 实测设定的 score_seconds、按 05 UTC 截止计算的结果窗口、按 $228 口径的预算。
