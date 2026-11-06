# MiMo v2.5 语音模型 API 协议（实测版）

> 全部结论来自对 `https://token-plan-cn.xiaomimimo.com/v1` 的实际探测，非文档推测。
> 探测手段：构造请求 → 读服务端 400 报错 → 逐层收敛参数。

## 1. 模型清单

`GET /v1/models` 返回 6 个模型：

| 模型 ID | 类型 | 能力 |
|---|---|---|
| `mimo-v2.5` | 对话 | 通用 LLM（reasoning 模型，有 `reasoning_content`） |
| `mimo-v2.5-pro` | 对话 | 增强版 LLM |
| `mimo-v2.5-asr` | 语音→文本 | 语音识别 |
| `mimo-v2.5-tts` | 文本→语音 | 基础合成（默认音色）+ 唱歌模式 |
| `mimo-v2.5-tts-voiceclone` | 文本→语音 | 音色克隆（需参考音频） |
| `mimo-v2.5-tts-voicedesign` | 文本→语音 | 音色设计（需文字描述） |

## 1.1 能力定位（官方口径 + 实测校验）

### MiMo-V2.5-ASR — 语音识别

- **定位**：端到端自动语音识别（Speech-to-Text）
- **能力**：中英双语、方言、代码切换、歌词、噪声环境、多人对话
- **适合**：会议转写、字幕生成、方言转录、录音分析
- **实测补充**：中文准确率极高（`红妆`→`红装` 仅同音替换）；**英文专有名词弱**（`MiMo`→`memo`）；对唱腔拖腔无能为力（输出大段"啊"填充）

### MiMo-V2.5-TTS — 语音合成（精品音色）

- **定位**：内置多种高质量精品音色，开箱即用
- **能力**：通过自然语言指令控制情绪、语气、语速
- **适合**：有声书、播客、通用对话场景
- **实测补充**：
  - "自然语言指令"的**具体实现是 content 标签**，非独立参数。已验证：`（唱歌）``（念白）``（哭腔）``（粤语）``（河南话）`
  - **无独立语速参数**
  - 预置音色 `（冰糖）``（苏打）` **必须写 content 标签**；`voice` 参数传音色名**无效**
  - 原生支持唱歌模式，实测时长 ×3.35

### MiMo-V2.5-TTS-VoiceDesign — 语音合成（自定义音色）

- **定位**：用文字描述生成全新音色
- **能力**：输入"年迈的东欧学者""元气少女"等描述，生成对应嗓音，无需参考音频
- **适合**：游戏NPC、动画角色、虚拟主播、品牌IP
- **实测补充**：✅ 描述**生效且可量化**——三个戏曲行当 F0 实测 98.1 / 112.3 / 179.8 Hz，与描述吻合
- **调用结构**：`user.content`=音色描述，`assistant.content`=待读文本

### MiMo-V2.5-TTS-VoiceClone — 语音合成（声音克隆）

- **定位**：高保真复刻真人声音
- **能力**：数秒参考音频即可克隆，保留音色、气息等个人细节
- **适合**：配音演员声音复刻、个性化语音助手、内容再创作
- **实测补充**：
  - 时长上界远超"数秒"：实测 **7.5 分钟 / 7.24MB mp3** 可用
  - 音色继承**跟随参考素材而非文本语义**
  - ⚠️ **只克隆音色，不克隆旋律/唱腔**（音高曲线、时长、拖腔信息被丢弃）
  - ⚠️ 基频可能漂移（合成音频当参考漂移 +37%；真实录音素材效果更好）
  - 传参：**顶层 `audio.voice` = DataURL**

## 2. 统一入口

**所有模型都走 `POST /v1/chat/completions`。**

- 没有 `/v1/audio/speech`（实测 404）
- 没有 `/v1/audio/transcriptions`
- 鉴权：`Authorization: Bearer <key>`

这跟 OpenAI 的 audio 接口设计不同 —— 小米把语音能力塞进了 chat 协议里，用 **role 约定**来区分意图。

## 3. 各模型请求格式

### 3.1 ASR —— 音频进 user 消息

