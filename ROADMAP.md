# Roadmap

## 📅 版本規劃

### v0.1.0 - 基礎架構 ✅
- [x] 專案初始化
- [x] 目錄結構
- [x] Memory Bank
- [x] 文檔系統

### v0.2.0 - 核心 API 整合 🚧
- [ ] RxNorm API Client
- [ ] openFDA API Client
- [ ] DailyMed API Client
- [ ] 快取層實作

### v0.3.0 - 藥品查詢模組
- [ ] search_drug_by_name
- [ ] search_drug_by_atc
- [ ] search_drug_by_indication
- [ ] get_drug_alternatives

### v0.4.0 - 藥品資訊模組
- [ ] get_drug_details
- [ ] get_drug_label
- [ ] get_pharmacokinetics
- [ ] get_contraindications
- [ ] get_side_effects

### v0.5.0 - 劑量計算模組
- [ ] calculate_pediatric_dose
- [ ] calculate_renal_dose
- [ ] calculate_weight_dose
- [ ] calculate_bsa_dose

### v0.6.0 - 交互作用模組
- [ ] check_drug_interaction
- [ ] check_multiple_drugs
- [ ] get_interaction_severity
- [ ] get_interaction_mechanism

### v0.7.0 - 食品藥品衝突模組
- [ ] check_food_interaction
- [ ] check_alcohol_interaction
- [ ] check_supplement_interaction
- [ ] get_dietary_restrictions

### v1.0.0 - 正式發布
- [ ] 完整測試覆蓋
- [ ] 文檔完善
- [ ] 效能優化
- [ ] 安全性審查

---

## 🔮 未來規劃

### v0.8.0 - 台灣健保整合 ✅
- [x] 台灣 TFDA 藥品資料 API Client
- [x] 中文藥名對照功能（120+ 藥品）
- [x] TFDA 藥品查詢 Tools
- [x] 健保給付查詢 Client
- [x] 健保藥價查詢功能
- [x] 事前審查藥品清單
- [x] 健保給付規則資料庫（60+ 藥品）
- [x] 整合至 DrugInfoService
- [x] 6 個新 MCP Tools
- [x] 43 個測試全部通過

### v0.9.0 - 處方執行功能 🔜
- [ ] Domain: Prescription entity, Order value objects
- [ ] Mock Data: formulary.json, renal_adjustments.json
- [ ] Infrastructure: HIS Mock API client
- [ ] Service: PrescriptionService (整合現有 services)
- [ ] Tools: `get_formulary_options` - 查詢院內可開立藥品
- [ ] Tools: `get_dosing_recommendations` - 取得建議用法用量
- [ ] Tools: `generate_prescription_plan` - 產生處方計畫
- [ ] Tools: `submit_prescription` - 確認開立處方
- [ ] Tools: `discontinue_order` - 停止醫囑
- [ ] 知識庫: 腎功能調整規則 (Top 30 藥物)

### v0.10.0 - Agent 增強功能
- [ ] 藥品比較功能 (`compare_drugs`)
- [ ] 適應症 ↔ 藥品雙向查詢
- [ ] 重複用藥檢查 (`check_therapeutic_duplication`)
- [ ] 台灣學名藥替代品查詢
- [ ] 批次查詢 API

### v1.0.0 - 正式發布
- [ ] 完整測試覆蓋（> 80%）
- [ ] 文檔完善
- [ ] 效能優化
- [ ] 安全性審查
- [ ] PyPI 發布

### v1.1.0 - 台灣健保進階功能
- [ ] 醫院藥碼對照（台大、榮總等）
- [ ] 藥袋資訊生成
- [ ] ATC 分類碼對照
- [ ] 藥品外觀查詢

### v1.2.0 - 臨床安全強化
- [ ] 病患用藥清單管理
- [ ] 過敏交叉反應檢查
- [ ] 特殊族群警示（孕婦、哺乳、兒童、老人）
- [ ] 輸液配伍禁忌

### v1.3.0 - 進階功能
- [ ] 藥物基因組學 (Pharmacogenomics)
- [ ] 治療藥物監測 (TDM)
- [ ] 治療指引整合

---

*Last Updated: 2025-12-22*
