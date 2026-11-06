# 08-doc-skills — 文档专用三技能

文档写作按三层拆开,各管一层,可单独装也可组合:

| 技能 | 层 | 管什么 | 来源 |
|---|---|---|---|
| technical-writing | 文风层 | 每句话怎么写:禁词表、句式、中文行文规范 | 引入:[luoling8192/technical-writing](https://github.com/luoling8192/technical-writing) @ `5f684e95`(MIT) |
| documentation | 结构层 | 文档长什么样:五类研发文档的章节模板(设计文档/ADR/PRD/RFC/操作指南) | 自写(自有内容) |
| doc-coauthoring | 流程层 | 怎么一起写:访谈 → 逐节起草 → 读者测试 | 引入:[anthropics/skills](https://github.com/anthropics/skills) @ `ca45fc49`(Apache-2.0) |

## 引入口径

- 两个引入技能的 SKILL.md 为上游**逐字节拷贝**,零改动;来源以 commit 锚定,上游更新时重拉替换
- 许可为仓库级:luoling8192/technical-writing 为 MIT,anthropics/skills 非 docx/pdf/pptx/xlsx 的技能为 Apache-2.0(见其 README 与 THIRD_PARTY_NOTICES)
- 按根 README 公开仓口径:**引入内容不入公开仓**;documentation 为自有内容,可发布

## 安装到具体项目

```bash
# 一条命令装三件(推荐;本仓缺的技能会按下方登记的上游锚点自动拉取并校验 SHA-256)
python tools/install_doc_skills.py <目标项目> [--harness zcode,claude,cursor,codex]

# 等价的白名单写法(完整工作仓内,三个技能都在本地时)
python tools/install_to_project.py <目标项目> --only technical-writing,documentation,doc-coauthoring

# 卸载(零残留,两种方式共用同一安装清单)
python tools/install_to_project.py <目标项目> --uninstall
```

`install_doc_skills.py` 在公开仓也能跑:documentation 用本仓的,technical-writing / doc-coauthoring
按锚点从上游拉取;需要 git 和网络,拉取后哈希不符会拒绝安装(上游被改写时更新脚本内登记即可)。
在完整工作仓里运行则三个全走本地,不访问网络。

## 与基线的关系

基线 `hanchor-docx` 的 9 个写作专家按文体分(公文/合同/研报/博客…),管的是"内容怎么写好";
本组按抽象层次分(文风/结构/流程),管的是"任何文档通用的三层纪律",两者正交。
基线 experts 的禁词/反模式素材(business-copy、tech-blog、legal-contract)可作未来自有扩展
technical-writing 本地层的素材,当前未动。
