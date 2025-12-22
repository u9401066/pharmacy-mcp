# Progress (Updated: 2025-12-22)

## Done

### v0.1.x 基礎建設
- ✅ 建立完整專案結構
- ✅ 初始化 pyproject.toml
- ✅ 建立 README (中/英)
- ✅ 建立 CONSTITUTION.md
- ✅ 建立 ARCHITECTURE.md
- ✅ 建立 Memory Bank 結構
- ✅ 建立 Claude Skills 結構
- ✅ Domain Layer: Drug, DrugConcept, DrugType entities
- ✅ Domain Layer: DrugInteraction, InteractionSeverity entities
- ✅ Domain Layer: Dosage, Severity value objects
- ✅ Infrastructure: RxNorm API client
- ✅ Infrastructure: FDA openFDA API client
- ✅ Infrastructure: Disk cache service
- ✅ Application: DrugSearchService
- ✅ Application: DrugInfoService
- ✅ Application: InteractionService (drug-drug + food-drug)
- ✅ Application: DosageService (weight/BSA/CrCl/pediatric)
- ✅ Presentation: MCP Server with 13 tools
- ✅ 修復 RxNorm Drug Interaction API 停用問題
- ✅ 新增本地藥物交互作用資料庫（25+ 種常見交互作用）
- ✅ Git 倉庫初始化

### v0.8.0 台灣健保整合 🇹🇼
- ✅ TFDA 藥品資料 API Client (`TFDAClient`)
- ✅ NHI 健保給付查詢 Client (`NHIClient`)
- ✅ 中文藥名對照功能 (`translate_drug_name`)
- ✅ 藥名對照表 - 120+ 常用藥品
- ✅ 健保給付規則資料庫 - 60+ 藥品
- ✅ TaiwanDrugService 服務層
- ✅ 6 個新 MCP Tools:
  - `search_tfda_drug`
  - `get_nhi_coverage`
  - `get_nhi_drug_price`
  - `translate_drug_name`
  - `list_prior_authorization_drugs`
  - `list_nhi_coverage_rules`
- ✅ 整合至 DrugInfoService（自動加入台灣資訊）
- ✅ 43 個測試全部通過

## Doing

- 無

## Next

### v0.9.0 Agent 增強
- 📋 藥品比較功能 (`compare_drugs`)
- 📋 適應症 ↔ 藥品雙向查詢
- 📋 重複用藥檢查
- 📋 台灣學名藥替代品查詢

### v1.0.0 正式發布
- 📋 完整測試覆蓋（> 80%）
- 📋 文檔完善
- 📋 效能優化
- 📋 PyPI 發布
