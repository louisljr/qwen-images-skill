#!/usr/bin/env python3
"""Qwen-Image 文生图 / 图像编辑 CLI（仅用 Python 标准库，零第三方依赖）。

用法：
    python qwen_image.py --prompt "一只戴帽子的猫，油画风格"
    python qwen_image.py --prompt "把背景换成雪山" --image ./in.png
    python qwen_image.py --prompt "..." --size 1536x1024 --n 2 --out ./out

环境变量：
    DASHSCOPE_API_KEY   百炼 API Key（兼容旧名 BAILIAN_API_KEY）
    DASHSCOPE_BASE_URL  默认 https://dashscope.aliyuncs.com/api/v1
    QWEN_IMAGE_MODEL    默认 qwen-image-3.0-pro
"""

import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

# 一律以 UTF-8 输出。Windows 控制台默认是 GBK/cp1252，直接 print 中文 JSON 会抛
# UnicodeEncodeError；中文提示词与路径也会被写坏。errors="replace" 保证绝不因此崩掉。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 老 Python 或已重定向的流
        pass

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
ROUTE = "/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen-image-3.0-pro"

SKILL_VERSION = "1.1.0"
SKILL_MARKER = "qwen-images-skill"
RUN_LOG_NAME = "_runs.jsonl"

# 兼容原 qwen-images-skill 仓库用过的变量名
API_KEY_ENVS = ("DASHSCOPE_API_KEY", "BAILIAN_API_KEY")

# 环境变量缺失时的兜底来源（按顺序查找）。供 GUI 客户端（WorkBuddy 等）
# 使用，这类客户端不会继承 shell 的 export。
FALLBACK_ENV_FILE = "~/.env"

# 由 load_fallbacks() 填充
FALLBACK = {}


def load_env_file(path):
    """解析 .env 风格的键值对（只解析文本，不执行其中任何内容）。"""
    values = {}
    try:
        text = pathlib.Path(path).expanduser().read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if key:
            values[key] = val.strip().strip('"').strip("'")
    return values


def load_fallbacks():
    """当环境变量没有对应值时，从 ~/.env 兜底读取。"""
    global FALLBACK
    FALLBACK = load_env_file(FALLBACK_ENV_FILE)
    return FALLBACK


def first_env(names, default=None):
    for n in names:
        v = os.getenv(n) or FALLBACK.get(n)
        if v:
            return v
    return default


def normalize_size(raw):
    """API 要求 "宽*高"（星号），用户常写 1024x1024 / 1024×1024。"""
    if not raw:
        return None
    for ch in ("x", "X", "×", "＊", "*"):
        raw = raw.replace(ch, "*")
    return raw


def to_image_ref(value):
    """本地路径 -> data URI；URL / data URI 原样返回。"""
    if value.startswith(("http://", "https://", "data:")):
        return value
    path = pathlib.Path(value).expanduser()
    if not path.is_file():
        raise SystemExit(f"错误：找不到图片文件 {path}")
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_payload(args, model):
    content = [{"image": to_image_ref(p)} for p in args.image]
    content.append({"text": args.prompt})

    parameters = {"watermark": args.watermark, "prompt_extend": args.prompt_extend}
    if args.size:
        parameters["size"] = normalize_size(args.size)
    if args.n:
        parameters["n"] = args.n
    if args.negative_prompt:
        parameters["negative_prompt"] = args.negative_prompt

    return {
        "model": model,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": parameters,
    }


def call_api(url, api_key, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(detail)
            code = body.get("code") or body.get("error", {}).get("code")
            msg = body.get("message") or body.get("error", {}).get("message")
            if code or msg:
                detail = f"{code}: {msg}"
        except json.JSONDecodeError:
            pass
        raise SystemExit(f"错误：接口返回 HTTP {exc.code}\n{detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"错误：网络请求失败（{exc.reason}）。请检查网络与 BASE_URL。")
    except json.JSONDecodeError:
        raise SystemExit("错误：接口返回的不是合法 JSON。")


def extract_urls(response):
    """图片链接位于 output.choices[*].message.content[*].image，兼容 results[*].url。"""
    urls = []
    output = response.get("output") or {}
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        for item in message.get("content") or []:
            if isinstance(item, dict) and item.get("image"):
                urls.append(item["image"])
    for item in output.get("results") or []:
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    return urls


def save_image(url, outdir, stem, index):
    """签名 URL 有效期有限，落地到本地。返回文件路径。"""
    suffix = ".png"
    if url.startswith("data:"):
        header, _, b64 = url.partition(",")
        if "image/" in header:
            suffix = "." + header.split("image/", 1)[1].split(";", 1)[0]
        blob = base64.b64decode(b64)
    else:
        with urllib.request.urlopen(url, timeout=120) as resp:
            blob = resp.read()

    name = f"{stem}-{index}{suffix}"
    path = outdir / name
    path.write_bytes(blob)
    return path


def write_run_log(outdir, args, model, request_id, results):
    """把每次调用追加到 <out>/_runs.jsonl。

    双重作用：排查问题，以及回答"这张图到底是本技能生成的，还是客户端内置生图
    通道生成的"。文件里有对应记录，就证明走的是本技能。
    """
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "skill": SKILL_MARKER,
        "version": SKILL_VERSION,
        "model": model,
        "prompt": args.prompt,
        "size": normalize_size(args.size),
        "n": args.n,
        "mode": "edit" if args.image else "text2image",
        "request_id": request_id,
        "images": [r.get("path") or r.get("url") for r in results],
        "cwd": os.getcwd(),
    }
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        with (outdir / RUN_LOG_NAME).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"提示：运行留痕写入失败（{exc}），不影响出图。", file=sys.stderr)


