# 💊 藥品資訊 MCP Server

> 完整藥品資訊 MCP Server - 藥品查詢、資訊取得、劑量計算、交互作用檢查、食品藥品衝突

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)

🌐 [English](README.md)

## ✨ 功能特色

- 🔍 **藥品查詢** - 依名稱、ATC 碼、適應症搜尋
- 📋 **藥品資訊** - 完整藥品資訊、仿單、藥理學資料
- 🧮 **劑量計算** - 小兒劑量、腎功能調整、體重劑量
- ⚠️ **交互作用** - 藥物-藥物交互作用檢查
- 🍎 **食品衝突** - 食品、酒精、保健品與藥物衝突

## 📦 資料來源

| 來源 | 提供者 | 資料類型 |
|------|--------|----------|
| [RxNorm API](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html) | NIH/NLM | 藥品命名標準化 |
| [openFDA](https://open.fda.gov/apis/) | FDA | 不良反應、藥品標籤 |
| [DailyMed](https://dailymed.nlm.nih.gov/dailymed/) | NLM | 藥品仿單 |
| [RxClass](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxClassAPIs.html) | NIH/NLM | 藥品分類 |

## 🚀 快速開始

### 安裝

```bash
# Clone 專案
git clone https://github.com/your-org/pharmacy-mcp.git
cd pharmacy-mcp

# 使用 uv 建立虛擬環境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安裝依賴
uv sync --all-extras
```

### 執行伺服器

```bash
# 執行 MCP server
pharmacy-mcp

# 或使用 Python
python -m pharmacy_mcp.server
```

### Claude Desktop 設定

將以下內容加入 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "pharmacy": {
      "command": "uv",
      "args": ["run", "pharmacy-mcp"],
      "cwd": "/path/to/pharmacy-mcp"
    }
  }
}
```

## 🛠️ 可用工具

### 藥品查詢
| 工具 | 說明 |
|------|------|
| `search_drug_by_name` | 依名稱搜尋藥品 |
| `search_drug_by_atc` | 依 ATC 碼搜尋 |
| `search_drug_by_indication` | 依適應症搜尋 |
| `get_drug_alternatives` | 取得替代藥品 |

### 藥品資訊
| 工具 | 說明 |
|------|------|
| `get_drug_details` | 完整藥品資訊 |
| `get_drug_label` | FDA 核准標籤 |
| `get_pharmacokinetics` | 藥物動力學資訊 |
| `get_contraindications` | 禁忌症清單 |
| `get_side_effects` | 不良反應 |

### 劑量計算
| 工具 | 說明 |
|------|------|
| `calculate_pediatric_dose` | 小兒劑量計算 |
| `calculate_renal_dose` | 腎功能調整劑量 |
| `calculate_weight_dose` | 體重劑量計算 |
| `calculate_bsa_dose` | 體表面積劑量 |

### 交互作用檢查
| 工具 | 說明 |
|------|------|
| `check_drug_interaction` | 檢查兩藥物交互 |
| `check_multiple_drugs` | 多重藥物檢查 |
| `get_interaction_severity` | 取得嚴重等級 |
| `get_interaction_mechanism` | 取得機轉說明 |

### 食品藥品衝突
| 工具 | 說明 |
|------|------|
| `check_food_interaction` | 食品藥物交互 |
| `check_alcohol_interaction` | 酒精交互作用 |
| `check_supplement_interaction` | 保健品交互作用 |
| `get_dietary_restrictions` | 飲食限制建議 |

## 🏗️ 專案架構

```
src/pharmacy_mcp/
├── domain/              # 核心領域
│   ├── entities/        # 藥品、交互作用實體
│   └── value_objects/   # 劑量、嚴重等級
├── application/         # 應用層
│   ├── search/          # 搜尋服務
│   ├── info/            # 資訊服務
│   ├── dosage/          # 劑量計算器
│   └── interaction/     # 交互作用檢查器
├── infrastructure/      # 基礎設施
│   ├── api/             # API 客戶端 (RxNorm, FDA)
│   └── cache/           # 快取層
└── presentation/        # 呈現層
    └── tools/           # MCP Tool 定義
```

## 🧪 測試

```bash
# 執行所有測試
pytest

# 含覆蓋率報告
pytest --cov=src --cov-report=html

# 只執行單元測試
pytest -m unit

# 靜態分析
ruff check src tests
mypy src
```

## ⚠️ 免責聲明

> **本資訊僅供參考，不構成醫療建議。請諮詢專業醫療人員。**

## 📄 授權

[Apache License 2.0](LICENSE)

---

*為醫療專業人員和開發者用心打造 ❤️*
