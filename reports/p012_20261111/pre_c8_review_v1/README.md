# P012 F4/F5 与共享启动器：一次审查请求

依据 Claude `020017ae` 和负责人的指令，F4、F5 与 Modal 启动器在 C8 前一起送审。F1–F3 已执行。本包不请求逐格重复审查。

1. **F4**：OMI-2 必须使用导出的训练模板。缺失、空模板或 pre-rendered 绕过会拒绝。四个真实分词器各测0/4-shot，共8个用例，在固定训练环境与实际评测环境逐 token 一致。完整token、模板SHA和版本见两个`*_TEMPLATE_PARITY.json`。这是合成工程测试；C6正式4个示例仍需从题池外冻结。
2. **F5**：先严格数值比较，再 math-verify；逐条记录路径，同时报告两个准确率及差值。货币与数字文本包装可通过；`18 dollars`不合规；百分比按数学值判等。Li的G0判分语义不变。
3. **Modal**：`modal_g0.py`已用于G0；`modal_train.py`为待审候选，直接调用固定 LLaMA-Factory CLI。核对数据、行数、模型和代码SHA；保留输入、有效YAML、日志、检查点SHA。权重留在持久卷，完整独立备份完成前不删除。覆盖项只有容器路径、禁止覆盖输出，以及标准Trainer的`skip_memory_metrics=false`内存记录。无自定义训练循环或自动科学重试。统一用`modal run -m experiments.p012.<module>`。
4. **集中judge**：`judge_collection.py`为各格题号加命名空间，一次加载判分模型。评分器核对合并输入与每格原始prompt完全一致，再从同一份原始judge输出回填；不重写原始输出或伪造拆分manifest。测试覆盖跨格同题号、错误分组及prompt替换。实际32B judge尚未运行。

60个不重复的相关本地用例通过；记录见本目录和`../f4_f5_candidate_v1/`。训练环境构建、pip check、实际LF导入及两套环境的8个token用例通过。依赖修复仅把PyArrow26.0.1改为21.0.0，以兼容固定NumPy1.26.4。启动和导入失败记录保留。

请审查F4/F5、两个Modal共享路径、内存记录覆盖项和judge逐格追溯。训练、C8、正式4-shot基线均未启动。源文件SHA见`SOURCE_MANIFEST.json`，已完成G0结果及独立10%抽查入口见`G0_RESULT_INDEX.json`。MATH最终Li分数等待全部G0队列统一judge；当前exact分数不能用于判定复现门槛。

Built with Llama.
