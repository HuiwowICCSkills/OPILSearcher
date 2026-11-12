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

## 实测效果（2026-11-12）

以下命令与结果来自本机 `~/.codex/skills/OPILSearcher` 的实网运行；检索日期 2026-11-12（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
$opil = "$env:USERPROFILE\.codex\skills\OPILSearcher\run.ps1"
& $opil search 'command responsibility' --product mpil --year-from 2010 --year-to 2015 --limit 5
```

- 状态：`ok`；`total = 59`；本次返回 5 条；`products_observed` 只含 `Max Planck Encyclopedias of International Law [MPIL]`。
- 高级过滤：`fromDate=2010`、`toDate=2015`；它们限制出版日期，不改变 MPIL 产品分面。
- 代表性结果：

| 题名 | 产品 / 类型 | 链接 |
| --- | --- | --- |
| Command Responsibility » | MPIL / Encyclopedia entries | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e273?rskey=zSWZve&result=1&prd=MPIL |
| Blaškić Case » | MPIL / Encyclopedia entries | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e2076?rskey=zSWZve&result=2&prd=MPIL |
| International Organizations or Institutions, Responsibility and Liability » | MPIL / Encyclopedia entries | https://opil.ouplaw.com/display/10.1093/law:epil/9780199231690/law-9780199231690-e509?rskey=zSWZve&result=3&prd=MPIL |

> 说明：OPIL 搜索行是**检索元数据**（题名、引证头、作者、主题词等），不是词条或报告正文；`fetch` 后的 `text_characters` 才能说明实际取得多少正文。MPIL 词条和 ORIL 报告都是次级材料，引用时仍需回溯一手裁判。
