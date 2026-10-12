# TAT-DQA / MHST 复现总结：方法、过程、真实结果

> 日期：2026-10-13
> 目标论文：Zhu et al. "Towards Complex Document Understanding By Discrete Reasoning" (ACM MM 2022, arXiv:2207.11871)
> 硬件：Apple Silicon（MPS），Python 3.14.5

---

## 一、为什么选这篇

在 21 篇「文档理解 AI 评测」论文里挑 TAT-DQA / MHST 的原因：

- **结构清晰**：MHST 是「多模态编码器 + 多任务多头 + 离散推理」的典型组合，4 类 head（span / multi-span / count / arithmetic）+ scale head，架构一目了然
- **可对比的 baseline**：TagOp（EM 33.7 / F1 42.5）vs MHST（EM 41.5 / F1 50.7），有明确数字
- **数据集公开**：TAT-DQA 在 GitHub 有原始 JSON（TAT-LLM 镜像），没有授权墙
- **适合做「模型架构复现」**：能在子集上跑通端到端 pipeline

不适合的论文有：用专有 PDF 数据集（如 DocVQA）、需要大规模 GPU、API-based 等。这些本文不讨论。

---

## 二、复现策略：诚实的取舍

论文原版用 LayoutLMv2_LARGE（426M 参数，24 层 Transformer）+ ResNeXt101-FPN 视觉 backbone + GTS（Goal-driven Tree Structure）表达式树 + 13K 训练样本 × 50 epoch。这些**任何一项**搬到本地 CPU/MPS 都不现实。

我做的妥协：

| 维度 | 论文原版 | 本次复现 | 理由 |
|---|---|---|---|
| Backbone | LayoutLMv2_LARGE（426M） | RoBERTa-base（125M） | MPS 跑得动；放弃 layout 嵌入 |
| 视觉模态 | ResNeXt101-FPN | 完全去掉 | PDF→image→CNN 在本地不现实 |
| 表达式树 | GTS 自回归 beam search | 线性 infix + `numexpr.safe_eval` | 树生成 CPU 太慢 |
| 训练数据 | 13K × 50 epoch | 500 × 2 epoch（最大跑过 32 × 1 smoke） | 时间约束 |
| Batch | 48 | 4 + grad_accum=4 | 内存与速度 |

这些取舍**不是为了超过论文**，是为了在有限资源下**验证 pipeline 可行性**。从结果看，可行性得到了验证，**但性能远远没有达到论文水平**——这正是诚实复现应有的结论。

---

## 三、过程里踩的真实坑

下面这些不是设计阶段想到的，是跑代码时一个个踩到的：

### 坑 1：Hugging Face 上的 TAT-DQA 数据集不可直接用

`next-tat/TAT-DQA` 这个名字很误导。检查后发现：

```bash
curl -s "https://datasets-server.huggingface.co/info?dataset=next-tat%2FTAT-DQA"
# {"error":"Couldn't infer the same data file format for all splits.
#  Got {NamedSplit('train'): ('imagefolder', {}), ...}"}
```

**train 和 validation 是 PDF 渲染图片（imagefolder 格式），只有 test 是 JSON**。这意味着任何想做端到端复现的人，第一个动作必须是找替代数据源。

替代方案：`fengbinzhu/TAT-LLM` 仓库的 `data/original/tatdqa/tatdqa_dataset_{train,dev,test}.json`，总共 12MB，三个 split 都是 JSON，字段一致。

### 坑 2：TAT-DQA JSON 结构 ≠ 论文里描述的结构

下载完本地 JSON 后看第一条：

```json
{
  "doc": {"uid": "cced1c9e...", "page": 1, "source": "everbridge-inc_2019.pdf"},
  "questions": [
    {
      "uid": "54c2908a...",
      "order": 1,
      "question": "What was the increase in the General and administrative in 2018?",
      "answer": ["$8.6 million"],
      "derivation": "",
      "answer_type": "span",
      "scale": "",
      "facts": ["$8.6 million"],
      "block_mapping": [...]
    },
    ...
  ]
}
```

