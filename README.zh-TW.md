# Pharmacy MCP Server

Pharmacy MCP 是一個 Python MCP server，提供藥物查詢、標籤摘要、劑量計算、
台灣 TFDA/NHI 查詢、院內處方輔助，以及 0.9.0 新增的可信任 PK/DDI
公式庫與 PBPK-lite 模擬工具。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.27+-green.svg)](https://modelcontextprotocol.io/)

English: [README.md](README.md)

## 0.9.0 重點

- 內建可信任 PK/DDI 公式庫：`src/pharmacy_mcp/data/formulas/`。
- 可重現的模擬服務：單室模型濃度、重複給藥累積、腎清除率調整、CYP 可逆抑制、AUC ratio、溫度校正消除速率。
- 對支援的 CYP 抑制案例提供機轉解釋與暴露量估算，例如 warfarin/fluconazole、statin/clarithromycin。
- 現代 MCP 介面：tools、read-only resources、resource templates、prompts、Streamable HTTP、structured output。
- 發布驗證：pytest coverage、ruff、mypy、bandit、wheel build。

模擬輸出只作為篩檢與教育估算，不是臨床處置建議。所有模擬輸出都會包含
專案 disclaimer 與 `not_for_direct_clinical_decision: true`。

## 安裝

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
```

## 執行

```bash
# 給本機 MCP client 使用的 stdio transport
uv run pharmacy-mcp

# 明確指定 stdio
uv run pharmacy-mcp --transport stdio

# Streamable HTTP
uv run pharmacy-mcp --transport streamable-http --host 0.0.0.0 --port 8000

# ASGI app
uv run uvicorn pharmacy_mcp.presentation.server:app --host 0.0.0.0 --port 8000
```

環境變數使用 `PHARMACY_MCP_` 前綴，例如 `MCP_TRANSPORT`、`MCP_HOST`、
`MCP_PORT`、`MCP_MOUNT_PATH`、`MCP_STREAMABLE_HTTP_PATH`、
`MCP_STATELESS_HTTP`。

## Claude Desktop 設定範例

```json
{
  "mcpServers": {
    "pharmacy": {
      "command": "uv",
      "args": ["run", "pharmacy-mcp", "--transport", "stdio"],
      "cwd": "/path/to/pharmacy-mcp"
    }
  }
}
```

## MCP Tools

藥物資料：

- `search_drug`
- `get_drug_info`
- `get_drug_dosage`
- `get_drug_warnings`
- `check_drug_interaction`
- `check_multi_drug_interactions`
- `check_food_drug_interaction`

劑量計算：

- `calculate_dose_by_weight`
- `calculate_dose_by_bsa`
- `calculate_creatinine_clearance`
- `calculate_pediatric_dose`
- `calculate_infusion_rate`
- `convert_dose_units`

台灣 TFDA/NHI：

- `search_tfda_drug`
- `get_nhi_coverage`
- `get_nhi_drug_price`
- `translate_drug_name`
- `list_prior_authorization_drugs`
- `list_nhi_coverage_rules`

院內處方流程：

- `get_formulary_item`
- `search_formulary`
- `get_renal_adjustment`
- `validate_order`
- `submit_order`
- `stop_order`

可信公式與模擬：

- `list_formula_catalog`
- `get_formula_details`
- `explain_interaction_mechanism`
- `simulate_pk_interaction`
- `simulate_concentration_time`

## MCP Resources 與 Prompts

Resources：

- `pharmacy://server/disclaimer`
- `pharmacy://formulas`
- `pharmacy://formulas/{formula_id}`
- `pharmacy://validation/formulas`

Prompts：

- `ddi_analysis_workflow`
- `formula_review_checklist`

## Trusted Formula 模型

公式庫採資料優先設計，公式 metadata 會被提交到 repo，但不執行任意 runtime
程式碼。每個可信公式都有 ID、expression、參數、單位、假設、限制、參考來源、
驗證案例。實際運算由 Python simulation service 依公式 ID dispatch 到已審核的實作。

NSForge 這類外部公式產生器可以當作 companion authoring tool，但 0.9.0
不把 NSForge vendoring 或 submodule 化。任何外部生成公式都必須先經人工審核、
提交到 trusted catalog、補上測試，才能被 production simulation tools 使用。

## 資料來源

| 來源 | 提供者 | 資料 |
| --- | --- | --- |
| RxNorm API | NIH/NLM | 藥名與概念 |
| openFDA | FDA | 藥品標籤與警語 |
| DailyMed | NLM | 標籤段落 |
| TFDA Open Data | 台灣 TFDA | 藥品許可與藥名 |
| NHI Open Data | 台灣健保署 | 給付規則與價格 |
| Local catalog | Pharmacy MCP | 可信 PK/DDI 公式與院內 mock data |

## 架構

```text
src/pharmacy_mcp/
  domain/                  Entity 與 value object
  application/services/    Use-case service 與 simulation orchestration
  infrastructure/api/      外部 API clients
  infrastructure/cache/    Disk cache adapter
  infrastructure/knowledge/Local formulary 與 trusted formula catalog
  presentation/            FastMCP server、tools、resources、prompts
```

## 驗證

```bash
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run mypy src
uv run bandit -q -r src
uv build
```

## Disclaimer

本專案只提供參考、教育與工作流程輔助，不提供醫療建議，也不能作為臨床決策的唯一依據。
臨床照護請以合格醫療人員與已驗證臨床系統為準。

## 授權

[Apache License 2.0](LICENSE)