def build_parser():
    p = argparse.ArgumentParser(
        description="调用百炼 Qwen-Image 生成 / 编辑图片（标准库实现）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--prompt", default=None, help="提示词")
    p.add_argument(
        "--image",
        action="append",
        default=[],
        metavar="PATH_OR_URL",
        help="参考图（可重复，最多 3 张）；给了就是图像编辑",
    )
    p.add_argument("--model", default=None, help=f"默认 {DEFAULT_MODEL}")
    p.add_argument("--size", default="1024x1024", help='如 1024x1024、1536x1024、2048*2048')
    p.add_argument("--n", type=int, default=1, help="生成数量，默认 1")
    p.add_argument("--negative-prompt", default=None, help="负向提示词")
    p.add_argument("--no-prompt-extend", dest="prompt_extend", action="store_false",
                   help="关闭提示词自动扩写")
    p.add_argument("--no-watermark", dest="watermark", action="store_false",
                   help="不加 AI 生成水印")
    p.add_argument("--out", default="./qwen-images-out", help="图片保存目录")
    p.add_argument("--name", default=None, help="文件名前缀，默认用时间戳")
    p.add_argument("--no-download", action="store_true", help="只返回链接，不下载")
    p.add_argument("--print-payload", action="store_true", help="打印请求体后退出（调试用）")
    p.add_argument("--api-key", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--check-key", action="store_true",
                   help="只报告 API Key 的来源（不打印 Key、不调用接口）")
    p.add_argument("--timeout", type=int, default=180)
    p.set_defaults(prompt_extend=True, watermark=False)
    return p


def main():
    args = build_parser().parse_args()
    load_fallbacks()

    base_url = (
        args.base_url or first_env(("DASHSCOPE_BASE_URL", "BAILIAN_BASE_URL")) or DEFAULT_BASE_URL
    ).rstrip("/")
    model = args.model or first_env(("QWEN_IMAGE_MODEL", "BAILIAN_MODEL"), DEFAULT_MODEL)
    url = base_url + ROUTE

    payload = build_payload(args, model)
    if args.print_payload:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not args.prompt and not args.check_key:
        raise SystemExit("错误：必须提供 --prompt（或用 --check-key 只检查 Key）。")

    if args.check_key:
        source = "缺失"
        if args.api_key:
            source = "--api-key 参数"
        else:
            for n in API_KEY_ENVS:
                if os.getenv(n):
                    source = f"环境变量 ${n}"
                    break
                if FALLBACK.get(n):
                    source = f"{FALLBACK_ENV_FILE} 中的 {n}"
                    break
        print(json.dumps({
            "key_source": source,
            "base_url": base_url,
            "model": model,
        }, ensure_ascii=False, indent=2))
        return 0 if source != "缺失" else 1

    api_key = args.api_key or first_env(API_KEY_ENVS)
    if not api_key:
        raise SystemExit(
            "错误：未设置 API Key。请 export DASHSCOPE_API_KEY=sk-xxx、"
            f"写入 {FALLBACK_ENV_FILE}，或用 --api-key 传入。"
        )

    response = call_api(url, api_key, payload, args.timeout)
    urls = extract_urls(response)
    if not urls:
        raise SystemExit(
            "错误：响应中没有图片。原始返回：\n"
            + json.dumps(response, ensure_ascii=False, indent=2)
        )

    stem = args.name or time.strftime("qwen-%Y%m%d-%H%M%S")
    results = []
    outdir = pathlib.Path(args.out).expanduser()
    for i, u in enumerate(urls, start=1):
        item = {"url": u if not u.startswith("data:") else "(base64 inline)"}
        if not args.no_download:
            outdir.mkdir(parents=True, exist_ok=True)
            item["path"] = str(save_image(u, outdir, stem, i).resolve())
        results.append(item)

    summary = {
        "model": response.get("model", model),
        "request_id": response.get("request_id"),
        "usage": response.get("usage"),
        "images": results,
    }

    write_run_log(outdir, args, model, response.get("request_id"), results)

    print(f"[{SKILL_MARKER}] model={model} request_id={response.get('request_id')}",
          file=sys.stderr)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not args.no_download:
        print(f"\n共 {len(results)} 张，已保存到 {outdir.resolve()}", file=sys.stderr)
        print("注：链接为临时签名 URL，请尽快使用已下载的本地文件。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