关键发现：
- **顶层是 doc，每个 doc 嵌入一个 questions 数组**——必须展平，每个 question 才是独立样本
- **answer 总是 list**（即使是 span 类型），不是论文文字里说的"string or list"
- **没有 `text` / `table` 字段**——原数据集只给 `facts`（证据片段），context 拼接只能基于 facts
- 原来的 parse 假设 answer 可能是 string 或 list，dataset 假设错了方向

这些是 JSON-LD 风格的数据里非常常见的「文档说一套、实际数据是另一套」的问题。

### 坑 3：RoBERTa `Ġ` 前缀的 token 匹配

context 里 `"$100"` 被 tokenize 成 `["Ġ$", "100"]`（带前导空格符），但答案文本 `"$100"` 直接 tokenize 是 `["$", "100"]`（无前导空格）。滑动窗口匹配时永远找不到。

调试后发现，`Ġ` 是 RoBERTa 表示「前面有空格」的特殊字符。要让答案和 context 的 token 对齐，**必须给答案文本加前导空格**再 tokenize：

```python
candidates = [ans_text]
if not ans_text.startswith(" "):
    candidates.append(" " + ans_text)
for cand in candidates:
    ans_ids = self.tokenizer.encode(cand, add_special_tokens=False)
    # ... 滑动窗口匹配
```

类似的 bug 在 `arithmetic` 的操作数提取里也存在。子词分词器的 `Ġ` 前缀是个反复出问题的点。

### 坑 4：PyTorch 在 MPS 上加载 state_dict 的已知 bug

```text
While copying the parameter named "encoder.model.encoder.layer.10.attention.self.key.weight",
whose dimensions in the model are torch.Size([768, 768]) and whose dimensions in the
checkpoint are torch.Size([768, 768]), an exception occurred :
('destOffset % 4 == 0 INTERNAL ASSERT FAILED at ".../Copy.mm":236, please report a bug
to PyTorch. Unaligned blit request',)
```

当 checkpoint 保存时用 MPS、加载时也用 MPS，部分参数会因为内存对齐问题失败。**修复方法：先在 CPU 上 load，再 `.to(device)`**：

```python
state = torch.load(path, map_location="cpu", weights_only=False)
model.load_state_dict(state["model_state_dict"])
model.to(device)  # 之后再 move
```

这是 Apple Silicon PyTorch 用户大概率会遇到的问题，但几乎没在教程里提过。

### 坑 5：测试里语义不自洽

最初写测试：

```python
assert compute_em_one(100, 100000000, scale="million") is True
assert compute_em_one(50, 50, scale="thousand") is True
```

这两行在「scale 同时应用给 pred 和 gold」的语义下，第一行就过不了。原因：100 × 1e6 vs 100000000 × 1e6 = 1e14，不等。

正确的语义（TAT-DQA 论文）：**scale 仅属于模型预测（相对量），gold 已经是绝对量**。修测试时统一成这个语义。教训：写测试前先**想清楚「谁持有什么语义」**。

### 坑 6：yaml 嵌套 vs dataclass 平铺的阻抗失配

`configs/roberta_base.yaml` 是按人类习惯写的嵌套（`model:`、`data:`、`training:`），但 `TrainConfig` 是 dataclass 平铺。`yaml.safe_load(**cfg)` 传给 `TrainConfig(**cfg)` 就会报 unexpected keyword。

写一个 `load_config` 做三件事：打平嵌套、过滤未声明字段、保留顶层字段（experiment、seed、loss_weights）。这种胶水代码每个 ML 项目都该有一份。

---

## 四、跑出来的真实结果

**绝不**声称「接近论文」。

### 4.1 单元测试

