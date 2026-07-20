# Decision Log

## 決策記錄

### DEC-001: 使用 MCP Python SDK
**日期**: 2025-12-22
**決策**: 使用官方 `mcp` Python SDK
**原因**: 
- 官方支援，穩定性高
- 與 Claude 整合最佳
- 持續更新維護

### DEC-002: 採用 DDD 分層架構
**日期**: 2025-12-22
**決策**: 使用 Domain-Driven Design 分層
**原因**:
- 業務邏輯與基礎設施分離
- 易於測試和維護
- 符合模板規範

### DEC-003: HTTP Client 選擇 httpx
**日期**: 2025-12-22
**決策**: 使用 httpx 而非 requests
**原因**:
- 原生支援 async/await
- API 與 requests 相容
- 效能較佳

### DEC-004: 快取選擇 diskcache
**日期**: 2025-12-22
**決策**: 使用 diskcache 而非 Redis
**原因**:
- 無需額外服務
- 適合單機部署
- 簡單易用

### DEC-005: 資料來源優先序
**日期**: 2025-12-22
**決策**: RxNorm > openFDA > DailyMed
**原因**:
- RxNorm 提供標準化藥品命名
- openFDA 提供不良反應資料
- DailyMed 提供完整仿單

### DEC-006: 本地藥物交互作用資料庫
**日期**: 2025-12-22
**決策**: 新增本地藥物交互作用資料庫作為備用
**原因**:
- RxNorm Drug Interaction API 於 2025 年被 NLM 停用
- 確保 MCP Tools 仍能提供基本的藥物交互作用檢查
- 本地資料庫包含 25+ 種臨床常見的高風險交互作用
- 結合 FDA 標籤資訊提供更完整的資料
**後續行動**:
- 尋找替代的外部 API（如 DrugBank API）
- 持續擴充本地資料庫

### DEC-007: 台灣藥品資料不自建資料庫
**日期**: 2025-12-22
**決策**: 使用政府開放資料 + disk cache，不建立獨立資料庫
**原因**:
- 政府開放資料每週更新，保持資料新鮮度
- 減少維護成本
- disk cache 提供 7 天 TTL，平衡效能與即時性
**資料來源**:
- TFDA: https://data.fda.gov.tw/opendata/exportDataList.do
- 政府資料開放平台: data.gov.tw/dataset/9122

### DEC-008: 健保給付規則使用本地資料庫
**日期**: 2025-12-22
**決策**: 手動維護健保給付規則資料庫
**原因**:
- 健保署無提供公開 API
- 給付規定變動頻率較低
- 可針對臨床常用藥品優先建立
**涵蓋範圍**: 60+ 藥品，11 類別

### DEC-009: DrugInfoService 自動整合台灣資訊
**日期**: 2025-12-22
**決策**: `get_full_info()` 回傳結果自動包含 `taiwan` 欄位
**原因**:
- 使用者無需額外呼叫即可獲得本地化資訊
- 台灣資訊作為補充，不影響原有 API 結構
- 當藥品有對應資料時才顯示，無則為 null

### DEC-010: MCP structuredContent 作為唯一真實輸出
**日期**: 2026-07-20
**決策**: 所有 tools 共用 `QueryResponse` v1.0 JSON Schema；文字只作為 renderer
**原因**:
- 限制 agent 輸出漂移，讓查詢可被程式穩定解析
- 以 `outputSchema` 讓 MCP SDK 在回傳前驗證結果
- 允許人類選擇 JSON/compact JSON/Markdown，而不改變機器契約
**相容策略**:
- 原有 provider payload 保留在 `data`
- breaking change 必須提升 `schema_version`
- agents 必須保留 provenance、warnings、errors、meta，不可補造缺漏資料

### DEC-011: 統一 provider port 與誠實的來源狀態
**日期**: 2026-07-20
**決策**: API/FHIR/DB/file/vector/web 共用 `KnowledgeProvider` port，catalog 分開記錄 readiness
**原因**:
- agent 只需呼叫 `query_pharmacy`，不必理解每個後端協議
- provider failure 隔離後仍可回傳 partial result 與 provenance
- `registered` 與 `state` 分離，避免把 cataloged/需授權來源誤稱為已啟用
**執行規則**:
- 未設定或需授權來源回傳 `provider_unavailable`，不得靜默替代
- public/open data 不得被描述為可直接進行臨床決策
- 所有複合結果保留個別來源，不把多來源偽裝成單一權威資料

### DEC-012: NHI 官方大型 CSV 採原子 SQLite 索引
**日期**: 2026-07-20
**決策**: 串流下載 resource `A21030000I-E41001-001`，驗證後建立版本化 SQLite
**原因**:
- 官方資料約 97 MB / 22 萬歷史 rows，不適合每次查詢掃描或放入 git
- SQLite 可快速合併健保碼、現行支付價、ATC、有效期與給付章節
- temp DB 完成後 atomic replace，下載/建置中斷不會破壞可用索引
**驗證**:
- 2026-07-20 真實資料建置 224,455 rows
- ROC 六碼/七碼日期以數值比較；index schema version 變更會自動重建

### DEC-013: 公共 API 以 bounded projection 接入統一 port
**日期**: 2026-07-20
**決策**: DailyMed/PubChem/MedlinePlus 各自保留官方 client，但只透過 provider port 暴露給 agent
**原因**:
- 避免大型 SPL/化學/HTML payload 無限制進入 context
- 每個來源可獨立 timeout/fail，複合查詢仍保留其他成功結果
- 保留官方 ID、版本、連結與 attribution，方便追溯與二階段詳查

---
*Last updated: 2025-12-22*
