# Codex + GLM-5.3：推荐方案

> 基于本机实测诊断，2026-09-24。**已按 CLI profile 隔离方式设计，桌面版零影响。**

---

## 结论先行

**不要改顶层 provider。用 profile 隔离，桌面版保持 GPT，CLI 另开一档跑 GLM。**

```
codex              → GPT（桌面版同日用同一份基础配置，能力全保留）
codex -p glm       → GLM-5.3
```

---

## 为什么必须隔离——两条硬事实

### 事实 1：桌面版没有多模型切换能力

Codex 桌面版的模型选择器：

- 从 OpenAI 账号目录远程拉取（缓存在 `~/.codex/models_cache.json`）
- 外加**唯一一个 Custom 入口**，内容就是顶层 `model`
- **它不读 `model_catalog_json`**

本机 `models_cache.json` 不存在，且 `config.toml` 顶层没有 `model` / `model_provider`，说明现在是纯 OpenAI 默认态。

后果：桌面版想换模型只能**改顶层 + 重启**。没有 profile 那种"一个开关切一档"的机制。

### 事实 2：你桌面版启用了这些插件

```
unified-computer-use@openai-bundled    ← 看屏幕、操作电脑
browser@openai-bundled                 ← 浏览器操作
```

外加 `openai-primary-runtime` 的办公文档插件（documents / pdf / spreadsheets / presentations / template-creator）。

这些依赖 OpenAI 自家的 CUA 运行时（`@oai/sky`、`codex-computer-use.exe`、`cua_node`），并且**要模型能理解视觉画面**。而 GLM-5.3 在官方元数据里写死了：

```json
"input_modalities": ["text"]
```

**所以把顶层 provider 改成 ZAI，等于当场废掉你桌面版一半的能力，而且没有方便的开关切回来。**

---

## 本机现状（实测）

| 项目 | 值 |
|---|---|
| 桌面版版本 | 26.831.20005 |
| **CLI 版本** | **0.152.0** ✅ 远高于 profile v2 分界（0.134） |
| CLI 路径 | `C:\Users\harley\AppData\Local\OpenAI\Codex\bin\7537f22ba194f7c1\codex.exe` |
| `codex` 命令 | 不在 PATH，需全路径或加 PATH |
| `--profile` 支持 | ✅ 已实测确认：`-p, --profile <CONFIG_PROFILE_V2>` → `Layer $CODEX_HOME/<name>.config.toml on top of the base user config` |
| `~/.codex/models.json` | 不存在，需新建 |
| `~/.codex/*.config.toml` | 无任何 profile 文件 |
| `[model_providers.*]` | 无 |

---

## 配置

### 步骤 1：新建 `C:\Users\harley\.codex\models.json`

```json
{
  "models": [
    {
      "slug": "glm-5.3",
      "display_name": "glm-5.3",
      "description": "Z.ai's latest flagship model",
      "default_reasoning_level": "max",
      "supported_reasoning_levels": [
        { "effort": "low", "description": "Light reasoning" },
        { "effort": "high", "description": "Enhanced reasoning" },
        { "effort": "max", "description": "Deep reasoning" }
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 0,
      "base_instructions": "",
      "supports_reasoning_summaries": true,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "apply_patch_tool_type": "freeform",
      "truncation_policy": { "mode": "bytes", "limit": 50000 },
      "context_window": 1048576,
      "max_context_window": 1048576,
      "effective_context_window_percent": 95,
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": [],
      "input_modalities": ["text"]
    },
    {
      "slug": "glm-5-turbo",
      "display_name": "glm-5-turbo",
      "description": "Agent-optimized model",
      "default_reasoning_level": "max",
      "supported_reasoning_levels": [],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 1,
      "base_instructions": "",
      "supports_reasoning_summaries": true,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "apply_patch_tool_type": "freeform",
      "truncation_policy": { "mode": "bytes", "limit": 50000 },
      "context_window": 204800,
      "max_context_window": 204800,
      "effective_context_window_percent": 95,
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": [],
      "input_modalities": ["text"]
    }
  ]
}
```

两点改动说明：

- `truncation_policy.limit` 从官方默认的 `10000` 提到 `50000`。官方值会在跑测试、看长日志、读大 diff 时按字节砍掉信息。
- `glm-5-turbo` 的请求会被自动路由到 `glm-5.3-flash`。

### 步骤 2：改 `C:\Users\harley\.codex\config.toml`

**只加一个 provider 块，不改顶层任何键。**

在文件末尾追加：