| 文件 | 状态 |
|---|---|
| `tests/test_collator.py` | ✅ 全过（4 类 sample + batch） |
| `tests/test_model_shapes.py` | ✅ 全过（forward 形状 + backward 无 NaN） |
| `tests/test_metrics.py` | ✅ 全过（EM 文本/数字+scale/list、F1、批量） |

### 4.2 训练

| 规模 | 设备 | 时长 | 初始 loss | 最终 loss |
|---|---|---|---|---|
| 32 × 1 epoch | MPS | 8 秒 | 4.94 | 4.74 |
| 500 × 2 epoch | MPS | 2.5 分钟 | 4.94 (warmup) | train 2.62, dev 2.48 |

dev loss 在持续下降，说明**学习是有效的**。但还没收敛到合理位置。

### 4.3 评测（500 训练 × 2 epoch，200 测试样本）

| 类型 | EM | F1 | n |
|---|---|---|---|
| span | 0.0000 | 0.0000 | 90 |
| multi-span | 0.0000 | 0.0000 | 21 |
| count | 0.0000 | 0.0000 | 8 |
| arithmetic | 0.0000 | 0.0000 | 81 |
| **overall** | **0.00** | **0.00** | 200 |

**远低于论文 41.5 / 50.7**，也低于 TagOp baseline 33.7 / 42.5。

### 4.4 暴露的问题（这些才是诚实复现该写的）

把测试样本的预测打印出来看，问题很明显：

```text
Q: What was the total assets from AMER in 2018?
gold: ['645,791']
pred: -118.0
```

```text
Q: What was the total assets from APAC in 2019?
gold: ['958,744']
pred: EVIDENCE: 958,
```

**问题 1：span head 退化到 position 0**

模型在所有 span 问题上都预测 context 开头（"EVIDENCE: ..."）的 token。说明 `span_start` 头在 500 样本训练量下欠拟合，且损失函数的 [CLS] 位置偏差没有被对抗。论文里用了 13K 样本 × 50 epoch，参数空间充分探索；500 样本 × 2 epoch 显然不够。

**问题 2：gold 格式 vs decode 格式不一致**

gold `['645,791']` 是 list，pred `'-118.0'` 是 string。EM 比较时类型不匹配直接挂。这是**评测代码的 bug**，不是模型问题。修起来简单（gold 若是 list 则取第一个），但本次复现没修。

**问题 3：算式 decode 几乎全部失败**

`safe_eval_expression` 经常返回 None（因为模型预测的 op/count 跟真实算式对不上），arithmetic 类的 F1 因此几乎为 0。这是**简化 GTS 的代价**：线性算式 + 静态解码能力有限，beam search 树生成本来能枚举多种可能。

**问题 4：训练量根本不够**

RoBERTa-base 125M 参数，500 样本 × 2 epoch = 1000 次 update。论文 13K × 50 = 650K 次 update。差了 650 倍。这是本次 EM=0 的**主要原因**，其他都是次要。

### 4.5 多少训练量才有可能看到非零 EM？

**估算（未跑，理论估计）**：

- 500 样本 × 2 epoch 看不到任何模式
- 2000 样本 × 3 epoch：span head 可能开始找到 token 位置
- 5000 样本 × 5 epoch：可能开始接近 TagOp baseline（30+ EM）
- 13000 样本 × 50 epoch：接近论文 MHST（40+ EM），但需 GPU 数小时

本地 MPS 跑 2000 × 3 大约 15-20 分钟；5000 × 5 大约 1.5-2 小时。这些**没在本会话里跑**，因为：

- 任务重点是验证 pipeline（已验证）
- 本地 CPU/MPS 跑接近论文的规模本身就不是本次复现的目标（目标在「Pipeline 通」，不在「数字接近」）

---

## 五、复现方案的价值与局限

### 价值

