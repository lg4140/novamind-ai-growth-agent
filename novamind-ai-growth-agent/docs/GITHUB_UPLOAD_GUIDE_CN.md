# NovaMind V4 — GitHub 上传操作指南（中文）

## 上传之前

这个公开仓库来自 NovaMind V4，但**不是**完整版历史归档。已经移除旧版本 ZIP、Word 二进制报告、本地数据库、运行日志以及不适合公开发布的示例地址；只保留代码、Markdown 产品文档、可重现的测试和 `example.com` 演示联系人。

请保留 `.env.example`，不要上传你本机的 `.env`。本仓库的所有发送都只是本地模拟，没有真实营销发送能力。

## 方法 A：GitHub 网页上传（新手推荐）

1. 登录 https://github.com/new，新建名为 `novamind-ai-growth-agent` 的 Repository。
2. 如果准备把它作为公开作品集，选择 **Public**；否则先用 **Private** 复核。
3. 不要勾选 Initialize with README、Add .gitignore、Choose a license（包里已有 README 和忽略规则，授权由你以后决定）。
4. 在新仓库点击 **uploading an existing file**，或进入 **Add file → Upload files**。
5. **先解压**下载的 `novamind-ai-growth-agent-github-ready.zip`，把解压后仓库文件夹**里面的文件和目录**拖进 GitHub；不要直接上传 ZIP 一个文件。
6. 确认 GitHub 预览中包含 `app/`、`tests/`、`docs/`、`.github/workflows/ci.yml`、`README.md`、`.env.example` 和 `.gitignore`。若浏览器遗漏隐藏文件，请使用方法 B。
7. Commit message 填 `Initial public release: NovaMind AI Growth Agent V4`，提交到 `main`。
8. 打开仓库首页确认 README 正常显示，再查看 **Actions → CI** 是否绿色通过。

> GitHub 网页上传限制：一次最多 100 个文件，且单文件限制 25 MiB。本公开包小于这些限制；上传时务必保留目录层级。

## 方法 B：命令行上传（完整且最可靠）

先在 GitHub 新建一个**空仓库**（不要自动创建 README）。然后在解压后的 `novamind-ai-growth-agent` 目录运行：

```bash
python -m pip install -r requirements-test.txt
python scripts/public_release_check.py
python evals/run_offline_evals.py
python scripts/demo_offline.py

git init -b main
git add .
git status
git commit -m "Initial public release: NovaMind AI Growth Agent V4"
git remote add origin https://github.com/YOUR_USERNAME/novamind-ai-growth-agent.git
git push -u origin main
```

把 `YOUR_USERNAME` 替换成你的 GitHub 用户名。GitHub 可能要求你通过浏览器、SSH Key 或 Credential Manager 认证，而不是账户密码。

## 上传后推荐完善

- 仓库描述：`Evidence-aware, plan-first AI marketing copilot | Human approval · Agent planning · Python · SQLite · Streamlit`
- Topics：`ai-agents`, `ai-product-management`, `llm`, `marketing-automation`, `python`, `streamlit`, `human-in-the-loop`
- About 中暂时不要填写不存在的在线 Demo 链接。
- 需要开放源码复用时，再自行选择许可协议；本包没有替你决定 LICENSE。
- 提交前再次核对测试结果。`53 tests` 指确定性 Python 回归测试，不是 53 次真实大模型 Agent 测试；真实模型评测仍为 0/30。