```toml
[model_providers.ZAI]
name = "ZAI"
base_url = "https://api.z.ai/api/v1"
env_key = "ZAI_API_KEY"
requires_openai_auth = true
wire_api = "responses"
```

> 国内网络把 `base_url` 换成 `https://open.bigmodel.cn/api/v1`。
>
> 这个块只是**定义**，顶层没有 `model_provider = "ZAI"` 指向它，所以桌面版和默认 CLI 完全不受影响。

### 步骤 3：新建 `C:\Users\harley\.codex\glm.config.toml`

profile 是独立文件，**顶层键**，叠加在基础配置之上：

```toml
model = "glm-5.3"
model_provider = "ZAI"
model_reasoning_effort = "max"
model_catalog_json = "~/.codex/models.json"
model_context_window = 1000000
```

如果需要保险丝，再加两行：

```toml
max_turns = 30
approval_policy = "on-request"
```

> `max_turns` 防的是第三方模型偶发陷入工具调用循环。

### 步骤 4：设 API Key（不要写进 config.toml）

```powershell
[Environment]::SetEnvironmentVariable("ZAI_API_KEY", "<你的 Coding Plan Key>", "User")
```

注意两个坑：

1. 写注册表后**已运行的进程读不到**（进程环境块是启动快照）——必须新开终端才生效
2. Codex 桌面版是 GUI 进程，**同样不继承新设的环境变量**。但本方案里桌面版不读这个 key，所以无影响；只有 CLI 需要，而 CLI 从终端继承

### 步骤 5：让 `codex` 命令可用

bundle 的 CLI 路径带 hash（`bin\7537f22ba194f7c1\`），升级后会变。加到 PowerShell profile 里动态解析：

放到 `$PROFILE` 里：

```powershell
function codex {
    $bin = Get-ChildItem "$env:LOCALAPPDATA\OpenAI\Codex\bin" -Directory -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $bin) { Write-Error "Codex CLI not found"; return }
    & (Join-Path $bin.FullName "codex.exe") @args
}
```

### 步骤 6：验证

```powershell
codex --version                  # 应输出 codex-cli 0.152.0
codex doctor --summary --ascii   # 诊断安装 / config / auth / runtime
codex -p glm "reply with OK only, do not use tools"
```

确认工具调用正常后再放写权限：

```powershell
codex -p glm "run pwd via the shell tool, then print the exact path"
```

---

## 两条路径怎么分工

| 任务类型 | 走哪条 | 原因 |
|---|---|---|
| computer use / 浏览器操作 | **GPT** | GLM 是 text-only，看不了屏幕 |
| 截图 / vision 输入 | **GPT** | 塞给 GLM 会先绕道 OpenAI 识别（见坑 2） |
| 办公文档（docx / pdf / xlsx / pptx） | **GPT** | 插件绑 OpenAI 运行时 |
| 模糊调试、架构决策 | **GPT** | GLM 在"执行到底"类任务上落后 22 点 |
| 认证 / 计费 / 破坏性改动 | **GPT** | 风险不该省钱 |
| 有界重构、补单测 | **GLM** | 验收标准明确，跑错能立刻发现 |
| 批量小改、代码审计 | **GLM** | 量大、单次风险低 |
| 跑测试修 bug | **GLM** | 有测试做验收信号 |
| 大仓库全量读码 | **GLM** | 原生 1M 上下文 |
| 日志 / 配置类粗活 | **GLM** | 不需要强推理 |

---

## 六个坑

### 坑 1：推理档位静默降级 ★最危险

GLM 官方只声明 **low / high / max**，Codex 客户端档位体系是 `minimal/low/medium/high/xhigh(/ultra)`。对不齐时 UI 会显示中间值。

已有人实测：`config.toml` 写 `max`，桌面端显示**「中」**——因为 `[desktop] enabled-reasoning-efforts` 里没有 `max`。**你以为在跑满血，实际跑低档，而且不报错。**

本方案走 CLI profile，比桌面版 UI 路径可控，但仍要验证实际生效值。

自证方法（不靠主观感受）：

```python
import sqlite3, os, pathlib
db = pathlib.Path(os.path.expanduser('~/.codex/logs_2.sqlite'))
con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
for r in con.execute("""
    select datetime(ts,'unixepoch','localtime'), substr(feedback_log_body,1,300)
    from logs where feedback_log_body like '%codex.turn.reasoning_effort=%'
    order by id desc limit 3"""):
    print(r[0], '|', r[1])