```json
{
  "model": "mimo-v2.5-asr",
  "messages": [{
    "role": "user",
    "content": [{
      "type": "input_audio",
      "input_audio": { "data": "<裸base64>", "format": "wav" }
    }]
  }]
}
```

- `content` 必须是**数组**，元素类型 `input_audio`
- `data` 是**裸 base64**（不带 `data:` 前缀）
- `format` 可选：`mp3` / `flac` / `m4a` / `wav` / `ogg`
- 响应文本在 `choices[0].message.content`

### 3.2 TTS —— 只放 assistant 消息【含唱歌模式】

**基础调用**：

```json
{
  "model": "mimo-v2.5-tts",
  "messages": [{ "role": "assistant", "content": "要朗读的文本" }]
}
```

- **`assistant.content` 才是待读文本**（不是 user）
- **禁止出现 system 角色** —— 加了就 400

**⚠️ 重大修正（2026-09-17 实测推翻早前结论）**

`mimo-v2.5-tts` **原生支持「唱歌模式」**，通过 `content` 里的**音频标签**控制。

我此前的"TTS 只能念白"结论是错的 —— 原因是我一直用**无标签的纯文本**调用，从未触发唱歌模式。用错误的输入去验证，数据再漂亮也无效。

**标签语法**：`（唱歌）` 或 `[唱歌]`，**前置**在正文前。

| 写法 | 效果 |
|---|---|
| `（唱歌）唱词` | ✅ 触发唱歌模式（全角括号） |
| `[唱歌]唱词` | ✅ 触发（方括号，输出与全角一致） |
| `<唱歌>唱词` | ❌ 未识别，当文字念出 |
| `system` 角色传标签 | ❌ 400，TTS 禁 system |

**实测证据**（同一段 28 字七字句唱词）：

| 模式 | 时长 | F0 中位 | 音高跨度 |
|---|---|---|---|
| 纯文本（念白） | 7.68s | 233.0 Hz | 119.7 Hz |
| `（唱歌）` | **25.76s** | 358.2 Hz | **142.0 Hz** |
| `（唱歌）（冰糖）` | **31.04s** | 363.6 Hz | **203.4 Hz** |

- 时长 **×3.35**（7.68s → 25.76s）→ 多出的 18 秒是拖腔
- 音高跨度 **119.7 → 203.4 Hz** → 有旋律起伏，非语言语调
- F0 进入 **358–364 Hz** 高音区 → 戏曲唱腔音域

**标签可叠加**：`（唱歌）（冰糖）` 比单 `（唱歌）` 又长 69%（297KB → 502KB），说明两个标签独立生效。

**预置音色（实测）**：
- ✅ `（冰糖）`——生效，音高跨度从 142Hz 拉到 203Hz
- ✅ `（苏打）`——生效
- ❌ `voice` 参数传音色名 —— **无效**，被忽略（输出与默认音色字节完全一致）
- ❌ `audio.voice` 传音色名 —— **无效**，同上

**结论：音色名要写在 `content` 的标签里，不能走参数。**

**其他已验证标签**：`（念白）`、`（粤语）`、`（河南话）`、`（哭腔）` 均被接受（`（哭腔）` 实测 F0 抬至 338Hz）。

**标签与念白的关系**：不加标签 = 默认念白；加 `（唱歌）` = 唱。文档 B 节"TTS 只能念白"的说法仅对**无标签调用**成立。

### 3.2.1 京剧唱段可用方案（修正）

**MiMo `tts` + `（唱歌）` 标签可以出唱段**，这是此前被漏掉的能力。

对比文档原方案：
- 文档 D 节说"要精确控制唱腔必须上 DiffSinger"——**精确控制音高曲线**确实仍需 DiffSinger
- 但**"能不能唱"这一层，MiMo 已具备**，无需建音源库

适用判断：
| 需求 | 方案 |
|---|---|
| 快速出唱段，音高由模型决定 | ✅ MiMo `（唱歌）` 标签 |
| 精确指定每个音的音高/时长 | DiffSinger（需音源库） |
| 带伴奏的完整编曲 | Suno / ACE-Step |

