# Tinker 当前账号可用模型与单价 · 2026-11-23

2026-11-23 09:22:54 PST（17:22:54 UTC），用 Tinker SDK 0.39.0 调用 `ServiceClient.get_server_capabilities()`，账号返回 **40 个模型 ID**，对应 **24 个不同的官方模型卡**。其中 **38 个支持训练和采样，2 个仅支持采样**。09:24 PST 读取 Tinker 的两份官方价目，40 个 ID 全部按完整名称匹配。此次盘点只读取元数据，付费调用为 0。

**按总参数量，最小的是 Qwen3.5-4B（40 亿）。** 标准 64K 版和 256K 版都可训练。账号清单中没有 Llama-3.2-1B、Llama-3.2-3B（含各自的 Instruct），也没有小于 4B 的 Qwen3.5 或其他模型。表中的 A3B 表示 MoE 每个 token 激活约 30 亿参数，例如 Qwen3.5-35B-A3B-Base 总计 350 亿参数。

## 完整价目

单位均为**美元 / 100 万 token**。采样时，生成 token 按“输出”计价，提示 token 按是否命中缓存取“输入”或“缓存输入”。训练栏的“仅采样”表示 API 返回 `trainable=false`。NVIDIA 条目使用查询当日官方公布的限时五折价。扩展上下文与仅采样版本均按各自完整 ID 单列。[官方价格与计费定义](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/)

| Tinker 模型 ID | 总参数（十亿） | 训练 | 采样输出 | 采样输入 | 缓存输入 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Qwen/Qwen3-8B` | 8.2 | 0.44 | 0.60 | 0.195 | 0.039 |
| `Qwen/Qwen3.5-35B-A3B-Base` | 35 | 1.177 | 1.335 | 0.54 | 0.108 |
| `Qwen/Qwen3.5-397B-A17B` | 397 | 6.60 | 7.50 | 1.65 | 0.33 |
| `Qwen/Qwen3.5-397B-A17B:peft:262144` | 397 | 12.00 | 7.50 | 1.65 | 0.33 |
| `Qwen/Qwen3.5-4B` | 4 | 0.737 | 1.005 | 0.33 | 0.066 |
| `Qwen/Qwen3.5-4B:peft:262144` | 4 | 1.34 | 1.005 | 0.33 | 0.066 |
| `Qwen/Qwen3.5-9B` | 9 | 1.463 | 0.807 | 0.30 | 0.06 |
| `Qwen/Qwen3.5-9B-Base` | 9 | 1.463 | 0.807 | 0.30 | 0.06 |
| `Qwen/Qwen3.6-35B-A3B` | 35 | 1.177 | 1.335 | 0.45 | 0.09 |
| `Qwen/Qwen3.6-35B-A3B:peft:262144` | 35 | 2.14 | 1.335 | 0.45 | 0.09 |
| `Qwen/Qwen3.8-27B` | 27 | 4.103 | 5.595 | 0.6975 | 0.1395 |
| `Qwen/Qwen3.8-27B:peft:262144` | 27 | 7.46 | 5.595 | 0.6975 | 0.1395 |
| `deepseek-ai/DeepSeek-V4.1-Flash-1017:peft:262144` | 552 | 4.98 | 3.60 | 0.60 | 0.12 |
| `deepseek-ai/DeepSeek-V4.1-Flash:peft:262144` | 552 | 4.98 | 3.60 | 0.60 | 0.12 |
| `moonshotai/Kimi-K2.6` | 1000 | 4.84 | 5.49 | 2.205 | 0.441 |
| `moonshotai/Kimi-K2.6:peft:131072` | 1000 | 15.40 | 5.49 | 2.205 | 0.441 |
| `moonshotai/Kimi-K3.1-Pro:peft:262144` | 2800 | 32.00 | 25.00 | 6.00 | 1.20 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | 120 | 1.276 | 1.44 | 0.57 | 0.114 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16:peft:262144` | 120 | 2.32 | 1.44 | 0.57 | 0.114 |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16` | 550 | 5.478 | 6.225 | 1.80 | 0.36 |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16:peft:262144` | 550 | 9.96 | 6.225 | 1.80 | 0.36 |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | 30 | 0.44 | 0.495 | 0.184 | 0.0368 |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16:peft:262144` | 30 | 0.80 | 0.495 | 0.184 | 0.0368 |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16` | 120 | 1.276 | 1.44 | 0.57 | 0.114 |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16:peft:262144` | 120 | 2.32 | 1.44 | 0.57 | 0.114 |
| `openai/gpt-oss-120b` | 117 | 0.737 | 0.84 | 0.33 | 0.066 |
| `openai/gpt-oss-120b:peft:131072` | 117 | 2.33 | 0.84 | 0.33 | 0.066 |
| `openai/gpt-oss-20b` | 21 | 0.396 | 0.45 | 0.18 | 0.036 |
| `thinkingmachines/Inkling` | 975 | 5.61 | 4.68 | 1.87 | 0.374 |
| `thinkingmachines/Inkling-2-Mini` | 26.4 | 0.75 | 0.50 | 0.15 | 0.015 |
| `thinkingmachines/Inkling-2-Mini:peft:262144` | 26.4 | 1.50 | 0.50 | 0.15 | 0.015 |
| `thinkingmachines/Inkling-2-Small` | 594 | 1.50 | 1.00 | 0.30 | 0.03 |
| `thinkingmachines/Inkling-2-Small:peft:262144` | 594 | 3.00 | 1.00 | 0.30 | 0.03 |
| `thinkingmachines/Inkling-Small` | 276 | 1.73 | 1.44 | 0.58 | 0.116 |
| `thinkingmachines/Inkling-Small:peft:262144` | 276 | 3.47 | 1.44 | 0.58 | 0.116 |
| `thinkingmachines/Inkling-Small:peft:262144:sampling-nvfp4` | 276 | 仅采样 | 1.20 | 0.30 | 0.06 |
| `thinkingmachines/Inkling:peft:262144` | 975 | 11.23 | 4.68 | 1.87 | 0.374 |
| `thinkingmachines/Inkling:peft:262144:sampling-nvfp4` | 975 | 仅采样 | 4.05 | 1.00 | 0.17 |
| `zai-org/GLM-5.3-Flash:peft:262144` | 320 | 5.58 | 2.11 | 0.84 | 0.168 |
| `zai-org/GLM-5.3:peft:262144` | 753 | 14.58 | 12.15 | 3.78 | 0.756 |

## 数据与来源

- [账号 API 响应](CAPABILITIES.json)保留原始顺序、训练/采样可用标记和接口返回的上下文长度。
- [完整机器可读清单](MODELS_AND_PRICES.json)含调用时间、SDK 版本、各价格源的 SHA256、总参数量、激活参数量和逐 ID 单价。仅采样条目的训练价记为 `null`，其参数量按官方价目中的同一模型卡核对。
- 当日价目快照保留官方发布的原始字节。[训练与采样价目快照](sources/models.json) · [仅采样价目快照](sources/serverless.json) · [官方训练与采样价目](https://tinker-docs.thinkingmachines.ai/tinker/models.json) · [官方仅采样价目](https://tinker-docs.thinkingmachines.ai/tinker/serverless.json)