```

跑完第一次 GLM 任务后再查，能看到实际值。本机目前无此类记录（还没跑过带 provider 的会话）。

### 坑 2：web search 和 vision 绕道 OpenAI ★合规相关

Codex 给模型的 `web_search(query)` 工具，**实际由你 ChatGPT 登录态的 GPT-5.6-Luna 执行搜索**。

vision 同理：GLM 是 text-only，你往 prompt 塞图片，**图片会先送到 OpenAI 服务器识别**，再用文字描述替换掉原本的图片位置。

**「Codex 外壳 + GLM 模型」≠「数据只到智谱」。** 评估合规边界时这条必须算。

### 坑 3：不要用中间层 shim

社区方案 `codex-glm` / CCX / cc-switch 这类协议转换层，**默认把 GLM 的 thinking 关掉**（`ZHIPU_THINKING=disabled` 写死在默认值），且只验证到 `glm-5.2`。

GLM-5.3 的能力增量主要来自后训练 scaling + 长思考轨迹。关掉 thinking 等于拿到残废模型，然后你会得出"GLM 不行"的错误结论。

官方已有原生 Responses 端点，不需要任何 shim。

### 坑 4：端点必须用 Responses 专用地址

| 工具 | 端点 | 协议 |
|---|---|---|
| **Codex** | `https://api.z.ai/api/v1` | OpenAI **Responses** |
| Claude Code / Goose | Anthropic 兼容地址 | Messages |
| 其他 OpenAI 兼容工具 | `https://api.z.ai/api/coding/paas/v4` | chat/completions |

配 `/api/coding/paas/v4` 会直接失败。`wire_api` 必须写 `"responses"`——Codex 已经移除了 Chat Completions 支持。

### 坑 5：profile 文件不能写 `[profiles.x]` 表

Codex 0.134+ **拒绝**在 `config.toml` 里写 `[profiles.name]` 嵌套表，会报错。profile 必须是独立文件 `~/.codex/<name>.config.toml`，内容是顶层键。

`[model_providers.x]` 块则**留在主 config.toml**，不能放进 profile 文件。

### 坑 6：token 消耗是两支相乘

GLM-5.3-Flash 积分倍率：**input 2.3 / cached input 0.56 / output 8**。

关键在 output 倍率 8。而 Codex 的 agent loop 本身话多——OpenAI 官方做过实验，GPT-5.3-Codex 连跑 25 小时烧掉 13M tokens。

**Codex 外壳的长上下文倾向 × GLM 的 thinking token 消耗 = 消耗速度可能快于 ZCode + GLM。**

这是推断，不是实测。验证方法：跑同一批任务对比积分消耗。

---

## 什么情况下我改推别的

### ~~改推「自部署 GLM 权重」~~ —— 此项已撤回，见附录

> **勘误（2026-09-24）**：本节原建议"自部署 GLM 权重走本地 vLLM 解决数据不出本机"，
> 是在**没有核算硬件成本**的情况下给出的，属于错误建议。GLM-5.3 是 744B 总参与 / 40B 激活的
> MoE，FP8 权重大约 744GB，需要 8×H200 这一量级的硬件。真实成本见下方"附录：自部署的真实代价"。
>
> 结论：**"数据不出本机"与"使用 744B 前沿模型"在个人/小团队预算下是互斥的。**

---

## 附录：自部署的真实代价

### 硬件需求

GLM-5.3 沿用 GLM-5.2 底座：744B 总参数 / 40B 激活。官方部署指南给出的配置：

| 精度 | 显存需求 | 最低配置 |
|---|---|---|
| FP8 | ~744 GB 权重 + KV cache | **8×H200**（141GB × 8 = 1128GB） |
| INT4 | ~372 GB 权重 + KV cache | 4×H200（564GB），勉强 |

### 云租价格（2026-09 公开报价）

| 提供商 | 8×H200 节点 | 折合月成本（730h 全时） |
|---|---|---|
| Massed Compute（批发） | $22.64 / hr | $16,527 |
| DigitalOcean | $27.52 / hr | $20,475 |
| Hyperstack | $28.00 / hr | $20,440 |
| CoreWeave | $50.44 / hr | $36,821 |
| AWS / Azure / GCP | $7.91–13.78 每卡 / hr | $46,200 – $80,400 |

按**工作日每天 8 小时**（约 176 h/月）算下来最低也要 **$3,984/月**。

### 买断

| 项目 | 价格 |
|---|---|
| 单卡 H200 SXM | $31,000 – $40,000 |
| 8 卡 HGX H200 整机 | $350,000 – $450,000 |

