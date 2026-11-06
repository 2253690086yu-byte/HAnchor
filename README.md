# HAnchor — 自有 agent 规范体系:提炼层 + 多 harness 接入工具

> 命名:harness(攀岩安全带,agent 编排层)配套的 anchor(保护锚点,静态基准层)。
> 本仓是 HAnchor 体系的**公开部分**;234M 规范基线缓存为本地私有工作仓,不随本仓分发。

## 仓库内容

```
├── additions/         提炼层(9 项,含 MANIFEST 登记来源与去向)
│   ├── 01-user-rules/         用户级元规则 UR-01~08(实测提炼,高于任何单技能)
│   ├── 02-engineering/        硬约定×可执行校验范本(verify.py)
│   ├── 03-audio/              MiMo TTS 实测协议 + 方言标注验收方法论
│   ├── 04-design/             UI 交互 spec 模板 + design token 真实样本
│   ├── 05-golden-samples/     排版主题 design token 样本(business-modern)
│   ├── 06-cross-harness/      跨 harness 接入实测方法论(codex + GLM)
│   └── 08-doc-skills/         文档三技能:文风/结构/流程(公开部分仅自写的 documentation 五类研发文档模板;另两个技能按组 README 登记的上游来源安装)
└── tools/             harness 接入工具
    ├── export_for_harness.py  技能导出桥:版本剪裁 + 可移植性分类 + skills/codex/cursor/zcode-plugin 四种目标格式
    ├── install_to_project.py  项目级一键装/卸:ha- 前缀防遮蔽、清单化零残留、AGENTS.md 标记块
    └── install_doc_skills.py  文档三技能一条装齐:本仓缺的按 MANIFEST 上游锚点拉取并校验哈希
```

> `install_to_project.py` 全量安装需要本地完整工作仓(含基线 `plugins-cache/`)作数据源:
> `export HANCHOR_ROOT=/path/to/完整工作仓` 后即可在本仓直接运行。
> `install_doc_skills.py` 无此依赖,本仓克隆下来即可用(见「如何安装到指定项目」末尾)。

## UR-xx 用户级元规则(节选)

- **UR-01** “不支持”的结论门槛必须高于“支持”——判断能力边界前穷举参数空间
- **UR-02** API 结论以实测为准,不以文档为准;未实测显式标注“未知”
- **UR-03** 性能判断以计数器为准,不按经验百分比
- **UR-05** 跨窗口可复用的知识必须落成 skill,不落目录级文档
- **UR-06** 待办清单追加式维护,不重排历史

完整 8 条见 `additions/01-user-rules/meta-rules.md`,每条附来源与被推翻链路。

## 如何安装到指定项目(以 ZCode 为例)

### 前提

技能数据源是本地完整工作仓(含 234M→39M 规范基线 `plugins-cache/`,因版权边界**不在本仓**)。
在本机把它指向环境变量(Windows PowerShell 示例):

```powershell
setx HANCHOR_ROOT "C:\Users\你的用户名\HAnchor"   # 指向你本地的完整工作仓
```

### 一键安装(只动目标项目,不碰 harness 全局)

```bash
python tools/install_to_project.py "C:\path\to\你的项目" --harness zcode
```

装完后目标项目里出现:

```
你的项目/
├── .zcode/skills/ha-<技能名>/SKILL.md   # 全部带 ha- 前缀,不遮蔽 ZCode 原生/插件技能
│   ├── references/  scripts/  assets/   # 逐字节无损的技能载荷
│   └── ...
└── AGENTS.md                             # 追加 UR-xx 元规则块(带 <!-- hanchor:begin/end --> 标记)
```

在 ZCode 中**打开该项目并新开会话**,技能即被自动发现,按 description 触发(或直接点名 `ha-xxx`)。

### 常用变体

```bash
python tools/install_to_project.py --list      # 先查可装技能与描述(配 HANCHOR_ROOT 后为全量基线)
--only html-review                             # 只装指定技能,名字从 --list 挑(基线技能需已配 HANCHOR_ROOT)
--group writing                                # 按分组装;组键见 --list(本仓自带 writing=文档三件套)
--no-rules                                     # 不往 AGENTS.md 写元规则
--status                                       # 查看该项目装了什么
--harness zcode,claude,cursor,codex            # 同时喂多个 harness(各自目录约定)
```

重复安装不同技能集时安装清单自动合并,`--uninstall` 永远按清单整批清除。

### 文档三技能(文风/结构/流程)一条装齐

```bash
python tools/install_doc_skills.py "C:\path\to\你的项目"
```

documentation 用本仓自带;technical-writing、doc-coauthoring 按登记的上游 commit 锚点拉取并校验
SHA-256 后统一安装(同样 ha- 前缀 + 清单化)。只需 git 和网络,无需本地完整工作仓。

### 随时干净卸载

```bash
python tools/install_to_project.py "C:\path\to\你的项目" --uninstall
```

按安装清单(`.zcode/hanchor-install.json`)精确移除:技能目录全删、AGENTS.md 只摘标记块 —— **零残留**。

设计要点:只写目标项目目录、`ha-` 前缀保证不遮蔽宿主原生技能、安装写清单
(`.zcode/hanchor-install.json`)、卸载按清单精确清除零残留、技能载荷逐字节无损。

## 维护约定

- 提炼层新增内容走 MANIFEST 登记,编号体系(UR-xx / SC-xx 同构)必附来源
- 工具改动在完整工作仓中进行,公开仓随发布同步
