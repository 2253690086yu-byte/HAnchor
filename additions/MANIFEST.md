# additions 清单

> 每份精选内容的来源、类型与**建议并入位置**(相对 `plugins-cache/`,版本目录 `<ver>` 以实际为准)。
> 基线 `plugins-cache/` 保持原样未动;并入动作做不做、何时做,由后续改造决定。

| # | 文件 | 类型 | 来源 | 建议并入位置 | 一句话价值 |
|---|---|---|---|---|---|
| 01 | `01-user-rules/meta-rules.md` | 规则层(新写) | 30 份 memory 提炼 | 新增顶层 `user-rules/`(体系目前没有用户级 scope) | 高于任何 skill 的元规则,SC-xx 同构编号 |
| 02 | `02-engineering/hard-contracts-verifier/` | 机制范本 | 2026-09-21 会话 | `fullstack-dev/references/` + `fullstack-dev/scripts/` | 三条硬约定 + verify.py 真编译真解析断言——"规则可执行化"最深样本 |
| 03 | `03-audio/MIMO_API.md` | Provider 参考 | 2026-09-17 会话 | `frontend-dev/references/`(与 minimax-\* 并列) | 实测口径的 API 协议:禁 system 角色、音色走 content 标签、DataURL 格式 |
| 04 | `03-audio/TTS标注脚本_河南话_标注员A.md` | 验收规范 | 2026-09-17 会话 | 新建 `skills/audio-review/references/` | 方言保字规则 + 变速后三道校验 + 正确率优先于碎片率 |
| 05 | `04-design/ad-platform-login-menu-spec.md` | 模板范本 | 2026-11-05 会话 | `ardot/skills/ardot-ui-design/references/` | 页面清单/字段规则/状态反馈三表 + 显式"不包含"声明——ardot 缺的交互逻辑维度 |
| 06 | `04-design/worker-ledger.html` | 设计样本 | 2026-09-17 会话 | Visualizer 色板体系的落地样本 | CSS 变量双主题 token 组织 |
| 07 | `05-golden-samples/`(1 份) | 回归样例 | 2026-10-23 tdoc 流水线产物 | `hanchor-docx/<ver>/tests/golden/` | stage2 design tokens(business-modern 主题)——排版主题的完整 token 定义 |
| 08 | `06-cross-harness/codex-glm5.3-setup.md` | 方法论参考 | 2026-09-24 会话 | 独立保留(跨 harness 类别) | 实测优先的跨 harness 接入纪律:版本实测、硬事实先行、profile 隔离 |
| 09 | `08-doc-skills/`(3 技能) | 技能组(1 自写 + 2 引入) | documentation 自写;technical-writing 引自 [luoling8192/technical-writing](https://github.com/luoling8192/technical-writing)@`5f684e95`(MIT);doc-coauthoring 引自 anthropics/skills@`ca45fc49`(Apache-2.0) | export/ 全渠道 + install_to_project(`--only` 按需) | 文档三层纪律:文风(禁词/句式)/结构(五类研发文档模板)/流程(访谈→逐节起草→测试)——基线按文体分专家,无此抽象层 |

## 选取标准

1. 机制层优先:可执行校验、实测协议、隔离实验 > 纯提示词规范
2. 唯一性:现有 1528 份规范中没有对应维度(音频验收、用户规则层、golden sample 均属空白)
3. 业务产物不入选,测试价值由 golden sample 覆盖
