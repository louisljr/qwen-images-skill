# Qwen-Image API 参考（阿里云百炼 / DashScope）

## 端点

```
POST {BASE_URL}/services/aigc/multimodal-generation/generation
```

| 环境 | BASE_URL |
|---|---|
| 北京（中国大陆） | `https://dashscope.aliyuncs.com/api/v1` |
| 新加坡（国际） | `https://dashscope-intl.aliyuncs.com/api/v1` |

鉴权：`Authorization: Bearer $DASHSCOPE_API_KEY`

⚠️ 常见错误路由（会 404 / url error）：

- `/compatible-mode/v1/images/generations` —— OpenAI 兼容模式不提供 Qwen-Image 生图
- `/services/aigc/text-to-image/image-synthesis` —— 这是 Wanx 系**异步**任务接口，需 `X-DashScope-Async: enable` 再轮询 `/api/v1/tasks/{task_id}`

## 请求

```json
{
  "model": "qwen-image-3.0-pro",
  "input": {
    "messages": [
      { "role": "user", "content": [ { "text": "你的提示词" } ] }
    ]
  },
  "parameters": {
    "n": 1,
    "size": "1024*1024",
    "negative_prompt": "",
    "prompt_extend": true,
    "watermark": false
  }
}
```

- 仅支持**单轮**：`messages` 只有 1 条 `user` 消息。
- 文生图：`content` 里**恰好 1 个** `text` 对象。
- 图像编辑：`content` 里 1–3 个 `image` 对象 + 恰好 1 个 `text` 对象。
  `image` 接受公网 URL 或 `data:{mime_type};base64,{data}`。
- `size` 用**星号**分隔（`"1024*1024"`），横版在前：`"1536*1024"` 是 3:2 横图。

## 响应

```json
{
  "request_id": "…",
  "output": {
    "choices": [
      { "message": { "content": [ { "image": "https://dashscope-result-….oss-cn-beijing.aliyuncs.com/….png" } ] } }
    ]
  },
  "usage": { "image_count": 1, "output_width": 1024, "output_height": 1024 }
}
```

**图片位置：`output.choices[*].message.content[*].image`**，是 OSS 临时签名链接，有效期有限，请立即下载。
（部分旧版/代理部署会返回 `output.results[*].url`，脚本两种都兼容。）

失败时返回 `code` / `message`（如 `InvalidApiKey`、`Throttling`、`Model not exist`）。

## 模型

| 模型 | 说明 |
|---|---|
| `qwen-image-3.0-pro` | 3.0 系列，当前主力，质量最好 |
| `qwen-image-3.0` | 3.0 标准版 |
| `qwen-image-2.0-pro` | 2.0 pro，`n` 可取 1–6 |
| `qwen-image-max` | `n` 固定 1 |
| `qwen-image-edit-plus` / `-max` | 图像编辑专用 |
| `wan2.7-image` | 同端点的 Wan 系，走异步任务 |
| `wanx2.1-t2i-turbo` | Wanx 系，**另一条**异步端点 |

模型名以控制台「模型广场」当前可见的为准，`Model not exist` 通常是名字或开通状态问题。

## 常用尺寸

- `1024*1024`（1:1）
- `1536*1024`（3:2 横）/ `1024*1536`（2:3 竖）
- `2048*2048`（1:1 高清，慢且贵）
- `1280*720`（16:9 横）/ `720*1280`（9:16 竖）

## 直连 curl（不走脚本时）

```bash
curl -sS -X POST "$DASHSCOPE_BASE_URL/services/aigc/multimodal-generation/generation" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-image-3.0-pro",
    "input": {"messages": [{"role": "user", "content": [{"text": "黄昏的山间湖泊，电影感光线"}]}]},
    "parameters": {"size": "1536*1024", "n": 1, "prompt_extend": true, "watermark": false}
  }'
```

## 来源

- 阿里云官方文档：https://help.aliyun.com/zh/model-studio/qwen-image-api
- 官方模型页：https://modelstudio.console.alibabacloud.com/

## OpenAI 兼容模式能不能用来生图？（2026-10-10 实测）

在北京节点标准百炼账号上实测：

| 探测 | 结果 |
|---|---|
| `GET /compatible-mode/v1/models` | **200**，返回 247 个模型，其中**包含** `qwen-image-3.0-pro`、`qwen-image-edit-plus`、`wan2.7-image`、`z-image-turbo` |
| `POST /compatible-mode/v1/images/generations` | **404**（响应体为空，属网关级 404，路由不存在） |
| `POST /v1/images/generations` | 404 |
| `POST /compatible-mode/v1/images/generations`，换 `model: qwen-image` | 404 |

**结论：百炼 compatible-mode 只在 `/models` 里"列出"图像模型，并不提供 `/images/generations` 路由。**
模型可见 ≠ 路由可用。想用 OpenAI SDK 的 `client.images.generate()` 直连百炼，此路不通。
（注意：千问云 / MaaS 域名如 `maas.qwencloudapi.com` 是**另一套平台**，那边据称有这个路由，与百炼不通用。）

### 那 GUI 客户端（WorkBuddy 等）怎么办

两种接入方式，别混为一谈：

1. **当 Skill 用（推荐，本技能就是这个路子）**
   skill 里的脚本自己打原生端点，Key 从环境变量或 `~/.env` 读。
   **完全不需要 OpenAI 兼容模式** —— 兼容模式只约束"对话模型"那一层，脚本是进程内直连，绕过它。

2. **当自定义模型注册**（`~/.workbuddy/models.json`）
   这条路要求供应商提供 OpenAI 兼容的 `/v1/images/generations`。百炼直连不行，需要：
   - 挂一层适配器/代理，把 `/v1/images/generations` 翻译成原生调用再返回 `b64_json`；或
   - 用客户端的自定义协议开关（WorkBuddy 社区文档提到 `models.json` 里有 `useCustomProtocol`
     字段，**此项未实测**）。

   另外注意 `models.json` 的图片相关开关 `supportsImages` 指的是**视觉输入**（能不能看图），
   不是"能不能生图"，别搞混。
