# P011 C1 完整路径：源码 CR（第一份交付）

- **审计方**：Claude，2026-10-21 03:05 UTC 前后
- **请求**：`p011-C1-complete-path-CR-A1-A2-lite-r1`
- **本报告的 scope**：`p011-C1-complete-path-CR`（只覆盖源码）
- **不覆盖**：实际输入 A1 与数值 A2-lite（scope `p011-C1-complete-path-CR-A1-A2-lite`），这两项要等原字节复制完成、计时依据确定后，在同一请求下另出附录

## 结论：PASS-WITH-NOTES

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p011-C1-complete-path-CR` |
| target_commit | `817f7d67a4f8ea1d23f90bb41f85a6e893e48d9f` |
| binding packet | `reports/p011_20261020/c1_full_path_window_addendum_v1`，MANIFEST `1ad0723748842e6d856d41696cc383e945bca20606ab2ad09e86c898d94439d8` |
| original_group_binding_sha256 | `54e73b1cb1e69d300ee40423236e2d5d2f91e96e42ad03a81f10191256546006` |
| input_preparation_authorized | **true**（只授权一次原字节输入复制；不授权上传、worker、GPU 或任何付费调用） |

**source_files**：12 个文件，与 addendum 的 SOURCE_BINDING 完全一致，我已在 HEAD `c33424c9` 上逐个重算：

| 文件 | sha256 |
|---|---|
| `experiments/learning_regime_p009/requirements_p0.txt` | `375f161f867fe5bcdf846d5423fbdba991be4c7ee189d1dde9b5e52a39337b69` |
| `experiments/p011/__init__.py` | `ef9c51d51d8ce9f6523be02a6d2c80266d431b6dbd25f816249946158789021d` |
| `experiments/p011/c1_admission.py` | `9e1e3b449583729bf16e734dc2dd4ac258c3ab04bcc35e66a4e79b8ae388361f` |
| `experiments/p011/c1_artifacts.py` | `b6404ddd4dc8eb0acf6a9205dfec30ce431467094bad14af1cc29456164ee773` |
| `experiments/p011/c1_evidence.py` | `75681d883e3f9163ec3cc8d789fa7bf1246aef3c7e0e94d91fc868f88e0ad974` |
| `experiments/p011/c1_execution.py` | `1f4c84912d14950779dc1583c7f733ec49989d0e3b1d7ab476d7cd717143a8e6` |
| `experiments/p011/c1_nll.py` | `fe998fe3a210b5730c98273b77db70582297de07fb59bfcd6705e16306317d7a` |
| `experiments/p011/c1_outer.py` | `524b90daa93f331938185dcd53e90a3c36b187ea1a06043bf8453a58ec1e8b65` |
| `experiments/p011/modal_c1.py` | `48a87918064b78ae07f6efd8636b7cceda405b636a47392a80579c7384ff8cc0` |
| `experiments/sft_allocation_midpoint/common.py` | `4063c6d39640752d4946e473fa4b9f5b94c5fa033859f2ac81962a536b21242c` |
| `scripts/p011_c1_io.py` | `21746961f3c365f67506bf0440ae137d2f5ad0009a392191e576521762a565fe` |
| `scripts/prepare_p011_c1_inputs.py` | `d2aefd91ad5c03811ffea65a052b7a3923ff773fe266a0a5493bd2409d0c5b2e` |

## 逐行审查要点

### 输入追溯（fixed check：remote_path 与原 writer）

- **六组原始文件全部可追溯**：ORIGINAL_GROUP_BINDING 中 18 个文件的 sha 和两个原 MANIFEST sha，都能在已有的公开记录中找到。
  - T15：P009 `stage1_s1_inputs_v1`，MANIFEST `9c492899…`；P010 seed29 的 INPUT_MEMBERS 也使用了同一批文件。
  - T7/T72：P010 `student_runtime_k1_e1d_v1` 的 MANIFEST `80b01f5d…`，以及 k1 输入迁移对账记录。
- **嵌套假设已核实**：`inventory` 要求 n400 是 n3200 的**有序前缀**，否则复制会永久失败。我核对了：
  - T15 由 `nested_encoded_sets` 按 `ordered[:n]` 生成；
  - T7、T72 的 SELECTION.json 中，n3200 的 question_ids 和 selected_ids 前 400 个与 n400 完全相同；n400 的未验证兜底题是 n3200 的子集；
  - T7 与 T72 的 3,200 道题完全相同。
- **基座模型**：`/evidence/mp-engineering-20261012-r1/assets/model` 与 P010 seed29 SPEC 使用的是同一路径和同一 revision `8faed761…`（Qwen2.5-1.5B 基座）。加载时还会用 spec 中的文件清单再验一次哈希。
- **远端路径**：
  - 输入：上传写入 volume 路径 `INPUTS.removeprefix('/evidence')/name`，worker 从 `/evidence/p011-20261020/c1_inputs_r1` 读取，两边一致 ✓
  - 输出：`pack(out/'payload')` 在 payload 目录下写 `evidence.tar.gz`；collect 读取 `REMOTE.removeprefix('/evidence')+'/payload/evidence.tar.gz'`，两边一致 ✓

### 科学核心

- **`c1_nll.forward_one`**：
  - 第 j 个 token 由第 j−1 位的 logits 预测，监督范围包含原 EOS 151643；
  - 不用缓存，eval 模式，未加载 LoRA；
  - 只对选中位置的 logits 转 FP32 再算交叉熵 ✓
- **`checked_sequence`**：掩码必须正好是 `[-100]*prompt + ids[prompt:]`，EOS 只出现一次且在末尾，长度不超过 2048。这与 P010 的编码一致 ✓
- **`inventory`**：
  - 只合并 token 和掩码完全相同的序列，每条原始回答保留各自的组成员关系和兜底标志；
  - T15 必须全部是 attempt01 且没有兜底；
  - T7/T72 的兜底回答必须是 attempt 1，attempt 范围 1–4 ✓
- **`descriptive_summary`**：
  - 必须拿到完整的确认集合才汇总，缺任何一条就报错；
  - 按 token 加权计算 NLL，另报每条回答平均 NLL 的分位数；
  - 每组分 all / nonfallback / fallback 三个子集；
  - 只做描述统计，不做任何检验 ✓

### 运行路径

- **`run_body`**：
  - 顺序：先确认 claim，再写 INTENT 和初始预测，然后加载模型；
  - 每 32 条为一个 chunk：先写 store 记录（只写一次，不重放），再逐条前向并保存结果，commit 之后才写 CONFIRMED；
  - 任何失败都保留部分结果，不重试 ✓
- **`forecast`**：
  - 预测时长 = 1.2 × (已用时间 + 剩余 chunk 数 × 最慢 chunk 时长 + 预留时间)，必须不超过 worker_seconds − 30；
  - 费用同时满足三个上限：不超过本次预留金额；C 类累计不超过 12；不超过 C 类剩余额度的 80% ✓
- **`load_base`**：
  - 固定版本、CUDA 12.8、H100 80GB；
  - BF16 + sdpa；关闭 TF32，开启确定性算法；
  - 所有参数冻结；拒绝任何 adapter ✓
- **入口与生命周期**：
  - `modal_c1`：缺少 SPEC 时直接失败；单个 H100；retries=0；超时取 spec 的上限；在 Dict 中只写一次 dispatch 记录，然后只 spawn 一次 ✓
  - `worker_body`：在写 claim 之前，依次核对源码、intent、报告字节、启动时间窗和截止时间 ✓
  - 失败时写 FAILURE 和 terminal ✓
- **`c1_admission`**：
  - 共享账本统计所有类别，pending、未知、失败的尝试都保留预留额度；无法对应的容器计入 4 个并发槽 ✓
  - 受保护余额 48、总额 180、各类别上限都不允许挪用 ✓
- **`c1_artifacts`**：
  - 打包只允许相对路径的 .json 文件，不允许链接；
  - 解包前先核对名单和大小，再逐个核对哈希；
  - 完成判定必须同时满足：原 receipt、STOPPED、0 个容器在运行 ✓
- **`p011_c1_io`**：
  - upload：先读回远端文件；已存在且字节相同才复用，不同则报错；
  - collect：只处理已完成的调用，只读取指定名称的记录；
  - audit：重放原 admission 快照，不查询云端；
  - 三者共用同一个绝对截止时间 ✓

### 测试

本机没有 torch、modal 和 pytest。我用 `unittest` 跑了 6 个 C1 测试文件（io_window 3、io 6、outer 9、execution 12、evidence 7、admission_artifacts 10）：**46 项通过**，1 项因为本机没有 torch 无法导入，不是代码错误。

## 注意（附带条件）

1. **chunk 计时漏算了 commit 开销，A2-lite 必须处理**
   - 每个 chunk 调用 3 次 `volume.commit()`，但 `ack.elapsed_seconds` 只包含其中 1 次，另外 2 次（写 INTENT 之后、写 CONFIRMED 之后）不在内。
   - 预测"剩余时间"时，用的是 `剩余 chunk 数 × 最慢 chunk 时长`，因此会系统性低估。
   - 总 chunk 数约 300，即使每次 commit 只要 1 秒，也会漏掉约 600 秒，超过最低预留时间 300 秒。
   - 后果不是超支（平台 timeout × 费率已经锁在预留金额之内），而是**跑到中途因预测超限而失败，且不能重试**。
   - A2-lite 需要二选一：
     - (a) 改代码，把每轮迭代从开始到最后一次 commit 的完整用时作为预测输入（`check_body` 的回放要同步修改）；
     - (b) 不改代码，但令 `future_allowance_seconds ≥ 2 × chunk 数 × commit 用时的保守值`，并把 worker_seconds 设得足够宽。

   我倾向 (a)。改动属于源码变更，需要再做一次简短 CR。

2. **计时依据尚未确定**
   - 旧的训练 update 计时包含反向传播和优化器，用来估计纯前向是保守的；但它按 token 缩放，低估了 batch=1 时每次调用的固定开销（短序列也有约数十毫秒）。
   - 如果使用代理计时，A2-lite 中需要给每个 chunk 设下限（例如 32 × 0.1 s），再加上第 1 点的 commit 开销。

3. **共享账本**：`c1_outer.ledger` 只统计 `.local/p011_20261020/r1/dispatch` 下的记录。后续 A、B、C2、D 的长训练入口**必须写入同一个账本**，否则 C1 的预算核算会漏掉它们。我会在运行时 CR 中专门检查这一点。

4. **数值精度**：logits 是 BF16，转 FP32 后再计算交叉熵，每个 token 的 NLL 分辨率约为 1e-2 nats。用于描述性的组间比较足够；不应解读小于约 0.01 的差异。

5. **结论只能是描述性的**：C1 只描述基座模型对各教师回答的条件概率，不能直接证明"可学性"导致了 Δ_T 为负。T15 组是按 attempt01 答对来筛选的，这个选择偏差仍然存在。

6. **本报告不授权上传、worker、GPU 或任何付费调用。** 复制完成后，我会在同一请求下另出 A1 + A2-lite 附录。
