# AGENTS.md - VS Code Copilot Agent 指引

此文件為 VS Code GitHub Copilot 的 Agent Mode 提供專案上下文。

---

## 專案規則

**藥品資訊 MCP Server v0.8.0** - 透過 Model Context Protocol 提供完整藥品功能。

### 當前版本狀態

| 指標 | 數值 |
|------|------|
| 版本 | v0.8.0 |
| MCP Tools | 19 個 |
| 測試數量 | 43 個 (全部通過) |
| 藥名對照 | 120+ 藥品 |
| 健保規則 | 60+ 藥品 |

### Python 環境規則

- **優先使用 uv** 管理套件和虛擬環境
- 專案使用 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

### MCP 開發規則

- 所有 Tool 定義在 `src/pharmacy_mcp/presentation/server.py`
- Tool 函數必須使用 type hints
- Tool 描述必須清楚說明參數和回傳值
- 台灣相關 Tools 使用 TaiwanDrugService

### 測試規則

- 測試放在 `tests/` 目錄
- API 測試必須使用 Mock
- 執行測試: `uv run pytest tests/ -v`

---

## 可用 MCP Tools (19 個)

### 基礎功能 (13 個)
- `search_drug` - 藥品搜尋
- `get_drug_info` - 藥品資訊（含台灣資訊）
- `get_drug_dosage` - 劑量資訊
- `get_drug_warnings` - 警告資訊
- `check_drug_interaction` - 藥物交互作用
- `check_multi_drug_interactions` - 多藥物交互作用
- `check_food_drug_interaction` - 食品藥物交互
- `calculate_dose_by_weight` - 體重劑量計算
- `calculate_dose_by_bsa` - BSA 劑量計算
- `calculate_creatinine_clearance` - 腎功能計算
- `calculate_pediatric_dose` - 小兒劑量
- `calculate_infusion_rate` - 輸液速率
- `convert_dose_units` - 劑量單位轉換

### 台灣功能 (6 個) 🇹🇼
- `search_tfda_drug` - TFDA 藥品查詢
- `get_nhi_coverage` - 健保給付查詢
- `get_nhi_drug_price` - 健保藥價查詢
- `translate_drug_name` - 中英藥名對照
- `list_prior_authorization_drugs` - 事前審查清單
- `list_nhi_coverage_rules` - 健保給付規則

---

## 💸 Memory Checkpoint 規則

在以下情況使用 checkpoint：
1. 完成一個功能模組
2. 重要 API 整合完成
3. 長時間工作中斷前
4. 版本發布前

---

## 回應風格

- 繁體中文優先
- 程式碼註解用英文
- 遵循 PEP 8 風格
- 使用 type hints

---

*Updated: 2025-12-22 (v0.8.0)*