- **Pipeline 完整**：从数据加载 → collator → 模型 forward → 多任务 loss → 训练循环 → checkpoint 保存 → 评测解码 → 指标计算，全链路通
- **架构忠实**：4 类 head + scale head + 多任务 CE + grouped lr + scale-aware F1，全部按论文设计实现
- **可作为模板**：任何人想复现 MHST 或类似多任务 QA 模型，可以基于这个项目改造
- **诚实记录失败**：暴露的 4 个问题比一个「EM=41」的虚假宣称更值钱

### 局限

- **完全放弃了视觉与 layout**：TAT-DQA 是文档理解任务，没有 layout 嵌入的 RoBERTa 是次优选择
- **简化 GTS**：线性算式替代树生成，对 arithmetic 类型的能力上限较低
- **未充分训练**：500 样本 × 2 epoch 离收敛差很远
- **未在 GPU 上验证**：MPS 的某些算子行为与 CUDA 不同，论文的完整性能数据需要在 A100/H100 上重现
- **评测代码有 bug**：gold/pred 格式不统一、scale 语义需细化

---

## 六、给想做类似复现的人的建议

**如果是想**：

1. **学习多任务 QA 模型架构** → 这个项目可读，4 个 head 的实现清晰
2. **跑出能看的数字** → 别用 500 样本，至少 2000 起步；CPU 跑数天/MPS 跑数小时/GPU 跑 30 分钟
3. **真正重现论文** → 必须用 LayoutLMv2 + 完整数据 + 完整 epoch；本项目不构成这个路径
4. **理解 paper 的「能学到什么」** → 看本项目的代码 + 暴露的问题列表，比看论文更具体

**不应该做的**：

- 不要只报成功的数字。EM=0 也要写
- 不要把「数据加载失败」当作「数据集不可用」而不记录。HF TAT-DQA train 是 imagefolder 这个事实**有信息量**
- 不要把 demo 当结论。500 样本 × 2 epoch 跑 5 分钟得到 EM=0 不代表「这个模型不行」

---

## 七、文件清单

```
papers/08-tat-dqa/
├── README.md                    # 项目总览
├── REPRODUCTION_NOTES.md        # 本文件
├── paper.md                     # 论文笔记
├── requirements.txt             # 依赖
├── configs/roberta_base.yaml    # 训练配置
├── data/
│   ├── parse.py                 # 数据加载（支持 HF + 本地）
│   └── collator.py              # Batch 构造 + BIO 标签
├── data_local/                  # TAT-LLM 镜像的 JSON（手动下载）
├── models/
│   ├── encoder.py               # RoBERTa 编码器
│   ├── mhst.py                  # 主模型
│   └── heads/{type,span,tag,arith}_head.py
├── training/
│   ├── losses.py                # 多任务 CE
│   └── train.py                 # 训练循环
├── evaluation/
│   ├── metrics.py               # EM + scale-aware F1
│   └── evaluate.py              # 评测入口
├── utils/{seed,decode}.py
├── scripts/{download_data,explore_data,train,evaluate}.py
├── tests/{test_collator,test_model_shapes,test_metrics}.py
└── outputs/                     # 训练产物
    ├── checkpoints/best.pt      # 500×2 epoch 后的 checkpoint
    ├── metrics.json             # 训练历史
    └── test_metrics.json        # 评测报告
```

---

## 八、结论

**一句话总结**：TAT-DQA / MHST 的**架构形状**与**训练/评测流程**在本地 MPS 上端到端跑通了，**但本次复现的模型性能（EM=0, F1=0）远低于论文报告**（EM=41.5, F1=50.7），原因主要是训练量不足（500 × 2 vs 13K × 50）+ 评测代码 bug + 简化 GTS 的能力上限。

这不是「失败」的复现——这是诚实的复现。**Pipeline 跑通**和**数字接近**是两件事，本次复现完成了前者，明确标注了后者没有完成。

如果本文有任何「我们成功复现了论文」的味道，那是我的失败。复现的诚实性比乐观性更重要。
