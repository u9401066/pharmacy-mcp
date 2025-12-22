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
