# Document Understanding Dataset and Evaluation (DUDE)

## 基本信息

- **论文标题**：Document Understanding Dataset and Evaluation (DUDE)
- **作者**：Jordy Van Landeghem, Rubén Tito, Łukasz Borchmann, Michał Pietruszka, Paweł Józiak, Rafał Powalski, Dawid Jurkiewicz, Mickaël Coustaty, Bertrand Ackaert, Ernest Valveny, Matthew Blaschko, Sien Moens, Tomasz Stanisławek
- **发表年份**：2023
- **venue**：ICCV 2023
- **DOI**：10.1109/iccv51070.2023.01789
- **arXiv**：2305.08455
- **提交日期**：2023-05-15（修订 2023-09-11）
- **分类**：cs.CV, cs.CL, cs.LG
- **原文链接**：https://openaccess.thecvf.com/content/ICCV2023/html/Van_Landeghem_Document_Understanding_Dataset_and_Evaluation_DUDE_ICCV_2023_paper.html
- **License**：CC BY 4.0

## 核心价值

首个把「多页 + 多行业 + 多任务 + 不可答」打包的通用文档理解基准，直接模拟真实文档流。

## 关键贡献

- 41,000+ QA / 5,000 文档，均 5.72 页
- 跨 1860–2022 与 200+ 文档类型、15+ 行业
- 答案含抽取式、生成式、列表式、不可答四类
- 首创 layout-navigating 问题与多 OCR 版本（Tesseract/Azure/AWS）配套

## 摘要

We call on the Document AI (DocAI) community to reevaluate current methodologies and embrace the challenge of creating more practically-oriented benchmarks. Document Understanding Dataset and Evaluation (DUDE) seeks to remediate the halted research progress in understanding visually-rich documents (VRDs).

### 关键特点

- 新型 benchmark，含新颖问题类型、答案与版式
- 多行业、多领域、多页可视化富文档，来源与年代多样
- 多任务、多领域评测设置，模拟真实泛化与低资源适配需求
- 强调语言、图像、版式高效融合

## 价值指标（规模 / 成绩 / 指标）

- 人类专家 **ANLS 74.76**
- 最佳 T5-2D (large) 微调后 **46.06**
- 文本-only LLM 35–47
- 视觉理解题落后人类约 25 分

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：通用文档理解基准、多行业文档评测