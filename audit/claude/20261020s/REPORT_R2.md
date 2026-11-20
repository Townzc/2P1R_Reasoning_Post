# P011 长链数据构建路径 CR：第 2 轮（复审）

- **审计方**：Claude，2026-10-20 22:45 UTC 前后（实际时间以 git commit 时刻为准）
- **请求**：`p011-OT3-AM-long-data-construction-CR-r2`
- **scope**：`p011-OT3-AM-long-data-construction-CR`
- **目标提交**：`df4d590485a2bb6b8cb2eeb02e8688f64ebd03db`
- **packet**：`reports/p011_20261020/long_data_preflight_v2`，MANIFEST SHA `c8648dde2563e098c753a18a0980882d8264c36ece615bab58d245129b442242`

## 结论：PASS-WITH-NOTES

| 绑定字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p011-OT3-AM-long-data-construction-CR` |
| target_commit | `df4d590485a2bb6b8cb2eeb02e8688f64ebd03db` |
| source_files | `experiments/p011/__init__.py` `ef9c51d5…021d`；`experiments/p011/data_contract.py` `4bcb6227770d7db845527712ad3b08a26127e96c02ec46439ae0650bc7e42204`；`scripts/prepare_p011_long_inputs.py` `4468a80d82f0a80d6c217d92e54ac41b211dcf943b156432850bffb6405812e1` |
| source_lock_sha256 | `0e78298f49b86ee3de7182443eb052da422d14af14f423bceb3f728a1696fdb0`（未变） |
| plan_sha256 | `20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22` |
| owner_amendment_sha256 | `e58e8d721f740e438d82ef3f5e6ecea50970e3b507458ad3d77e07eacfe75c72` |
| proposal_sha256 | `f8d5816e362aa3ddc7108676f118af85cd6ccf3405cad6757c7f973521ea7756` |
| operational_details_accepted | **true**：第 1–5 项原样接受；第 6 项按 R1/R2 修改后接受 |

**三源映射（来自 SOURCE_LOCK，未变）**

| 来源 | HF 仓库 | 修订 | 文件 |
|---|---|---|---|
| ot3 | `open-thoughts/OpenThoughts3-1.2M` | `61bcf9d4eb38b30295efc2021227a63cc5bb34c8` | 120 个 parquet |
| am_thinking | `a-m-team/AM-Thinking-v1-Distilled` | `186b575b5cc2113f8ba81d4f4ac9ae2494633829` | `math.jsonl`，sha `aa0770c4…3189` |
| am_qwen3 | `a-m-team/AM-Qwen3-Distilled` | `498448170567e330435019c5321faa0a15e19118` | `math.jsonl`，sha `87d9ebe2…3b73` |

## 逐项复审（对照 r1 的 diff 逐行读）

**R1：剂量取各格最大值**
- `encode_and_plan` 中两种模式都改为 `budget = max(once.values())`。
- FROZEN_DOSE 记录了剂量定义，并明确"A7 不要求恰好一遍" ✓。

**R2：按遍训练**
- `whole_schedule` 每一遍用 `Random(f'17:pass:{e}')` 把全部回答打乱一次，共 q 遍。
- extras 先由 `exact_subset` 精确选出，再用 `Random('17:extras')` 打乱，接在最后。
- 全局长度分桶已删除，切分逻辑和 q/q+1 不变量检查保留 ✓。

**R3：按打乱顺序逐个检查，凑满即停**
- **OT3**：
  - 候选 = 行数为 16 的父题（`ORDER BY parent` 排序），用 `Random(20261020)` 打乱后逐个检查。
  - 先查完整性和去污染，两项都通过才分词查长度，这样省时间，而且判定结果与先后顺序无关。
  - 凑满 4,096 即停；不足则写出 INSUFFICIENT 并报错。
  - 行数不对的父题按全池统计；`ot3_order` 不再重复打乱 ✓。
- **D**：
  - 共同父题排序后用 `Random(20261021)` 打乱，逐个处理。
  - 每题先用 `choose_d_row` 定好用哪一行；被选中的行不合格时，不换成另一条 ✓。
  - 凑满 1,024 即停。
  - 来源一致性按全部共同父题统计，只查元数据 ✓。

**其他检查**
- **负责人修订绑定**：`admit_code` 要求 amendment 和 proposal 的 SHA 与 review 记录一致，并且 `budget_changed=false` ✓。
- **磁盘检查**：在建目录之前进行，要求可用空间 ≥ 1.5 倍输入字节数 ✓。

**我本地实际跑过的测试**
- 新增 8 项测试：全部通过。
- 原有 12 项：11 项通过。剩下 1 项需要 transformers，本机没有，未运行；这是 Codex 那边已经跑过的原生 tokenizer 边界测试。

## 注意事项（不阻塞）

1. **磁盘可能不够**：OT3 的 parquet 是压缩格式，入库后 sqlite 存的是未压缩的数学文本，实际体积可能超过 1.5 倍门槛。运行期间请留意。如果因磁盘满而失败，保留部分证据并汇报，不要自动重跑。
2. **A1 要报告的内容**：
   - 已检查前缀的长度；
   - 各项剔除计数；
   - 行数不对的父题数；
   - 难度分布（保留 vs 剔除，按前缀统计）；
   - AM verify_score 的例外计数；
   - 来源一致性；
   - 各格单遍 token 数、B、U；
   - 任何"凑不出精确剩余量"的失败。
3. **评测必须与训练一致**：评测 CR 必须使用与 `native_text` 完全相同的 prefix，包括默认 system 提示，并且按同样方式分词。
4. **本次通过的范围**：只覆盖代码，**不是 A1**。数据构建完成后，A1 另行审。
