# Pharmacy MCP 藥品知識閘道

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-00695C.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-00897B.svg)](https://u9401066.github.io/pharmacy-mcp/)

這是一個 **MCP server + agent harness**，把公共藥品 API、台灣 TFDA/NHI、
醫院 FHIR/庫存、院內資料庫、向量搜尋、檔案、固定 Web 文件與可信任
PK/DDI 模擬整合成一個可追溯的藥品查詢入口。

[English](README.md) · [說明網站](https://u9401066.github.io/pharmacy-mcp/) · [架構](ARCHITECTURE.md)

> 目前為 1.0 prerelease。所有內容只供參考，不構成醫療建議，也不能取代藥師、醫師或
> 經驗證的臨床決策支援系統。

## 為什麼需要這個入口

- **Agent 只需一個入口：** `query_pharmacy` 依 capability 或明確來源路由，
  並隔離 provider timeout 和錯誤。
- **輸出可以被穩定解析：** 所有 MCP tools 共用 `QueryResponse` v1.0 JSON
  Schema；文字可選 `json`、`json_compact` 或 `markdown`，但
  `structuredContent` 永遠是唯一真實來源。
- **直接約束 Agent：** 每個 tool 都附 forwarding 規則，MCP client 也能載入
  `pharmacy-query-contract` prompt。
- **複合結果仍可追溯：** provider payload、來源、警告與錯誤分開保留；某一
  來源失敗時，其餘成功資料以 `partial` 回傳。
- **預設能接醫院：** FHIR 只讀；file/SQL/vector/web 都由管理者設定邊界，
  agent 不能自行指定路徑、SQL、endpoint 或 URL。
- **主動偵測來源漂移：** 每週排程檢查 14 個官方 API/資料集入口，且不下載
  台灣的大型資料檔。
- **FastMCP 可部署：** 本機可用 stdio，也可把同一份工具目錄掛載成
  SSE/Streamable HTTP；service 與 ASGI app 都採 lazy initialization。
- **可稽核模擬：** 可信任公式包含單位、假設、限制、來源、驗證案例與
  fail-closed 數值檢查。

## 快速開始

需要 Python 3.11+ 與 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
uv run pharmacy-mcp
```

Streamable HTTP 與 ASGI 仍使用相同工具及輸出契約：

```bash
uv run pharmacy-mcp --transport streamable-http --host 127.0.0.1 --port 8000
uvicorn pharmacy_mcp.presentation.server:app --host 127.0.0.1 --port 8000
```

MCP client 設定：

```json
{
  "mcpServers": {
    "pharmacy": {
      "command": "uv",
      "args": ["run", "pharmacy-mcp"],
      "cwd": "/absolute/path/to/pharmacy-mcp"
    }
  }
}
```

建議查詢：

```json
{
  "query": "warfarin",
  "capabilities": ["identity", "label", "reimbursement", "formulary"],
  "sources": ["rxnorm", "dailymed", "tw-tfda", "tw-nhi", "local-formulary"],
  "limit": 10,
  "output_format": "json_compact",
  "locale": "zh-TW"
}
```

非 MCP workflow 可以使用同一份契約：

```bash
uv run pharmacy-query warfarin \
  --source local-formulary \
  --capability formulary \
  --format json_compact
```

Python 可直接匯入 `pharmacy_mcp.application.harness.PharmacyHarness`。

## 已整合的知識

| 範圍 | 隨附 adapters |
|---|---|
| 公共藥品知識 | RxNorm/RxClass、openFDA 全七個藥品端點、DailyMed、PubChem、MedlinePlus Connect |
| 台灣 | TFDA 許可證、健保署官方每月藥品項目、給付規則、藥名對照 |
| 醫院 | FHIR R4/R5 藥品、醫囑、調劑、庫存/供應，以及 bundled formulary |
| 組織資料 | PDF、DOC/DOCX、CSV、XLS/XLSX、Markdown、text、唯讀 SQLite、vector gateway、固定 HTTPS 文件 |
| PK/DDI 模擬 | 可信任公式 catalog、濃度時間估算、機轉式 CYP 抑制 screening、公式 resources 與驗證 fixtures |
| 商業資料 catalog | DrugBank、FDB、Micromedex；沒有授權時不抓取也不假裝啟用 |

`list_knowledge_sources` 是 runtime 真實狀態：會列出 capability、實作狀態、
credential 需求與 adapter 是否已註冊。完整內容見[資料來源總覽](docs/data-sources.md)。

## 台灣健保與院內設定

NHI provider 會按需下載官方月 CSV，再以 atomic replace 建立版本化 SQLite
索引。同一查詢可合併健保碼、支付價、ATC、有效日期、TFDA 與給付規則。詳見
[台灣健保複合查詢](docs/taiwan-nhi.md)。

設定 `PHARMACY_MCP_FHIR_BASE_URL` 後才會註冊醫院 adapter。Bearer token 由
`SecretStr` 設定讀取；只有授權呼叫方明確傳入 `context.patient_id` 時才會查
病人資源。院內資料連接器也採同樣的 allowlist 原則。請從 [.env.example](.env.example)、
[FHIR 與庫存](docs/fhir.md)及[組織資料連接器](docs/connectors.md)開始。

## 輸出與 Agent 規則

固定的 top-level fields：

```text
schema_version · status · data · sources · warnings · errors · meta
```

未知欄位會被拒絕。目前 33 個工具（包含計算與模擬）全部使用這份 envelope。
Agent 必須保留七個欄位、不得自行補足缺失的臨床事實，
也不得把多來源扁平化成一個虛構的權威來源。詳見 [Agent harness](docs/agent-harness.md)
與 [response contract](docs/architecture/response-contract.md)。

## 開發

```bash
uv sync --all-extras
uv run pytest
uv run ruff check src tests examples scripts
uv run mypy src
uv run mkdocs build --strict
uv run python scripts/check_source_health.py
```

本 repo 使用分段 Conventional Commits、持續更新 Memory Bank、多 Python 版本
CI、每週公共來源健康檢查和 GitHub Pages 文件部署。詳見
[CONTRIBUTING.md](CONTRIBUTING.md) 與
[SECURITY.md](SECURITY.md)。

## 授權

程式碼採 Apache License 2.0。外部資料集與商業知識庫仍各自適用其授權、
attribution 與臨床使用限制。
