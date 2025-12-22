# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (none)

### Changed
- (none)

### Fixed
- (none)

---

## [0.8.0] - 2025-12-22

### Added - 台灣健保整合 🇹🇼

#### 新增 MCP Tools（6 個）
- `search_tfda_drug` - 搜尋台灣 TFDA 藥品許可證資料庫
- `get_nhi_coverage` - 查詢藥品健保給付狀態
- `get_nhi_drug_price` - 查詢健保藥價
- `translate_drug_name` - 藥品名稱中英對照
- `list_prior_authorization_drugs` - 列出需事前審查藥品
- `list_nhi_coverage_rules` - 列出健保給付規則資料庫

#### 新增 Infrastructure
- `TFDAClient` - 台灣 TFDA 藥品開放資料 API 客戶端
- `NHIClient` - 健保給付查詢客戶端
- `translate_drug_name()` - 中英藥名對照函數
- `DRUG_NAME_MAPPING` - 120+ 常用藥品中英對照表
- `NHI_COVERAGE_RULES` - 60+ 藥品健保給付規則資料庫

#### 新增 Service
- `TaiwanDrugService` - 台灣藥品服務層

#### 健保給付規則涵蓋類別
- 抗凝血/抗血小板藥物（8 種）
- 降血脂藥物（5 種）
- 降血糖藥物（9 種）
- 降血壓藥物（6 種）
- 質子幫浦抑制劑（3 種）
- 抗生素（3 種）
- 神經/精神科用藥（5 種）
- 止痛藥（3 種）
- 生物製劑/標靶藥物（6 種）
- 抗癌標靶藥物（6 種）
- 其他常用藥物（6 種）

#### 藥名對照表涵蓋類別
- 抗凝血/抗血小板（10 種）
- 降血脂（7 種）
- 降血糖（12 種）
- 降血壓（16 種）
- 質子幫浦抑制劑（5 種）
- 抗生素（7 種）
- 神經/精神科（17 種）
- 止痛藥（9 種）
- 類固醇（5 種）
- 呼吸道用藥（6 種）
- 麻醉/手術用藥（11 種）
- 生物製劑/標靶（14 種）
- 及更多...

### Changed
- `DrugInfoService.get_full_info()` 現在自動包含台灣藥品資訊（翻譯 + 健保給付）
- 總測試數量增加至 43 個（全部通過）

---

## [0.1.1] - 2025-12-22

### Fixed
- 修復 RxNorm Drug Interaction API 停用問題（NLM 於 2025 年停用該 API）
- 新增本地藥物交互作用資料庫作為備用方案（25+ 種常見交互作用）
- `check_drug_interaction` 和 `check_multi_drug_interactions` 現在使用本地資料庫 + FDA 標籤

### Changed
- `InteractionService` 現在優先使用本地資料庫，並結合 FDA 標籤資訊
- API 回應中加入 `source` 和 `note` 欄位說明資料來源

---

## [0.1.0] - 2025-12-22

### Added
- 專案初始化
- 完整目錄結構
- pyproject.toml 配置
- README 文檔（中/英）
- CONSTITUTION.md 專案憲法
- CLAUDE.md / AGENTS.md AI 指引
- Memory Bank 初始結構
- 基礎 MCP Tool 定義
  - Drug Search tools
  - Drug Info tools
  - Dosage Calculator tools
  - Interaction Checker tools
  - Food-Drug Interaction tools
