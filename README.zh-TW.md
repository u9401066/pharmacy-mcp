# Pharmacy MCP Server

Pharmacy MCP 是一個 Python MCP server，用於藥品參考工作流程。它整合藥品查詢、仿單摘要、劑量計算、台灣 TFDA/NHI 查詢、院內醫囑輔助，以及可信任 PK/DDI 公式庫的 PBPK-lite 教育用模擬。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.27+-green.svg)](https://modelcontextprotocol.io/)

English: [README.md](README.md)

## 0.9.1 更新

- 互動作用輸出改為非指令式 `management_consideration`，並保留安全聲明。
- 模擬服務對 NaN、Infinity、不穩定分母與 catalog drift 採 fail-closed。
- 新增 release artifact audit 與 wheel install smoke test。
- Streamable HTTP ASGI app 改為 lazy、支援 mount path，並避免 `--help` 產生 runtime cache。

## 安裝

```bash
git clone https://github.com/u9401066/pharmacy-mcp.git
cd pharmacy-mcp
uv sync --all-extras
```

## 執行

```bash
uv run pharmacy-mcp
uv run pharmacy-mcp --transport stdio
uv run pharmacy-mcp --transport streamable-http --host 0.0.0.0 --port 8000
uv run uvicorn pharmacy_mcp.presentation.server:app --host 0.0.0.0 --port 8000
```

環境變數使用 `PHARMACY_MCP_` 前綴，例如 `PHARMACY_MCP_TRANSPORT`,
`PHARMACY_MCP_HOST`, `PHARMACY_MCP_PORT`, `PHARMACY_MCP_MOUNT_PATH`,
`PHARMACY_MCP_STREAMABLE_HTTP_PATH`, `PHARMACY_MCP_STATELESS_HTTP`。

## 主要 MCP Tools

- 藥品參考：`search_drug`, `get_drug_info`, `get_drug_dosage`, `get_drug_warnings`
- 互動作用：`check_drug_interaction`, `check_multi_drug_interactions`, `check_food_drug_interaction`
- 劑量計算：`calculate_dose_by_weight`, `calculate_dose_by_bsa`, `calculate_creatinine_clearance`, `calculate_pediatric_dose`, `calculate_infusion_rate`, `convert_dose_units`
- 台灣資料：`search_tfda_drug`, `get_nhi_coverage`, `get_nhi_drug_price`, `translate_drug_name`, `list_prior_authorization_drugs`, `list_nhi_coverage_rules`
- 院內流程：`get_formulary_item`, `search_formulary`, `get_renal_adjustment`, `validate_order`, `submit_order`, `stop_order`
- 公式與模擬：`list_formula_catalog`, `get_formula_details`, `explain_interaction_mechanism`, `simulate_pk_interaction`, `simulate_concentration_time`

## 可信任公式模型

公式 metadata 以資料形式提交，不執行任意 runtime 表達式。每個可信任公式都包含 ID、表達式、參數、單位、假設、限制、參考來源與 validation cases。Python simulation service 只依已審核的 formula ID dispatch 到對應實作。

NSForge 可作為外部公式撰寫輔助，但 Pharmacy MCP 0.9.x 不 vendor NSForge，也不直接執行外部 MCP 產生的未審核公式。

## 驗證

```bash
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests scripts
uv run mypy src
uv run bandit -q -r src
uv build
uv run python scripts/audit_release_artifacts.py dist
```

## 免責聲明

本專案僅供參考、教育與工作流程輔助，不構成醫療建議，也不得作為臨床決策的唯一依據。照護病人時請依合格醫療專業人員、最新仿單、院內規範與已驗證臨床系統判斷。

## License

Apache-2.0
