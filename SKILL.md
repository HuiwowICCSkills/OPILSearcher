---
name: OPILSearcher
description: 独立检索 Oxford Public International Law（OPIL）平台，覆盖 Max Planck 国际法百科全书（MPIL）、Oxford Reports on International Law（ORIL）及其国际刑法分册（ORIL-ICL）；返回检索元数据、编者 Core Issue(s)，并可读取条目页正文。
---

# OPILSearcher

> **`<skill-dir>`** = 本 SKILL.md 所在目录。核心脚本为 `<skill-dir>/scripts/opil_search.py`；Windows 用 `<skill-dir>/run.ps1`，macOS/Linux 用 `<skill-dir>/run.sh`。部署与排错见 [README.md](README.md)。

这个 skill 只做 `opil.ouplaw.com` 一个平台，按三个产品档案检索：

| `--product` | 产品 | 分面 |
| --- | --- | --- |
| `mpil` | Max Planck Encyclopedia of Public International Law | `prd=MPEIPRO` + `access=all&level=all` |
| `oril` | Oxford Reports on International Law 全产品 | `pc_17=bdcb8d33-0914-4cd9-bd2b-c84ac21665f7` |
| `oril-icl` | ORIL 国际刑法分册 | `pc_32=68306099-6983-4cb7-a931-60f851434432` |

平台对通用研究 UA 返回 403，且首次请求要走一次 OIDC/重定向握手；适配器会先用浏览器式 UA 完成握手并把会话 Cookie 存到缓存目录。MPIL 与 ORIL 的分面参数是**相反**的：MPIL 必须带 `access=all&level=all`，ORIL 的 `pc_*` 分面不能带 `access=all`，否则服务端会静默缩小结果。适配器会校验返回的 Product 字段，不匹配时报错，不返回“看起来成功”的错结果。

## 命令

```powershell
# MPIL 百科检索
& '<skill-dir>/run.ps1' search 'command responsibility' --product mpil --limit 10 --out './opil-mpil.json'

# 按出版年份收窄（站点 Advanced Search 的 publication-date range）
& '<skill-dir>/run.ps1' search 'command responsibility' --product mpil --year-from 2010 --year-to 2015 --limit 10

# ORIL 全产品
& '<skill-dir>/run.ps1' search 'state immunity' --product oril --limit 10 --out './opil-oril.json'

# ORIL 国际刑法分册
& '<skill-dir>/run.ps1' search 'genocide' --product oril-icl --limit 10 --out './opil-oril-icl.json'

# 读取条目页正文（用 search 返回的 URL）
& '<skill-dir>/run.ps1' fetch 'https://opil.ouplaw.com/display/...' --out './opil-entry.json' --text-out './opil-entry.txt'

# 部署自检
& '<skill-dir>/run.ps1' doctor
```

通用参数：`--out`、`--cache`、`--cache-ttl`、`--offline`、`--timeout`。`search` 另有 `--product`、`--limit`（1..50）、`--offset`；`fetch` 另有 `--text-out`、`--max-mb`。

## 结果边界

- `search` 返回的是**检索元数据**：题名、引证头、日期、管辖、主题词和编者 `Core Issue(s)`，不是报告或词条正文。需要正文时对返回的 `url` 运行 `fetch`。
- `fetch` 的 `content_scope` 会说明实际取得的是百科词条正文、报告 headnote，还是完整裁判文本；MPIL 已转为 Subscribe-to-Open，多数词条页可读；ORIL 是订阅产品，匿名多数报告页只有 1,333–2,266 字符的 headnote，少数条目可能返回完整判决文本。务必读 `text_characters`，不要把 headnote 当完整报告。
- `products_observed` 是本次结果行实际出现的 Product 字段；如果 MPIL 检索出现 OSAIL/ORIL 混入，说明分面没有生效，适配器会报错而不是静默返回。
- `total` 是平台在产品分面下报告的总命中数，不等于本机已取得全文的数量。
- `--year-from`/`--year-to` 映射到 OPIL 搜索页的 `fromDate`/`toDate`（四位年份），只限制出版日期；它们不改变产品分面。不要把年份范围当作法律事实发生时间。
- 单次 403/405 只是该请求被平台或人工验证页拦截，不等于没有资料；不要对同一请求反复重试。`doctor` 会分别探测三个产品。
- OPIL 的百科词条和 ORIL 报告都是次级材料或评注；输出时应标注其性质，并把其中的判例线索回溯到一手裁判全文。

## 参考

- 2026-11-09 实测：三个产品的分面、总数、Product 校验和会话握手：[references/opil-search.md](references/opil-search.md)
- 部署、环境与排错：[README.md](README.md)
