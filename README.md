# qwen-images

一个 Agent Skill，用 **通义千问 Qwen-Image**（阿里云百炼 / DashScope）生成和编辑图片。

**它要解决的具体问题**：WorkBuddy 这类客户端只接受 **OpenAI 兼容**的模型接口，而百炼的
`compatible-mode` **不提供** `/images/generations` 路由 —— 于是 Qwen-Image 根本注册不进去。
本 skill 绕过这个限制：技能里的脚本是独立进程，直接打百炼原生端点，与客户端的模型层无关。

适用于任何支持 Agent Skills 标准的客户端（WorkBuddy、Claude Code、GitHub Copilot 等）。

## 为什么要绕

| | 说明 |
|---|---|
| WorkBuddy 的限制 | 模型层只走 OpenAI 兼容协议，自己拼 `/chat/completions` |
| 百炼的实际支持 | `GET /compatible-mode/v1/models` 能列出 `qwen-image-3.0-pro` 等（实测 200） |
| 但路由不存在 | `POST /compatible-mode/v1/images/generations` → **404**（实测）。模型可见 ≠ 路由可用 |
| 结论 | 没法把 Qwen-Image 注册成自定义模型。**走 Skill 才行** |

副作用（可能是你想要的）：这样出图走**你自己的百炼额度**，而不是 WorkBuddy 的积分；
模型、尺寸、负向提示词等参数都直接可控。

## 特性

- 文生图 + 图像编辑（图生图，最多 3 张参考图）
- **零第三方依赖**，只用 Python 标准库
- 自动下载图片到本地 —— 百炼返回的是临时签名 URL，过期就没了
- Key 自动从环境变量或 `~/.env` 读取，GUI 客户端无需额外配置
- 每次调用留痕（`_runs.jsonl`），可查证图是不是本 skill 生成的

## 安装

Skill 的安装方式在所有客户端和操作系统上都是同一件事：**把 `qwen-images/` 整个目录
放进客户端的 skills 目录**。没有安装器 —— 技能目录因客户端而异，写脚本反而会写错。

```bash
# macOS / Linux
cp -R qwen-images ~/.workbuddy/skills/

# Windows（PowerShell）
Copy-Item -Recurse qwen-images "$env:USERPROFILE\.workbuddy\skills\"
```

常见客户端的 skills 目录：

| 客户端 | macOS / Linux | Windows |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` |
| Claude Code | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |
| Copilot / Cursor / Codex 等 | 见各自文档；公共约定目录为 `.agents/skills/` | 同左 |

装完**重启客户端**即可被加载。

> 想跨客户端共用一份、避免多处副本各自漂移，可以把本仓库目录软链进各自的 skills 目录
> （`ln -s` / `mklink /D`）。前提是客户端会跟随软链 —— 不确定时用复制更稳妥。

## 配置

只需要一个百炼 API Key，脚本会按顺序自己找：

1. 环境变量 `DASHSCOPE_API_KEY`
2. `~/.env` 里的 `DASHSCOPE_API_KEY` ← **GUI 客户端（WorkBuddy）走这条**
3. 命令行 `--api-key`
4. 都没有 → 报错退出

> GUI 客户端不继承 shell 的 `export`，所以 `~/.env` 是它唯一可靠的来源。

确认能不能取到（不打印 Key、不调接口）：

```bash
python3 ~/.workbuddy/skills/qwen-images/scripts/qwen_image.py --check-key
```

可选覆盖：`DASHSCOPE_BASE_URL`（国际节点改 `https://dashscope-intl.aliyuncs.com/api/v1`）、
`QWEN_IMAGE_MODEL`。也兼容旧名 `BAILIAN_API_KEY` 等。

## 用法

```bash
# 文生图
python3 <技能目录>/scripts/qwen_image.py --prompt "黄昏的山间湖泊，电影感光线" --size 1536x1024

# 一次多张
python3 <技能目录>/scripts/qwen_image.py --prompt "..." --n 4

# 图像编辑：换背景 / 改风格，保留主体
python3 <技能目录>/scripts/qwen_image.py --prompt "把背景换成雪山" --image ./input.png

# 只拿链接不下载
python3 <技能目录>/scripts/qwen_image.py --prompt "..." --no-download

# 只看请求体（调试用，不调接口）
python3 <技能目录>/scripts/qwen_image.py --prompt "..." --print-payload
```

交互式使用更简单 —— 直接说「用 qwen-images 生成一张…」即可。

