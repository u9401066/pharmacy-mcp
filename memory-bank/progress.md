# Progress (Updated: 2026-07-24)

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

### v0.8.5 模板整合 + 處方功能 🆕
- ✅ 整合 template-is-all-you-need 模板架構
- ✅ Claude Skills (13 個技能)
- ✅ Bylaws (4 個子法)
- ✅ 合併 AGENTS.md + CLAUDE.md → copilot-instructions.md
- ✅ Domain: Order 實體、OrderStatus
- ✅ Domain: ValidationResult, OrderResult, StopResult, FormularyItem, RenalAdjustment 值物件
- ✅ Infrastructure: FormularyKnowledge (院內藥品檔)
- ✅ Infrastructure: RenalDosingKnowledge (腎功能劑量調整)
- ✅ Infrastructure: HISMockClient (模擬 HIS)
- ✅ Data: formulary.json (15 種院內藥品)
- ✅ Data: renal_adjustments.json (12 種腎功能調整規則)
- ✅ Application: PrescriptionService (原子化處方操作)
- ✅ Presentation: 6 個新 MCP Tools (處方相關)
- ✅ LangGraph 範例模組 (`examples/langgraph_prescription/`)
- ✅ 71 個測試全部通過

## Doing

- ✅ v1.0.0a1 現代化翻新與 main 整合
- ✅ QueryResponse v1.0 穩定輸出契約
- ✅ 全 MCP tool 共用 outputSchema 與 output_format/locale
- ✅ 修正 `pharmacy-mcp` CLI entry point
- ✅ provider catalog 與 unified query orchestrator
- ✅ `query_pharmacy` / `list_knowledge_sources` MCP tools
- ✅ provider timeout、partial failure、provenance 聚合
- ✅ 台灣 TFDA/NHI 複合查詢與官方 CSV SQLite 索引
- ✅ NHI 真實資料 smoke test（224,455 rows）與 ROC date regression test
- ✅ DailyMed SPL v2 adapter + live smoke test
- ✅ PubChem PUG REST chemical identity adapter + live smoke test
- ✅ MedlinePlus Connect patient education adapter + live smoke test
- ✅ PubMed E-utilities literature citation adapter + live smoke test
- ✅ ClinicalTrials.gov API v2 intervention-study adapter + live smoke test
- ✅ ChEMBL molecule/target/bioactivity adapter + live smoke test
- ✅ Open Targets drug/target/indication GraphQL adapter + live smoke test
- ✅ FHIR R4/R5 medication + explicit patient query adapter
- ✅ FHIR R5 InventoryItem/InventoryReport + R4 SupplyDelivery fallback
- ✅ Bearer secret boundary、resource allowlist、unsupported resource isolation
- ✅ PDF/DOC/DOCX/CSV/XLS/XLSX/Markdown/text file connector
- ✅ read-only allowlisted SQLite connector
- ✅ vendor-neutral vector search gateway connector
- ✅ fixed HTTPS document connector（no redirects / no caller URL）
- ✅ Python agent harness + deterministic CLI
- ✅ MCP agent-contract prompt
- ✅ FastMCP stdio/SSE/Streamable HTTP + lazy ASGI
- ✅ trusted PK/DDI formula catalog、resources、prompts 與 simulation service
- ✅ 全 35 tools 由 transport boundary 套用 QueryResponse v1.0
- ✅ 統一查詢加入 operator-controlled fan-out、平行數與 per-provider timeout
- ✅ query response 回傳可觀測的 provider execution policy metadata
- ✅ 文件搜尋加入 opaque ID、完整 extracted-text SHA-256、行/字元 locator
- ✅ `read_knowledge_document` 提供不接受 path 的 bounded 文件調閱
- ✅ `inspect_fhir_server` 提供 CapabilityStatement 相容性檢查
- ✅ FHIR searchset/resourceType 驗證，保留 core fields、extensions 與院內欄位
- ✅ 私有 SOAP/WCF 契約僅本機盤點，泛化成可設定 `wcf` provider
- ✅ WCF HTTPS/TLS、defused XML、byte/record limits、TTL cache、field allowlists
- ✅ 真實 WCF endpoint/action/欄位只存在 ignored `.env`，repo 僅有 placeholders
- ✅ MkDocs Material GitHub Pages 說明網站
- ✅ GitHub Pages official artifact/deploy workflow
- ✅ Python 3.11/3.12/3.13 test/build CI
- ✅ 雙語 README、architecture/security/contributing/changelog 現代化
- ✅ 雙語 README 重構為大型 MCP 產品入口，補齊 FHIR、文件、SQL、WCF 與安全邊界
- ✅ 新增兩張 accessible repo-native SVG（hero + knowledge-plane architecture）
- ✅ README 新增 bounded fan-out、FHIR 相容性、citation-ready retrieval Mermaid
- ✅ `architect.md` 與 `systemPatterns.md` 從 19-tool 舊模型更新為 35-tool 現況
- ✅ repo-wide Ruff format/check baseline
- ✅ repo-wide strict mypy baseline
- ✅ CI quality gate（format/lint/type）
- ✅ 195 tests / 82.97% branch coverage（gate 70%）
- ✅ SQLite/Cache resources explicit lifecycle，ResourceWarning-as-error 通過
- ✅ Bandit security baseline in CI；legacy cache key 改 SHA-256
- ✅ MkDocs strict build、sdist/wheel build
- ✅ isolated MCP stdio + Streamable HTTP smoke（第一階段 33 tools / 3 prompts / compound query / simulation）
- ✅ isolated wheel CLI smoke
- ✅ RxClass 獨立 provider（class ID/type/relation/source）
- ✅ openFDA 七個 drug endpoints 全部可依 capability 執行
- ✅ bounded openFDA label/regulatory projections
- ✅ provider partial status 正確傳遞到統一回應
- ✅ TFDA current HTTPS ZIP ingestion + plain JSON compatibility
- ✅ 每週 18-surface live health workflow；2026-07-20 全數通過
- ✅ 藥品知識 coverage/evidence matrix（可執行來源、capability、測試與界線）
- ✅ 新增能力後完整 release audit 全綠（quality/security/docs/package/CLI/MCP）
- ✅ PR #2 已合併至 `main`，本階段開始前已同步 `origin/main`
- ✅ 私有內部 API archives 僅本機檢視，保持 exact-ignore、untracked、未複製且不進入 artifact
- ✅ 第二階段 focused tests 41 passed；strict mypy 與 changed-file Ruff 通過
- ✅ 最終 206 tests / 83.46% branch coverage（gate 70%）
- ✅ repo-wide Ruff、strict mypy、Bandit、lock、MkDocs strict 全綠
- ✅ sdist/wheel、artifact/private-contract audit、Python 3.13 isolated 35-tool smoke 全綠
- ⚠️ 院內 WCF 主機可解析但此環境無私網連線；需在院內網路做一次 live query
- ✅ two-parent integration 已發佈；PR #2 mergeable 且 CI run 29741488853 成功
- ✅ API/docs expansion audited tree 已發佈；CI run 29742857952 成功
- ✅ 本機 `gh` 已重新驗證，可透過 HTTPS push publication branch
- ✅ SVG XML 有效且 hero/architecture 皆完成實際 PNG render 視覺檢查
- ✅ README/MEM 後 206 tests、83.46% branch coverage、Ruff、mypy、Bandit、lock、MkDocs 全綠
- ✅ sdist/wheel artifact audit 與 isolated Python 3.13 35-tool smoke 通過
- ✅ tracked range、wheel、sdist 的私有 WCF 契約字串掃描皆為零命中
- ✅ 分段 commits：`01228f8` feature、`36361c4` tests、`024f954` docs、最終 Memory checkpoint
- ✅ 發布分支 `agent/modernize-pharmacy-mcp-readme` 已推至 origin；既有 harness 修改未混入

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
