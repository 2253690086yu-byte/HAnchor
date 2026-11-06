---
name: documentation
description: 研发文档的结构模板。当用户要写技术设计文档、决策记录(ADR)、PRD、RFC/提案、操作指南(howto),或问"文档怎么组织/分几节/搭个框架/给个模板/列个大纲"时使用。管结构层——文档长什么样;每句话怎么写由 technical-writing 技能管;访谈式共创流程由 doc-coauthoring 技能管。
---

# 研发文档结构模板

## 职责边界

- 本技能只管**结构**:分几节、每节放什么、顺序如何
- 文风(禁词/句式/中文行文)→ technical-writing 技能
- 访谈 → 逐节起草 → 读者测试的共创流程 → doc-coauthoring 技能
- 办公类文档(公文/合同/研报/纪要/总结)不在本技能范围,走对应垂类模板

## 路由表

| 识别信号 | 文档类型 | 模板 | 一句话定位 |
|---|---|---|---|
| "技术方案 / 怎么实现 / 架构设计" | 技术设计文档 | references/design-doc.md | 把一个方案讲到能被评审挑出毛病 |
| "决策记录 / ADR / 为什么选 X 不选 Y" | 决策记录 | references/decision-doc.md | 把一个决定及其来路存档备查 |
| "需求文档 / PRD / 要做什么" | 产品需求文档 | references/prd.md | 把产品变化定义到不需要口头补充 |
| "提案 / RFC / 要不要做 / 征求意见" | 提案 | references/rfc.md | 把一个变更提议推向共识 |
| "指南 / 怎么操作 / 步骤 / 上手" | 操作指南 | references/howto.md | 让读者照着做就能完成 |

类型拿不准时,按读者拿文档做什么判断:拍板实现 → design-doc;存档决定 → decision-doc;达成共识 → rfc;排期验收 → prd;照做完成 → howto。

## 用法

1. 按路由表 Read 对应 references/ 模板
2. 复制骨架到目标文档,按各节"写什么/不写什么"填充
3. 章节可按篇幅裁剪,但模板标注的**必留节**不能删
4. 成文后过一遍 technical-writing 技能的 Editing Checklist

## 三层组合

- 与 doc-coauthoring 同用:访谈阶段先按路由表定类型 → 骨架取本技能模板 → 逐节起草时文风遵 technical-writing
- 多份文档互链:RFC 达成共识后落 design-doc;design 中关键取舍单独抽成 decision-doc 存档
