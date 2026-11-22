#!/usr/bin/env python3
"""Track the newest releases of key AI SDKs and frameworks via the GitHub API.

Writes RELEASES.md and refreshes the auto-generated block inside each
company's README (between <!-- releases:start --> and <!-- releases:end -->).
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = dt.date.today()

TRACKED = {
    "anthropic": ("Anthropic", [
        "anthropics/anthropic-sdk-python", "anthropics/anthropic-sdk-typescript",
        "anthropics/claude-code", "anthropics/claude-agent-sdk-python",
        "modelcontextprotocol/python-sdk", "modelcontextprotocol/typescript-sdk"]),
    "meta": ("Meta", [
        "meta-llama/llama-models", "meta-llama/llama-stack", "pytorch/pytorch",
        "facebook/react", "facebookresearch/faiss"]),
    "google": ("Google", ["googleapis/python-genai", "google/adk-python", "jax-ml/jax", "tensorflow/tensorflow"]),
    "microsoft": ("Microsoft", ["microsoft/semantic-kernel", "microsoft/autogen", "microsoft/vscode"]),
    "openai": ("OpenAI", ["openai/openai-python", "openai/openai-agents-python"]),
    "nvidia": ("NVIDIA", ["NVIDIA/NeMo", "NVIDIA/TensorRT-LLM"]),
    "community": ("Open-source ecosystem", ["huggingface/transformers", "langchain-ai/langgraph", "ollama/ollama", "vllm-project/vllm"]),
}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI-Developer-Docs-Hub"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def latest(repo, n=3):
    try:
        rel = [r for r in api(f"repos/{repo}/releases?per_page=10") if not r.get("draft")]
        if rel:
            return [{"tag": r["tag_name"], "date": (r.get("published_at") or "")[:10],
                     "url": r["html_url"], "pre": r.get("prerelease")} for r in rel[:n]]
        tags = api(f"repos/{repo}/tags?per_page={n}")
        return [{"tag": t["name"], "date": "", "url": f"https://github.com/{repo}/tree/{t['name']}", "pre": False} for t in tags]
    except Exception as exc:
        print(f"[skip] {repo}: {exc}", file=sys.stderr)
        return None


def block(repos, data):
    rows = ["| Project | Latest | Released | Earlier |", "|:--|:--|:--|:--|"]
    for repo in repos:
        rel = data.get(repo)
        if not rel:
            continue
        top = rel[0]
        pre = " 🧪" if top["pre"] else ""
        earlier = " · ".join(f"[{r['tag']}]({r['url']})" for r in rel[1:])
        rows.append(f"| [{repo}](https://github.com/{repo}) | [**{top['tag']}**]({top['url']}){pre} | {top['date'] or '—'} | {earlier or '—'} |")
    if len(rows) == 2:
        return "_Release data fills on the next daily run._\n"
    return "\n".join(rows) + f"\n\n<sub>Auto-updated {TODAY.isoformat()} from the GitHub API · 🧪 = pre-release</sub>\n"


def main():
    cache_path = os.path.join(ROOT, "data", "releases.json")
    data = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    if "--offline" not in sys.argv:
        for _, repos in TRACKED.values():
            for repo in repos:
                got = latest(repo)
                if got:
                    data[repo] = got
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        json.dump(data, open(cache_path, "w"), indent=1)

    out = ["# 🚀 Latest SDK & framework releases", "",
           "> The newest versions of the tools AI developers rely on — refreshed every morning (IST).", "",
           "[← Back to the hub](README.md)", ""]
    for key, (label, repos) in TRACKED.items():
        out += [f"## {label}", "", block(repos, data)]
    open(os.path.join(ROOT, "RELEASES.md"), "w", encoding="utf-8").write("\n".join(out))

    for key, (label, repos) in TRACKED.items():
        p = os.path.join(ROOT, key, "README.md")
        if not os.path.exists(p):
            continue
        s = open(p, encoding="utf-8").read()
        s = re.sub(r"<!-- releases:start -->.*?<!-- releases:end -->",
                   "<!-- releases:start -->\n" + block(repos, data) + "<!-- releases:end -->", s, flags=re.S)
        open(p, "w", encoding="utf-8").write(s)
    print("RELEASES.md written.")


if __name__ == "__main__":
    main()