### 3.3 voicedesign —— 描述进 user，文本进 assistant

```json
{
  "model": "mimo-v2.5-tts-voicedesign",
  "messages": [
    { "role": "user",      "content": "低沉浑厚的成年男性嗓音，语速偏慢，略带磁性" },
    { "role": "assistant", "content": "要朗读的文本" }
  ]
}
```

- `user.content` = 音色**文字描述**（不能为空）
- 支持中文描述（实测通过）

### 3.4 voiceclone —— 顶层 audio.voice 传 DataURL

```json
{
  "model": "mimo-v2.5-tts-voiceclone",
  "messages": [{ "role": "assistant", "content": "要朗读的文本" }],
  "audio": { "voice": "data:audio/wav;base64,<base64>" }
}
```

**这是最难猜的一个，三层才试对：**

| 尝试 | 字段 | 报错 | 结论 |
|---|---|---|---|
| assistant 带 `audio` | `message.audio` | `audio must not be empty` | 位置错 |
| user 带 `input_audio` | `message.content[]` | `audio must not be empty` | 位置错 |
| **顶层 `audio`** | `audio.data` | `audio.voice must not be empty` | **层级对了** |
| 顶层 `audio.voice` = 裸 base64 | `audio.voice` | `must be a DataURL` | 格式错 |
| **顶层 `audio.voice` = DataURL** | `audio.voice` | ✅ 200 | **正确** |

关键点：
- 位置是**请求体顶层**的 `audio` 对象，不在 messages 里
- 字段名是 **`voice`**，不是 `data`
- 值必须是完整 **DataURL**：`data:audio/wav;base64,<...>`

## 4. 响应格式（TTS 三兄弟通用）

```json
{
  "choices": [{
    "message": {
      "content": "",
      "role": "assistant",
      "audio": {
        "id": "...",
        "data": "<裸base64 WAV>",
        "expires_at": null,
        "transcript": null
      }
    }
  }]
}
```

- 音频在 `choices[0].message.audio.data`，**裸 base64**，解码即得文件
- **不是**二进制流，**不是**临时 URL —— 直接内嵌，无需二次下载
- `audio.transcript` 字段存在但在 TTS 场景恒为 `null`（预留位）
- `content` 恒为空字符串

### 实测音频参数

生成的文件全部为有效 WAV：

| 文件 | 大小 | 格式 | 时长 |
|---|---|---|---|
| test_tts.wav | 215 KB | 24kHz / 16bit / 单声道 | 4.48s |
| test_design.wav | 238 KB | 24kHz / 16bit / 单声道 | 4.96s |
| test_clone.wav | 99 KB | 24kHz / 16bit / 单声道 | 2.08s |

**统一 24kHz / 16bit / mono** —— 后面做拼接不用重采样。

## 5. 实测踩到的坑

### 5.1 `mimo-v2.5` 是 reasoning 模型

探测时 `max_tokens: 20` 全部被 `reasoning_content` 吃掉，`content` 返回空串：

```
finish_reason: "length"
content: ""
reasoning_content: "The user is asking me to just say \"ok\"..."
usage.completion_tokens_details.reasoning_tokens: 21
```

**结论**：调 `mimo-v2.5` 必须给足 `max_tokens`（建议 ≥ 512），否则思考过程占满预算、正文为空。

### 5.2 ASR 对英文专有名词识别弱

实测：原文 `"欢迎使用小米MiMo语音合成，这是一段端到端测试。"`
转写 → `"欢迎使用小米 memo 语音合成，这是一段端到端测试。"`

- 中文部分 **100% 正确**
- `MiMo` 被识别成 `memo`（英文品牌词的典型弱项）
- 后处理建议：对已知专有名词做词表替换

### 5.3 服务端报错信息极有用

这个 API 在参数错误时会把**具体要求**写在 `error.param` 里，例如：

```json
{"error": {"code": "400", "message": "Param Incorrect",
           "param": "ASR request requires a user message with input_audio content"}}
```

**调试方法**：故意传空参数，读报错即可反推格式，比翻文档快。

