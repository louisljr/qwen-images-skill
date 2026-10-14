---
name: qwen-images
description: 当用户要求"生成图片/画一张/出一张图/配图/作图/生成海报或 logo 或插画/文生图/改图/换背景/修图"，或明确提到"通义千问生图、Qwen-Image、qwen-image、百炼生图、DashScope 生图"时，使用此技能。调用阿里云百炼（DashScope）的 Qwen-Image 模型完成文生图与图像编辑，产出真实图片文件。
slug: qwen-images
version: 1.1.0
displayName: 通义千问 Qwen-Image 生图与改图
agent_created: true
---

# Qwen-Image 生图技能

通过阿里云百炼（DashScope / Model Studio）调用 `Qwen-Image` 系列模型生成和编辑图片。
本技能只用一个标准库脚本，无第三方依赖。

**适用场景**：客户端只支持 OpenAI 兼容接口、因而无法直接接入 Qwen-Image 时
（典型如 WorkBuddy）。技能里的脚本是独立进程，直连百炼原生端点，不受客户端模型层限制。

## 前置条件

Key 按以下顺序查找，**前三步脚本自动完成，通常无需任何配置**：

1. 环境变量 `DASHSCOPE_API_KEY`
2. `~/.env` 里的 `DASHSCOPE_API_KEY`（GUI 客户端不继承 shell export，靠这一步兜底）
3. `--api-key` 参数
4. 都没有 → 报错退出

`~` 在 Windows 上即 `%USERPROFILE%`（如 `C:\Users\you\.env`），脚本自动处理，无需特殊配置。
文件按 `.env` 风格解析：`DASHSCOPE_API_KEY=sk-xxx`，可带引号，不执行其中任何内容。

```bash
# 自检：报告 Key 来源，不打印 Key、不调用接口
python3 <技能目录>/scripts/qwen_image.py --check-key
```

可选覆盖：`DASHSCOPE_BASE_URL`、`QWEN_IMAGE_MODEL`。
兼容旧名 `BAILIAN_API_KEY` / `BAILIAN_BASE_URL` / `BAILIAN_MODEL`。

- 新加坡/国际节点的 Key 与北京节点**不通用**。国际节点改 `DASHSCOPE_BASE_URL` 为
  `https://dashscope-intl.aliyuncs.com/api/v1`。

## 用法

脚本 = **本 SKILL.md 所在目录** + `/scripts/qwen_image.py`。
不确定绝对路径时，先 `ls` 一下本技能目录。

| 客户端 | 技能目录（示例） |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/qwen-images/` |
| Claude Code | `~/.claude/skills/qwen-images/` |
| 其他（Copilot / Cursor / Codex 等） | 见客户端文档，或公共约定目录 `.agents/skills/` |

```bash
# 文生图
python3 <本技能目录>/scripts/qwen_image.py \
  --prompt "黄昏的山间湖泊，电影感光线，超写实倒影" --size 1536x1024

# 一次多张
python3 <本技能目录>/scripts/qwen_image.py --prompt "..." --n 4

# 图像编辑：把参考图换成雪山背景，保留主体
python3 <本技能目录>/scripts/qwen_image.py \
  --prompt "把背景换成雪山，保持人物不变" --image ./input.png

# 只拿链接不下载 / 只看请求体
python3 <本技能目录>/scripts/qwen_image.py --prompt "..." --no-download
python3 <本技能目录>/scripts/qwen_image.py --prompt "..." --print-payload
```

脚本默认把图片下载到 `./qwen-images-out/`，并在 stdout 输出 JSON 摘要
（`request_id`、`usage`、每张图的 `url` 与本地 `path`）。

## 执行流程

1. 先跑 `--check-key` 确认 Key 能取到。取不到就问用户，不要瞎猜、不要伪造 Key。
2. 把用户的自然语言需求整理成结构化提示词（主体 + 风格 + 构图 + 光线 + 色调 + 镜头/氛围）。
   用户已给明确描述时直接沿用，只做轻微清理，不要擅自加戏。
3. 跑脚本。默认 `--size 1024x1024`、`--n 1`；用户提到比例时换算，如 "16:9" → `1536x1024`，
   "竖版 9:16" → `1024*1536`。
4. 把生成的**本地文件路径**告诉用户，并按需在对话里展示图片。

## 怎么确认图是本技能生成的

GUI 客户端（尤其 WorkBuddy）通常另有内置生图通道，容易抢活。三个可靠凭据：

1. **脚本的标记行**：每次成功执行都会向 stderr 打印
   `[qwen-images-skill] model=… request_id=…`。
2. **运行留痕**：每次调用追加一条记录到 `<输出目录>/_runs.jsonl`，
   含时间戳、模型、提示词、`request_id`、产出的文件路径。**文件里有记录 = 走的是本技能。**
3. **账单口径**：本技能消耗**你百炼账户**的额度；客户端内置生图走客户端的积分。

反过来说，只看"图出来了"不能证明是本技能干的 —— 必须看到上面任一凭据。

## 关键约束（踩坑记录）

- **端点**：`{BASE}/services/aigc/multimodal-generation/generation`。
  不是 `/images/generations`，也不是 `/text-to-image/generation` —— 那是 Wanx 系或 OpenAI 兼容模式，
  Qwen-Image 走**多模态生成**路由，Key 和端点都不通用。
- **入参结构**：必须 `input.messages[0].content`，且 `content` 里**恰好一个** `text` 对象；
  编辑时图片用 `image` 对象（最多 3 张）。不存在 `input.prompt` 这个字段。
- **尺寸格式**：`"宽*高"` 用**星号**，如 `"1024*1024"`、`"1536*1024"`。
  脚本会把 `1024x1024` 自动转成 `1024*1024`。
- **图片链接是临时签名 URL**，有效期有限，务必立即下载。
- **`n` 的上限随模型不同**：`2.0` 系列 1–6，`max` / `plus` 固定为 1。超过会报错。
- `prompt_extend` 默认开（模型自动扩写提示词）；`watermark` 默认关。

## 报错排查

| 现象 | 原因 |
|---|---|
| `url error` / 404 | 端点写错了，见上面「关键约束」 |
| `InvalidApiKey` / 401 | Key 无效或与节点不匹配（北京 Key 访问国际节点） |
| `Model not exist` / 权限错误 | 模型名写错，或账号没开通该模型 |
| `Throttling` / 限流 | 并发或配额用尽，退避重试 |
| 返回结构里找不到图片 | 用了别的路由（如 Wanx 异步任务），本技能的路由是同步多模态生成 |
| 图出来了但没有标记行、也没有 `_runs.jsonl` | **不是本技能生成的**，是客户端内置通道干的 |

## 参考资料

- `references/api.md` —— 端点、完整请求/响应字段、模型清单、尺寸规格，
  以及**百炼没有 OpenAI 兼容生图路由**的实测记录、GUI 客户端接入方式对比
- `references/examples.md` —— 分类提示词范例（产品图 / 插画 / 风景 / 海报）
