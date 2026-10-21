# P011 长序列 A/D 完整路径：源码 CR（第一轮）

- **审计方**：Claude，2026-10-21 06:10 UTC 前后
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **target_commit**：`db1aff076163606ded08776eca637c043d6c916b`（我在 HEAD `396e5275` 上审阅；31 个 source 文件的 sha 与 SOURCE_BINDING `7fd487d4…` 逐个一致）
- **packet MANIFEST**：`d9ebd31be8b695a2d6198c9667546874d4f3e86db2db98d5347b16a0f5e8cdd2`

## 结论：分成两部分

| 部分 | decision |
|---|---|
| **输入准备**（`scripts/prepare_p011_long_runtime_inputs.py` 及其依赖：`long_training.learning_rates/validate_plan`、`long_evaluation.request_roster`、`long_execution.validate_endpoint`） | **PASS**，`input_preparation_authorized: true` |
| **运行时路径**（训练、导出、vLLM 评测、打包、收集） | **CHANGES-REQUIRED**（R1–R3 必须修改；R4 需要负责人决定） |

输入准备授权所需字段：
- scope `p011-long-A-D-complete-path-CR`；
- source_files = SOURCE_BINDING 中的 31 个文件；
- input_basis_files = SOURCE_BINDING 中的 5 个文件；
- target 为 `db1aff07…`。

**理由**：输入准备只在 CPU 上运行，不会触发任何付费调用。它只按冻结的 path_id 选取已接受的编码、逐字节复制 plan、为三个臂生成 LR 向量，并对 600 个 prompt 做原生编码。下面 R1–R3 的修改不会触及这些函数，所以先跑输入准备可以和修复并行，节省时间。

**如果修复改动了上述任一函数，产出的输入必须作废并重新审。**

---

## 必须修改

### R1（阻断）：源码闭包缺少 `src/sft_data.py`

- `long_training.accumulate` 中有 `from src.sft_data import shifted_loss_sum`，但 `src/sft_data.py` 不在 31 个 source 里。
- `modal_long` 的镜像只加入 `spec['source_files']`，所以 worker 里**一定会 ImportError**。
- 报错发生在模型加载完、第一次 update 时。每个学生 job 都会因此失败，而且 once-only 的 job 身份会被永久消耗。
- 本地测试没发现这个问题，是因为本地仓库里有 `src/`。
- 我用 AST 扫描了全部 31 个文件的本仓库 import，**只缺这一个**。
- **修改**：把 `src/sft_data.py` 加入 source closure。`src/__init__.py` 可选，没有它也能作为 namespace package 工作。

### R2（阻断，S-F15）：全参训练的终态 checkpoint 超出容器内存

- `checkpoint.snapshot` 会把**全部可训练参数和 AdamW 状态**克隆到 CPU。1.5B 的 FP32 参数约 6.2 GB，m 和 v 约 12.4 GB，合计约 18.6 GB。
- `checkpoint.save` 写盘后又执行 `torch.load(..., weights_only=True)`，没有用 mmap，并做全量 `same()` 比对，内存里会再多一份约 18.6 GB。
- 峰值约 37 GB，**超过 `modal_long` 给的 `memory=(32768,32768)`，即 32 GiB 硬上限**。容器会在整个训练结束后才 OOM，正好是代价最大的时刻。
- LoRA 臂只保存 adapter 和对应的 Adam 状态，体积小，不受影响。
- **修改**（任选其一，或组合使用）：
  - (a) 全参 job 的 memory 提到 ≥ 96 GiB。spec 中按 job 设置，费率要相应计入。
  - (b) 校验改用 `torch.load(mmap=True)`，逐个张量比对，不要整体加载。
  - (c) snapshot 后先释放 GPU→CPU 的临时副本。

  我建议 (a) 加 (b) 一起做。
- 另外请**在 A2-lite 中给出全参 16k 序列的 GPU 显存估算**：
  - FP32 参数、梯度和 Adam 约 25 GB；
  - 16k × 151,936 的 logits：BF16 约 5 GB；`shifted_loss_sum` 中的 `[valid].float()` 再来约 10 GB；CE 和反向的临时张量约 10–20 GB；
  - 峰值可能接近 60–70 GB，不能想当然。

### R3（阻断，预算层面）：评测是 104 次串行的 32 条小批，吞吐太低

- `evaluate` 每次只把 32 个请求交给 `llm.generate`，引擎设置为 `max_num_seqs=32`。每一批都要等其中最长的生成跑完，最长可达 16,384 个新 token。
- 长链学生经常会跑到上限，单批可能需要约 150–300 s，104 批合计约 **4–8 小时/job**。
- 按 4.40 美元/小时计，单个 job 的评测约 $20–35；A 加 D 大约 14 个 job，远超 A 类 $115 和 D 类 $25。
- 计划 §7.1 里"A 约 $70–110"的预估，是以批量化评测为前提的。
- KV 预算是够的：
  - 1.5B 每个 token 约 28.7 KB，3B 约 36.9 KB；
  - 0.80 × 80 GB 减去权重，约 55–60 GB 可以放下约 1.6–2M 个 token；
  - `max_num_seqs=256` 可行，KV 放不下时 vLLM 会自动抢占和重算。
