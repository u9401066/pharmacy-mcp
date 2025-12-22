# Active Context

## 🎯 當前焦點

- v0.8.0 台灣健保整合完成 ✅
- 準備 v0.9.0 Agent 增強功能

## 📝 最近完成的變更（v0.8.0）

| 檔案 | 變更內容 |
|------|----------|
| `infrastructure/api/tfda.py` | 新增 TFDA API Client + 120+ 藥名對照 |
| `infrastructure/api/nhi.py` | 新增 NHI Client + 60+ 健保給付規則 |
| `application/services/taiwan_drug.py` | 新增 TaiwanDrugService |
| `application/services/drug_info.py` | 整合台灣藥品資訊 |
| `presentation/server.py` | 新增 6 個台灣藥品 MCP Tools |
| `tests/test_taiwan_api.py` | 新增 20 個測試 |

## ✅ v0.8.0 新增功能

### MCP Tools（19 個，+6）
- `search_tfda_drug` - 搜尋台灣 TFDA 藥品
- `get_nhi_coverage` - 查詢健保給付
- `get_nhi_drug_price` - 查詢健保藥價
- `translate_drug_name` - 中英藥名對照
- `list_prior_authorization_drugs` - 事前審查藥品清單
- `list_nhi_coverage_rules` - 健保給付規則

### 資料庫
- 藥名對照表：120+ 常用藥品（16 類別）
- 健保給付規則：60+ 藥品（11 類別）

## ⚠️ 已知限制

- RxNorm Drug Interaction API 已停用（使用本地資料庫）
- TFDA 開放資料需下載完整 JSON（首次查詢較慢）
- 健保給付規則為手動維護（非即時同步）

## 💡 重要決定

- 台灣藥品資料不需自建資料庫，使用政府開放資料 + disk cache
- 健保給付規則使用本地資料庫（因無公開 API）
- `DrugInfoService.get_full_info()` 自動整合台灣資訊

## 📁 相關檔案

```
src/pharmacy_mcp/
├── infrastructure/api/
│   ├── tfda.py         # TFDA Client + 藥名對照
│   └── nhi.py          # NHI Client + 給付規則
├── application/services/
│   ├── taiwan_drug.py  # 台灣藥品服務
│   └── drug_info.py    # 整合台灣資訊
└── presentation/
    └── server.py       # 19 個 MCP Tools
```

## 🔜 下一步（v0.9.0）

- 藥品比較功能 (`compare_drugs`)
- 適應症 ↔ 藥品雙向查詢
- 重複用藥檢查
- 台灣學名藥替代品查詢

---
*Last updated: 2025-12-22*