还没算机房、电力、散热、以及运维人力。

### 量级对比

| 方案 | 月成本 | 相对订阅 |
|---|---|---|
| GLM Coding Plan Lite | **$18** | 1× |
| 8×H200 云租 · 工作日 8h | $3,984 | **221×** |
| 8×H200 云租 · 全时批发 | $16,527 | **918×** |
| 8×H200 云租 · 全时大厂 | $20,475 | **1,138×** |

**这个建议唯一成立的场景**：你所在的组织本来就有闲置的 H200/H100 集群——那自部署是"边际成本为零"的合理选择。否则纯属为省 $18/月 去买一台服务器。

### 如果确实要数据不出本机，现实选项

按可行性排序：

1. **分级使用**（零额外成本）
   敏感代码不交给任何云端 agent——注意这一条对 GPT 同样适用，见坑 2：Codex 的 web search 和 vision 本身就会走 OpenAI 服务器。不敏感的活儿照常用 Coding Plan。

2. **本地小模型兜底**（消费级硬件）
   30B 级模型可跑在单张消费卡或大内存 Mac 上，覆盖补全、解释、小型重构。能力明显低于 744B 前沿模型，这是拿能力换隔离。

3. **企业私有化部署报价**
   如果真是公司采购、有预算走这条路——找智谱/火山要私有化方案，别自己搭。厂商会连带交付推理优化和运维。

4. **接受云端 + 合同约束**
   GLM Coding Plan 目前的状态是零数据留存 + 代码开源可审计 + 信通院/绿盟审计。按需评估。

**核心 tradeoff**：「数据不出本机」和「用前沿大模型」互斥，除非付 6 位数。这不是一个能用配置绕过去的技术问题。

### 改推「纯 OpenAI」

如果你的活儿主要是模糊调试、长程无人值守、要看屏幕——GLM 那点差价换不来返工成本。

### 不推荐的做法

| 做法 | 为什么不行 |
|---|---|
| 顶层 `model_provider = "ZAI"` | 桌面版跟着切，废掉 computer-use / browser / 办公插件 |
| 装 ZCode 跑日常活儿 | 多维护一套工具；沙箱、插件生态、审批模型都不如 Codex；且有静默上传工作区的黑历史（3.12.3 及以前） |
| 用 shim 转换协议 | 默认关掉 thinking，拿到残障模型 |

---

## 成本参考

积分制，由 input / cached input / output / MCP 用量按模型倍率加权。

| 档 | 5 小时额度 | 每周额度 |
|---|---|---|
| Lite | 2,000 | 10,000 |
| Pro | 12,000 | 60,000 |
| Max | 28,000 | 140,000 |

- **非高峰半价**；高峰 = 周一至周五 14:00–18:00（新加坡时间）
- Lite + GLM-5.3 官方估 43M–105M tokens/周（视缓存命中率，是厂商口径不是保证值）
- `cached input` 倍率 0.56 是最便宜的一档，但**请求前缀不一致会击穿缓存**

---

## 顺带的好处：这是最干净的对照实验

挂上 profile 后，同一个外壳、同一批任务：

```powershell
codex        "把用户模块的回调改成 async/await"
codex -p glm "把用户模块的回调改成 async/await"
```

外壳变量被消掉，**差出来的就是纯模型差**。这是回答"到底有多少能力差距"唯一没有争议的方式。

### 验收别只看"做没做完"

至少记四个：

1. `pass@1` 和 `pass@4` —— 区分能力不足 vs 可靠性不足
2. **break rate** —— 改坏原本通过的代码的比例。参照值：GLM-5.3 Flash 6.9%，全量版 4.4%
3. 每任务积分消耗
4. 人工返工时间

样本 ≥ 12 个代表性任务，必须包含重试和评审时间——否则省下的钱会被返工吃掉。

### 换模型最贵的成本不是钱

| 层 | 内容 | 换 provider 时 |
|---|---|---|
| 模型 | 推理与生成 | 换掉 |
| 外壳 | 工具、审批、hooks、MCP | 不变 |
| 项目上下文 | AGENTS.md、tests、脚本、文档 | **能从文件自动重载** |
| 对话状态 | 已排除的假设、否决的方案、口头约定 | **不转移** |

Codex 和 Claude Code 的 memory 都是**文件驱动**的——每轮重新加载文件。只存在于长对话里的东西，比如「花一小时证明了某行日志在误导人」「约定不动 auth 中间件」，新起的 GLM 会话一无所知。

**切换点要选在文件状态完整的时刻。**
