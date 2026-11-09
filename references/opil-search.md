# OPIL 检索实测记录（2026-11-09）

## 平台与端点

- 搜索页：`https://opil.ouplaw.com/search`
- 首页/握手：`https://opil.ouplaw.com/`，产品页 `https://opil.ouplaw.com/home/MPIL`、`/home/ORIL`
- 请求头：浏览器式 `User-Agent`（Chrome/155）、`Accept: text/html,application/xhtml+xml,application/json`
- 会话：`requests.Session` + `LWPCookieJar`，缓存为 `<cache>/opil.cookies.txt`；同一主机请求间隔 2 秒

## 产品分面

| 产品 | 参数 | 2026-11-09 `command responsibility` 总数 |
| --- | --- | --- |
| MPIL | `prd=MPEIPRO&access=all&level=all` | 154 |
| ORIL | `pc_17=bdcb8d33-0914-4cd9-bd2b-c84ac21665f7` | 1,012 |
| ORIL-ICL | `pc_32=68306099-6983-4cb7-a931-60f851434432` | 365 |

## 解析

- 结果块：`div.contentItem`
- 标题：`h2.itemTitle a[href]`
- 元数据：`dl.metadata` 中的 `dt`/`dd`，字段包括 `Product`、`Module`、`Content type`、`Date`、`Jurisdiction`、`Subject(s)`、`Core Issue(s)`
- 总数文本：`You are looking at 1–20 of 154 results`
- 访问状态：结果块 class `hasAccess` / `locked`
- 产品校验：结果行的 `Product` 必须包含所声明产品的 expected 名称；MPIL 混入 OSAIL/ORIL 时说明分面未生效，应报错

## 已验证行为

- `command responsibility --product mpil --limit 3` → `status=ok`、`total=154`、`products_observed=[MPIL]`
- `command responsibility --product oril --limit 1` → `total=1012`
- `command responsibility --product oril-icl --limit 1` → `total=365`
- `fetch` 一个 MPIL 词条 URL → `text_characters=20384`
- 未先访问首页/产品页直接搜索时，产品分面可能不生效；适配器会先 `_warm()` 再检索

## 已知限制

- ORIL 是订阅产品，匿名多数报告页只有 headnote（约 1,333–2,266 字符）；MPIL 自 2024 年起 Subscribe-to-Open，多数词条正文可读。
- 同一主机连续请求过密会触发 HTTP 405 人工验证页；适配器固定 2 秒间隔。
- 结果页只给出检索元数据，不保证正文可读；`fetch` 后必须读 `text_characters`。
