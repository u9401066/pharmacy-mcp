# 💊 Pharmacy MCP Server

> 完整藥品資訊 MCP Server - 藥品查詢、資訊取得、劑量計算、交互作用檢查、食品藥品衝突

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)

🌐 [繁體中文](README.zh-TW.md)

## ✨ Features

- 🔍 **Drug Search** - 藥品名稱、ATC 碼、適應症搜尋
- 📋 **Drug Information** - 完整藥品資訊、仿單、藥理學
- 🧮 **Dosage Calculator** - 小兒、腎功能、體重劑量計算
- ⚠️ **Interaction Checker** - 藥物-藥物交互作用檢查
- 🍎 **Food-Drug Interactions** - 食品、酒精、保健品衝突
- 🇹🇼 **Taiwan NHI Integration** - 台灣健保給付、TFDA 藥品、中英藥名對照

## 📦 Data Sources

| Source | Provider | Data Type |
|--------|----------|-----------|
| [RxNorm API](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html) | NIH/NLM | Drug naming, concepts |
| [openFDA](https://open.fda.gov/apis/) | FDA | Adverse events, labels |
| [DailyMed](https://dailymed.nlm.nih.gov/dailymed/) | NLM | Drug labels |
| [RxClass](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxClassAPIs.html) | NIH/NLM | Drug classification || [TFDA Open Data](https://data.fda.gov.tw/) | 台灣 TFDA | Taiwan drug permits |
| [NHI Open Data](https://data.nhi.gov.tw/) | 台灣健保署 | NHI coverage, pricing |
## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/pharmacy-mcp.git
cd pharmacy-mcp

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install dependencies
uv sync --all-extras
```

### Running the Server

```bash
# Run MCP over stdio (default, for Claude Desktop and local MCP clients)
pharmacy-mcp

# Or with Python
python -m pharmacy_mcp
```

### Streamable HTTP Deployment

```bash
# Run the new Streamable HTTP transport locally
pharmacy-mcp --transport streamable-http --host 0.0.0.0 --port 8000

# Serve the ASGI app with uvicorn
uv run uvicorn pharmacy_mcp.presentation.server:app --host 0.0.0.0 --port 8000
```

Environment variables are also supported via the `PHARMACY_MCP_` prefix, including
`MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`, `MCP_MOUNT_PATH`, `MCP_STREAMABLE_HTTP_PATH`,
and `MCP_STATELESS_HTTP`.

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

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

## 🛠️ Available Tools

### Drug Search
| Tool | Description |
|------|-------------|
| `search_drug_by_name` | Search drugs by name |
| `search_drug_by_atc` | Search by ATC code |
| `search_drug_by_indication` | Search by indication |
| `get_drug_alternatives` | Get therapeutic alternatives |

### Drug Information
| Tool | Description |
|------|-------------|
| `get_drug_details` | Complete drug information |
| `get_drug_label` | FDA-approved labeling |
| `get_pharmacokinetics` | PK/PD information |
| `get_contraindications` | Contraindications list |
| `get_side_effects` | Adverse reactions |

### Dosage Calculator
| Tool | Description |
|------|-------------|
| `calculate_pediatric_dose` | Pediatric dosing |
| `calculate_renal_dose` | Renal adjustment |
| `calculate_weight_dose` | Weight-based dosing |
| `calculate_bsa_dose` | BSA-based dosing |

### Interaction Checker
| Tool | Description |
|------|-------------|
| `check_drug_interaction` | Check two drugs |
| `check_multiple_drugs` | Check drug list |
| `get_interaction_severity` | Get severity level |
| `get_interaction_mechanism` | Get mechanism |

### Food-Drug Interactions
| Tool | Description |
|------|-------------|
| `check_food_interaction` | Food-drug interaction |
| `check_alcohol_interaction` | Alcohol interaction |
| `check_supplement_interaction` | Supplement interaction |
| `get_dietary_restrictions` | Dietary restrictions |

### Taiwan NHI Integration 🇹🇼
| Tool | Description |
|------|-------------|
| `search_tfda_drug` | Search Taiwan TFDA drug database |
| `get_nhi_coverage` | Check NHI coverage status |
| `get_nhi_drug_price` | Get NHI reimbursement price |
| `translate_drug_name` | Translate drug names (EN↔TW) |
| `list_prior_authorization_drugs` | List drugs requiring prior auth |
| `list_nhi_coverage_rules` | List NHI coverage rules |

## 🏗️ Architecture

```
src/pharmacy_mcp/
├── domain/              # Core domain models
│   ├── entities/        # Drug, Interaction entities
│   └── value_objects/   # Dosage, Severity
├── application/         # Use cases
│   ├── search/          # Search services
│   ├── info/            # Information services
│   ├── dosage/          # Dosage calculators
│   └── interaction/     # Interaction checkers
├── infrastructure/      # External services
│   ├── api/             # API clients (RxNorm, FDA)
│   └── cache/           # Caching layer
└── presentation/        # MCP Tools
    └── tools/           # Tool definitions
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run focused server tests
uv run pytest tests/test_server.py -v

# Static analysis (repository currently has pre-existing ruff/mypy issues)
uv run ruff check src tests
uv run mypy src
```

## ⚠️ Disclaimer

> **This information is for reference only and does not constitute medical advice. Please consult a healthcare professional.**

## 📄 License

[Apache License 2.0](LICENSE)

---

*Built with ❤️ for healthcare professionals and developers*