## 6. 封装脚本

`mimo.py` —— 零依赖（仅标准库 `urllib`），四个函数：

```bash
export MIMO_API_KEY='<your-key>'
export MIMO_BASE_URL='https://token-plan-cn.xiaomimimo.com/v1'

python mimo.py asr    input.wav
python mimo.py tts    "要朗读的文本" out.wav
python mimo.py design "低沉男声，语速慢" "要朗读的文本" out.wav
python mimo.py clone  ref.wav "要朗读的文本" out.wav
```

Python 内调用：

```python
from mimo import asr, tts, voicedesign, voiceclone

text, _          = asr("input.wav")
size, _          = tts("你好", "out.wav")
size, _          = voicedesign("低沉男声", "你好", "out.wav")
size, _          = voiceclone("ref.wav", "你好", "out.wav")
```

### 选型速查

| 场景 | 用哪个 |
|---|---|
| 音频转文字 | `asr` |
| 普通朗读，不挑音色 | `tts` |
| 指定风格描述，无样本 | `voicedesign` |
| 模仿特定人声，有样本 | `voiceclone` |

一句话：**clone 要样本，design 要描述，tts 都不要。**

## 7. 待确认项

以下未实测，标注为未知，不要当成结论：

- 并发/限流策略（未测）
- 计费方式（按 token 还是按时长）
- `mimo-v2.5-pro` 与 `mimo-v2.5` 的具体差异（仅确认存在）

## 7.1 已补测项（2026-09-17 京剧实验）

### 参考音频限制 —— 比预期宽松得多

| 项 | 实测值 |
|---|---|
| 参考音频时长 | ✅ 至少 **7.5 分钟**（453s）可用，无报错 |
| 参考音频大小 | ✅ 至少 **7.24 MB**（`mp3`）可用 |
| DataURL 大小 | ✅ 至少 **9.4 MB** base64 可用 |
| 支持格式 | `mp3` 实测可用（此前只测过 `wav`） |
| 超时 | 300s 内正常返回 |

**推论**：文档类方案的"5–10 秒最佳"是质量建议，不是接口限制。

### voiceclone 的能力边界（重要）

| 项 | 实测结果 |
|---|---|
| 音色继承 | ✅ 有效。三条输出 F0 落在 205–250Hz 同区间，一致性好 |
| 音色来源 | ⚠️ **跟随参考素材，不跟随文本语义**。给"众将听令"（将军台词）配旦角素材，输出女声 |
| 咬字 | ✅ 准确 |
| **旋律/唱腔继承** | ❌ **无此能力**。参考音频的音高曲线、时长、拖腔信息被丢弃 |

**机制**：`voiceclone` 只提取**音色特征**（音高范围、音质、共振峰）用于合成。它不提取旋律。**注意**：这是 `voiceclone` 的能力边界；`tts` + `（唱歌）` 标签能唱，但唱腔由模型生成而非从参考音频学习。

**对照实验**：同一段唱词文本，用真实京剧录音 vs 合成音频做参考，停顿数分别是 18 和 11。**真实录音参考反而更碎**，因为节奏由待读文本决定，与参考音频无关。

**能精确控制唱腔的方案**：DiffSinger / OpenUtau（输入音高曲线 + 音素 + 时长）。
**能唱但音高由模型决定的方案**：MiMo `tts` + `（唱歌）` 标签（见 3.2 节）。

### 不支持的细粒度控制

| 功能 | 支持情况 |
|---|---|
| `[breath]` / `[laughter]` 标签 | ❌ 不支持（那是 CosyVoice2 特性） |
| `<strong>字</strong>` 加重 | ❌ 不支持 |
| 语速参数 | ❌ 无独立参数，`voicedesign` 只能靠描述词间接影响 |
| 音高曲线控制 | ❌ 无 |
| 拖腔/滑音 | ❌ 无 |

## 8. 安全提醒

本次调试中 API key 曾以明文出现在会话记录里。**建议到后台轮换该 key。**
脚本已设计为从环境变量 `MIMO_API_KEY` 读取，不要把 key 写进代码。