### 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--prompt` | 必填 | 提示词 |
| `--image PATH_OR_URL` | — | 参考图，可重复最多 3 张；给了就是图像编辑 |
| `--model` | `qwen-image-3.0-pro` | 也可用 `qwen-image-3.0`、`qwen-image-edit-plus` 等 |
| `--size` | `1024x1024` | 写 `1024x1024` 或 `1024*1024` 都行，脚本自动转换 |
| `--n` | `1` | 生成张数；上限随模型不同（2.0 系列 1–6，max/plus 固定 1） |
| `--negative-prompt` | — | 负向提示词 |
| `--no-prompt-extend` | 开 | 关闭提示词自动扩写 |
| `--no-watermark` | 已关 | 加 AI 生成水印 |
| `--out` | `./qwen-images-out` | 图片保存目录 |
| `--name` | 时间戳 | 文件名前缀 |
| `--no-download` | — | 只输出链接 |
| `--check-key` | — | 自检 Key 来源，不调接口 |

常用尺寸：`1024x1024`（1:1）、`1536x1024`（3:2 横）、`1024x1536`（2:3 竖）、
`1280x720`（16:9）、`720x1280`（9:16）。

### 输出

stdout 是一段 JSON 摘要（`request_id`、`usage`、每张图的 `url` 与本地 `path`）；
stderr 有一行标记；同时向 `<输出目录>/_runs.jsonl` 追加一条调用记录。

```json
{
  "model": "qwen-image-3.0-pro",
  "request_id": "480f11e4-434d-9ac0-8192-01928d44a77b",
  "images": [{ "url": "https://dashscope-….aliyuncs.com/….png", "path": "/…/qwen-1.png" }]
}
```

## 排查

| 现象 | 原因 |
|---|---|
| `url error` / 404 | 端点写错。必须是 `{BASE}/services/aigc/multimodal-generation/generation` |
| `InvalidApiKey` / 401 | Key 无效，或节点不匹配（北京 Key 访问国际节点） |
| `Model not exist` | 模型名写错，或账号没开通该模型 |
| `Throttling` | 并发或配额用尽，退避重试 |
| 图出来了但没有标记行、也没有 `_runs.jsonl` | **不是本 skill 生成的**，见下条 |

### 图不是本 skill 生成的？

WorkBuddy 等客户端**自带原生生图工具**（WorkBuddy 是 `ImageGen`），模型可能直接调用它而
不激活本 skill —— 原生工具通常优先级更高。判定办法：

| 凭据 | 本 skill | 客户端原生工具 |
|---|---|---|
| 输出目录 | `<cwd>/qwen-images-out/` | （WorkBuddy）`generated-images/` |
| 对话里 | `[qwen-images-skill] … request_id=…` + JSON 摘要 | 无 |
| 留痕 | `_runs.jsonl` 有记录 | 无 |
| 账单 | 你的百炼额度 | 客户端的积分 |

**想要稳定走到本 skill，就在指令里点名**：「用 qwen-images 生成…」。
（实测：不点名时 `ImageGen` 会抢走；点名后正常。）

## 仓库结构

本仓库就是一个 skill —— `qwen-images/` 即是技能包本身，可直接放进任何客户端的 skills 目录。

```
qwen-images/
├── SKILL.md            技能定义：触发条件 + 用法 + 踩坑约束
├── scripts/
│   └── qwen_image.py   生图/改图 CLI（标准库实现，跨平台）
└── references/
    ├── api.md          端点、请求/响应字段、模型清单、兼容模式实测
    └── examples.md     分类提示词范例
```

修改请直接改 `qwen-images/` 下的文件；改完重新复制到你的客户端 skills 目录（覆盖旧的）。

### 跨平台说明

- 脚本只用 Python 标准库，macOS / Linux / Windows 均可运行（Python 3.8+）。
- 输出强制 UTF-8，中文提示词在 Windows 控制台不会因 GBK 编码而报错。
- Key 支持 `~/.env`，Windows 上即 `%USERPROFILE%\.env`。

## 实测

- **WorkBuddy**（2026-10-13）：`--size 1536x1024 --n 2` 出图正常，留痕完整
- **WorkBuddy**（2026-10-10）：文生图走通
- **Claude Code**（2026-10-10）：文生图与图像编辑（换背景保留主体）均走通

## 许可

本仓库无 LICENSE 文件。使用前请确认你的百炼账号已开通对应图像模型。
