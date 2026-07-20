# Active Context

## 🎯 當前焦點

- v0.9.0a1 全面現代化翻新進行中
- 建立 MCP + harness 藥品查詢單一入口
- 統一所有 tool 的可驗證輸出契約與格式約束

## 🛠️ 本輪進度（2026-07-20）

- 建立 `QueryResponse` v1.0：固定 status/data/sources/warnings/errors/meta
- 所有 MCP tools 自動加入 `output_format` 與 `locale`
- 所有 MCP tools 宣告相同 `outputSchema`，由 SDK 驗證 structured content
- 支援 deterministic `json`、`json_compact`、`markdown` renderer
- 修正套件 CLI entry point
- 下一批：provider catalog、統一複合查詢與台灣健保真實資料匯入
- 已新增 `query_pharmacy` 單一入口與 `list_knowledge_sources` 探索工具
- provider registry 支援 capability/source routing、並行查詢、timeout、partial failure
- catalog 涵蓋主要公共藥品 API、台灣資料、FHIR、local/SQL/vector/file/web 與需授權來源
- 下一批：台灣健保真實 CSV 索引、DailyMed/PubChem 與 FHIR/院內庫存 adapters
- 已將 NHI placeholder 換成官方月資料 CSV → SQLite 原子索引
- 真實 smoke test：2026-07-20 建置 224,455 rows，可查現行支付價/ATC/有效期/官方連結
- 修正民國 99 年六碼日期誤判現行資料，索引 schema version 會強制淘汰舊索引
- 台灣 provider 現在複合 TFDA + NHI items + coverage rules，個別故障保留 partial result
- 下一批：DailyMed/PubChem/MedlinePlus、FHIR/院內庫存 adapters
- 已實作並註冊 DailyMed SPL v2、PubChem PUG REST、MedlinePlus Connect adapters
- 2026-07-20 live compound smoke test 三來源同時回 `ok`，provenance 完整
- 下一批：FHIR/院內庫存、SQL/vector/file/web adapters 與 agent harness
- 已完成 read-only FHIR R4/R5 adapter：Medication/Knowledge/Request/Dispense + Inventory/Supply
- FHIR base URL 設定後才註冊；Bearer token 為 SecretStr 且不進 MCP args/results/logs
- patient resources 僅在明確 `context.patient_id` 時查詢；R5 inventory 不支援時保留 R4 fallback partial result
- 下一批：SQL/vector/file/web connectors、agent harness、GitHub Pages/CI

## 📝 最近完成的變更（v0.8.5）

| 檔案 | 變更內容 |
|------|----------|
| `domain/entities/order.py` | 新增 Order 實體、OrderStatus |
| `domain/value_objects/order_result.py` | 新增 ValidationResult, OrderResult, StopResult, FormularyItem, RenalAdjustment |
| `infrastructure/knowledge/formulary.py` | 新增院內藥品檔知識庫 |
| `infrastructure/knowledge/renal_dosing.py` | 新增腎功能劑量調整知識庫 |
| `infrastructure/api/his_mock.py` | 新增 HIS Mock Client |
| `data/formulary.json` | 15 種院內藥品資料 |
| `data/renal_adjustments.json` | 12 種腎功能調整規則 |
| `application/services/prescription.py` | 新增 PrescriptionService |
| `presentation/server.py` | 新增 6 個處方相關 MCP Tools |
| `examples/langgraph_prescription/` | LangGraph 範例模組 |
| `tests/test_prescription.py` | 28 個測試 |
| `.github/copilot-instructions.md` | 統一 AI 指令 |
| `.claude/skills/` | 13 個 Claude Skills |
| `.github/bylaws/` | 4 個子法 |

## ✅ v0.8.5 新增功能

### 設計原則（給低階 Agent）
- **原子化**：每個 Tool 做一件事
- **無狀態**：狀態由外部 workflow 管理
- **確定性**：固定 input → 固定 output
- **可組合**：由 workflow 編排多個 tools

### 新增 MCP Tools（25 個，+6）
- `get_formulary_item` - 取得院內藥品詳情
- `search_formulary` - 搜尋院內藥品
- `get_renal_adjustment` - 取得腎功能調整建議
- `validate_order` - 驗證單一醫囑
- `submit_order` - 送出醫囑到 HIS
- `stop_order` - 停止醫囑

### 知識庫
- 院內藥品檔：15 種藥品（抗生素、心血管、鎮靜等）
- 腎功能調整：12 種藥品規則

### LangGraph 範例
- `examples/langgraph_prescription/`
  - `state.py` - PrescriptionState
  - `nodes.py` - 4 個 node 函數
  - `workflow.py` - StateGraph 定義
  - `demo.py` - 執行範例

## 📁 相關檔案

```
src/pharmacy_mcp/
├── domain/
│   ├── entities/order.py        # Order 實體
│   └── value_objects/order_result.py  # 處方相關值物件
├── infrastructure/
│   ├── api/his_mock.py          # HIS Mock
│   └── knowledge/
│       ├── formulary.py         # 院內藥品檔
│       └── renal_dosing.py      # 腎功能調整
├── data/
│   ├── formulary.json           # 藥品資料
│   └── renal_adjustments.json   # 調整規則
├── application/services/
│   └── prescription.py          # 處方服務
└── presentation/
    └── server.py                # 25 個 MCP Tools

examples/langgraph_prescription/
├── state.py
├── nodes.py
├── workflow.py
└── demo.py
```

## 🔜 下一步（v0.9.0）

- 藥品比較功能 (`compare_drugs`)
- 適應症 ↔ 藥品雙向查詢
- 重複用藥檢查
- 台灣學名藥替代品查詢

---
*Last updated: 2026-01-08*
