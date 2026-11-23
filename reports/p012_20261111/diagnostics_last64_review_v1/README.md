# 最后 64 步训练损失均值的脚本差异，待运行前审查

审查对象是 [相对 39cd2394 已接受代码的差异](PROPOSED_DIFF.patch) 和 [完整候选源码](candidate/build_table.py)。原表的 113 行已全部独立复现。

候选脚本沿用原来的 loss 日志与训练步数校验。设最后一步为 T，取 T−63 至 T 的 64 个 loss 值等权平均，JSON 保留完整精度，表格显示六位小数。Modal 读取 Trainer 每步记录的 loss，Tinker 读取 train_loss.jsonl 的 loss。已有清单的更新步数范围是 128 到 8,192。

请核对窗口边界、权重和输出列。已用 git apply --check 核对差异可应用。候选脚本尚未执行。审查通过后在新目录生成扩展表，核对原 113 行所有旧字段，并附已接受的七行首个 boxed 诊断。
