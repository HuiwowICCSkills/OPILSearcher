# OPILSearcher 部署指引

独立检索 Oxford Public International Law（OPIL）平台的 MPIL、ORIL 和 ORIL-ICL 产品。只访问 `opil.ouplaw.com`，不需要 `gdufs-auth-session`。

仓库：<https://github.com/HuiwowICCSkills/OPILSearcher>（公开仓库）。

## 1. 环境

| 组件 | 要求 |
| --- | --- |
| Python | 3.10+，依赖 `requests`、`beautifulsoup4`、`pypdf` |
| 网络 | 可访问 `opil.ouplaw.com` |
| 浏览器 | 不需要；平台用直接 HTTP + 会话 Cookie |

## 2. 安装

```powershell
git clone https://github.com/HuiwowICCSkills/OPILSearcher.git "$env:USERPROFILE\.codex\skills\OPILSearcher"
python -m pip install -r "$env:USERPROFILE\.codex\skills\OPILSearcher\requirements.txt"
```

## 3. 自检

```powershell
& "$env:USERPROFILE\.codex\skills\OPILSearcher\run.ps1" doctor
```

`doctor` 会分别探测 `mpil`、`oril`、`oril-icl` 三个产品；`ok: true` 表示至少一个产品可用。`--no-probe` 只检查依赖。

## 4. 使用

```powershell
$opil = "$env:USERPROFILE\.codex\skills\OPILSearcher\run.ps1"
& $opil search 'command responsibility' --product mpil --limit 10 --out './opil.json'
& $opil fetch 'https://opil.ouplaw.com/display/...' --out './entry.json' --text-out './entry.txt'
```

报告关键字段：`status`、`product`、`total`、`products_observed`、`results[].product`、`results[].core_issues`、`pagination.next_offset`、`evidence`。`fetch` 的 `text_characters` 用于判断是否只拿到 headnote。

## 5. 排错

| 现象 | 处理 |
| --- | --- |
| HTTP 403/405 或人工验证页 | 平台按 IP/频率拦截；稍后重试，或删除 `.opil-cache/opil.cookies.txt` 重新握手 |
| `Product filter not applied` | 分面参数没有生效；不要使用这次结果，检查 `--product` 和会话 Cookie |
| MPIL 结果混入 OSAIL/ORIL | 同上，通常是 `access=all&level=all` 未生效 |
| `fetch` 只有 1–2 千字符 | 可能是 ORIL headnote；读 `content_scope`，不要当完整报告 |

## 6. 边界

本 skill 只做 OPIL；判例全文、条约原文和其他来源请用对应的 `LegalToolsSearcher`、`ICJSearcher`、`ICRCSearcher`。OPIL 词条和 ORIL 报告是次级材料，引用时标注性质并回溯一手裁判。

## 实测效果（2026-11-09）

以下命令与结果来自本机 `~/.codex/skills/OPILSearcher` 的实网运行；检索日期 2026-11-09（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
& .\run.ps1 search 'command responsibility' --product mpil --limit 5
```

- 状态：`ok`；`product = mpil`；报告 `total = 154`；本次返回 5 条。
- 代表性结果：

| 题名 | 作者 | 类型 / 日期 | 链接 |
| --- | --- | --- | --- |
| Command Responsibility » | Yoram Dinstein† | Encyclopedia entries；—（API 未返回日期字段） | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e273?rskey=V6CyXK&result=1&prd=MPIL |
| Individual Criminal Responsibility » | Andreas Gordon O'Shea | Encyclopedia entries；—（API 未返回日期字段） | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e1852?rskey=V6CyXK&result=2&prd=MPIL |
| Blaškić Case » | Gideon Boas | Encyclopedia entries；—（API 未返回日期字段） | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e2076?rskey=V6CyXK&result=3&prd=MPIL |

> 说明：`total = 154` 是限定 MPIL 产品后的检索返回数，`products_observed` 仅含 "Max Planck Encyclopedias of International Law [MPIL]"。本 skill 的 `scope` 写明这些行是检索元数据而非词条正文：题名、作者、`content_type`、主题词与条目首段片段，`content_scope` 为“not the report text”。`access = entry page readable in this session` 只说明当次会话能打开条目页，不代表已抓到全文。MPIL 百科条目是次级材料，引用其观点前应回溯条目所援引的一手裁判与条约。