- **修改**：
  - 每次 generate 至少 256–512 个请求，例如 3,300 条分成 7 组 × 512 左右，每组之后照常 commit 和 ack；
  - `max_num_seqs` 至少 256；
  - `max_num_batched_tokens` 可以保持 8,192 并开启 chunked prefill；
  - 同步修改 `validate_engine`、预测中的 batch 数（目前硬编码为 104）、`long_evidence.verify_endpoint` 的分组和 `expected_record_keys`。
- 每个请求的 seed 不变。批次组成变了，在数值上可能有极小差异，但所有格子都用同一个协议，所以是可比的。

---

## 需要负责人决定

### R4：长训练没有任何 GPU 实测，而运行规则是一次性、不重试

- `long_training.load_model` 新加了 `torch.use_deterministic_algorithms(True)`。仓库里此前所有训练器（`src/experiment.py`、`real_math_experiment.py` 等）**都没有**这样设置。
- 在确定性模式下，反向传播中任何没有确定性实现的 CUDA 算子（例如部分 SDPA 后端）都会直接报 RuntimeError。
- 这一点，以及 R1/R2 这类问题、16k 全参显存、vLLM 0.11 编译配置等，**在本地 mock 测试中都无法暴露**。
- A2-lite 还需要真实的单次 update 和单批评测计时；目前 A/D 没有任何实测代理，Codex 也明确说明 C1 的自校准例外不适用于 A/D。
- **建议**：负责人批准一次有界的 **GPU 预检** 付费例外：
  - 每个臂只跑 2 次 update，用最长的几条序列，包含全参保存和 mmap 校验；
  - 导出后加载 vLLM，生成几条短请求；
  - 不产生任何科学结果，费用上限约 $5，从 A 类中支出；
  - 产出的实测计时同时作为 A2-lite 的依据。
- **替代方案**：不做预检，直接冒烟。代价是任何一个基础错误都会永久消耗一个冒烟臂，三个臂都可能失败。

---

## 已核对且没有问题的部分（摘要）

- **LR**：warmup = ⌈5% U⌉ = 33（U=654），之后余弦退火到 10% 峰值；LoRA 1e-4，全参 1e-5 ✓
- **优化器**：AdamW(0.9, 0.999, eps 1e-8, wd 0)，clip 1.0 ✓
- **精度与批次**：FP32 主参数 + BF16 autocast；每个 micro-batch 是一条完整序列，不 padding；按整个 update 的监督 token 数归一化 ✓
- **LoRA**：r64 / α128 / dropout 0，覆盖 7 个线性层；梯度检查点为 non-reentrant ✓
- **全参**：所有参数都可训练 ✓
- **导出**：LoRA 在 FP32 下 `merge_and_unload(safe_merge)` 后转 BF16；全参直接转 BF16 并保存 tokenizer ✓
- **训练子进程**：spawn 方式启动；退出并 join 之后，父进程才构建 vLLM ✓
- **评测请求**：
  - 使用原生 chat template（默认 system），只允许 NFC，并做往返校验；
  - 每题请求数：MATH500 为 4 次采样 + 1 次 greedy，其余为 8 次采样，合计 3,300 ✓
  - context = 最长 prompt + 16,384 ≤ 32,768 ✓
- **采样参数**：T=0.6 / top-p 0.95 / seed 0–3，greedy 为 T=0；停止 token 为模型的 EOS [151645, 151643] ✓
- **答案区域**：取最后一个 `</think>` 之后的文本，没有就用全文；截断的回答一律判错 ✓
- **配对 bootstrap**：10,000 次，seed 20261021，线性分位数 ✓
- **tokenizer**：1.5B 与 3B Instruct 的 tokenizer.json、vocab、merges、tokenizer_config 的 sha 完全相同 ✓
- **remote_path 追踪**：
  - 上传：`long_inputs_r1/<cell>`，worker 从 `INPUTS/<input_directory>` 读取；模型资产从 `local_path` 传到 `remote_path`；
  - 输出：`long_runs_r1/<logical>/evidence.tar`，collect 读取同一路径；
  - dispatch 目录名等于 job_id，即 `logical(job)`。

  三处都一致 ✓
- **共享账本**：与 C1 共用 `.local/p011_20261020/r1/dispatch` 和 4 槽并发上限 ✓
- **本地审计**：用 mmap 加载 state，本地不会出现 R2 的问题 ✓

## 其他注意

1. **本地存储**：全参 job 的 evidence.tar 约 22 GB，3B LoRA 约 7 GB，collect 会全量下载到本地。请在 A2-lite 中给出本地磁盘的余量。
2. **预算口径**：我在 C1 A2-lite（20261021j）中接受了"228 − 158.17"这个保守口径，但只限 C1。如果 A/D 沿用这个口径，可用额度只剩约 21.7，A 网格将无法准入。A/D 的预算口径需要负责人另行确认。
3. **训练吞吐量也没有实测**：我粗估一个 A 格（约 4,200 万监督 token，序列约 10k）在 1.5B LoRA 下约 1.5 小时，3B 约 3 小时。这只是推断，必须由 R4 的实测来确定。
