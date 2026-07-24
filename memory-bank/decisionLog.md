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
**後續修正**: NHI 大型歷史資料已由 DEC-012 改採本機 SQLite 索引；本決策僅保留於 TFDA 下載快取。
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

### DEC-014: FHIR adapter 預設隨附、設定 endpoint 後才註冊
**日期**: 2026-07-20
**決策**: read-only FHIR client 支援 R4/R5；無 base URL 時 catalog ready 但 runtime unregistered
**安全界線**:
- Bearer token 僅讀環境 SecretStr，不接受 tool argument、不回傳、不記錄
- patient resources 僅在呼叫方明確提供 `context.patient_id` 時查詢
- resource type 採 allowlist；每個不支援的 R4/R5 resource 獨立降級為 warning
- SMART Backend Services 的 token 取得/輪替交由院內授權基礎設施

### DEC-015: 組織資料連接器採 operator allowlist
**日期**: 2026-07-20
**決策**: file/SQL/vector/web 皆由啟動設定限定資料邊界，不接受 agent 指定路徑、SQL 或 URL
**安全界線**:
- file 僅掃描設定 roots，拒絕 symlink/越界/超大檔案並限制掃描數
- SQLite 使用 `mode=ro`、驗證過的 table/column allowlist 與 bound values
- vector 只傳 query/limit/明確 `vector_filters`，不外送 patient context
- web 僅固定 credential-free HTTPS URL、不跟 redirect、限制 response bytes
**原因**:
- 單一入口必須能整合院內資料，同時避免 agent 取得通用檔案、資料庫或網路能力
- 統一 provider port 讓每個來源維持 provenance、partial failure 與相同輸出契約

### DEC-016: MCP、Python 與 CLI 共用同一 QueryResponse
**日期**: 2026-07-20
**決策**: `query_pharmacy`、`PharmacyHarness`、`pharmacy-query` 全部回傳/輸出 QueryResponse v1.0
**Agent 約束**:
- 所有 tools 宣告相同 outputSchema，MCP structuredContent 是唯一真實來源
- `pharmacy-query-contract` MCP prompt 明示保留七個 top-level fields
- JSON renderer 不允許額外 prose/code fence；不得補造缺失臨床事實或丟棄 partial failures
**原因**:
- transport 可以不同，但 agent 解析和下游自動化只需維護一種契約
- prompt + JSON Schema + deterministic renderer 形成互補的格式約束

### DEC-017: 文件站採 MkDocs + GitHub Pages artifact deployment
**日期**: 2026-07-20
**決策**: `docs/` 是文件單一來源，MkDocs Material strict build 後透過 GitHub Pages Actions artifact 發布
**實作**:
- `mkdocs.yml` 定義導覽、搜尋、淺深色與 responsive landing page
- CI 驗證 strict docs build；Pages workflow 分離 build/deploy job
- deploy job 僅給 `pages: write` / `id-token: write`，一般 CI 維持 `contents: read`
**原因**:
- 不把產物或 `gh-pages` branch 手動混入主要開發流程
- 文件變更能在 PR/CI 先驗證，main 更新後自動發布 GitHub.io

### DEC-018: 保留 strict mypy 並清償 repo-wide 品質債務
**日期**: 2026-07-20
**決策**: 不以關閉 strict 或大量 ignore 讓 CI 表面通過；修正裸型別、API payload narrowing 與 cache 邊界
**例外**:
- `diskcache` 套件缺少型別標記，因此只對該第三方 module 設 `ignore_missing_imports`
- MCP SDK 的 server decorators 未暴露完整型別，只在四個 decorator 行採精確 error-code ignore
**結果**:
- Ruff format/check 覆蓋 `src tests examples`
- strict mypy 覆蓋 `src`
- 兩者納入獨立 CI quality job

### DEC-019: Coverage 與資源生命週期是 release gate
**日期**: 2026-07-20
**決策**: CI 的多版本 test job 執行 branch coverage，維持既有 70% 門檻
**改善**:
- 新增 retained atomic services、RxNorm/openFDA/TFDA 舊 adapters 的合成/HTTP mock 測試
- coverage 從 63.9% 提升到 78.88%，tests 從 107 增至 115
- NHI SQLite 使用 `contextlib.closing`；CacheService 以 finalizer + idempotent close 管理連線
- 測試可將 ResourceWarning/PytestUnraisableExceptionWarning 升為 error
**原因**:
- SQLite connection 的 `with connection` 只管理 transaction，不會關閉 connection
- 相容性 tools 既然繼續公開，就必須由 CI 覆蓋，而非只測新 gateway

### DEC-020: v0.9.0a1 以 transport-level smoke 作最終驗證
**日期**: 2026-07-20
**決策**: 除 unit/integration tests 外，release readiness 必須驗證真實 MCP stdio session 與 built wheel
**驗證結果**:
- MCP client 完成 initialize/list_tools/list_prompts/get_prompt/call_tool
- server 暴露 28 tools、`pharmacy-query-contract` prompt，compound result 為 QueryResponse v1.0
- sdist/wheel build 成功，isolated wheel 可執行 `pharmacy-query` 並產出可解析 JSON
- MkDocs strict build 成功，Pages artifact workflow 已在 repo
**發布狀態**:
- local implementation ready；GitHub push 因本機 u9401066 token invalid 而尚未完成
- 不在 repo 寫入或繞過 credentials；由 operator 重新登入後推送

### DEC-021: openFDA 依 capability 執行七個獨立藥品端點
**日期**: 2026-07-20
**決策**: `openfda` provider 明確分流 label、event、NDC、enforcement、Drugs@FDA、Orange Book、shortages
**原因**:
- catalog 宣告的能力必須有實際 executable route，不得由 label search 冒充
- NDC、FDA approval、therapeutic equivalence、recall 與 shortage 有不同語意與更新週期
- 一個端點失敗時保留其他成功結果，並把統一回應標為 `partial`
**輸出界線**:
- `search` 只查 labels；監測/法規資料必須明確要求 capability
- label 文字、products、submissions 與巢狀陣列均採 bounded projection
- NDC 不得被描述成 FDA approval 或 reimbursement

### DEC-022: 官方來源漂移採每週 live probe 並保留安全下載格式
**日期**: 2026-07-20
**決策**: GitHub Actions 初始檢查 14 個公共來源 surface；大型 TFDA/NHI 資料只驗證 stream status。擴充後的 18-surface 規則由 DEC-024 接續。
**原因**:
- mock tests 無法發現 endpoint redirect、格式或欄位漂移
- 首次執行即發現 TFDA 舊 URL 轉向明文 HTTP 且新格式改為 ZIP
- 維運檢查必須與 CI correctness gate 分離，避免一般 PR 依賴外部服務
**TFDA 安全處理**:
- 固定使用官方 HTTPS URL，不跟隨降級到 HTTP 的 redirect
- ZIP 只接受單一 JSON member，限制 uncompressed size，不解壓到檔案系統
- 保留 plain JSON 相容路徑與七日 cache

### DEC-023: 以 FastMCP 子類在 transport 邊界統一輸出
**日期**: 2026-07-20
**決策**: 保留 FastMCP 的 stdio、SSE、Streamable HTTP、resource 與 prompt
能力，並由 `PharmacyFastMCP` 在 `list_tools` 與 `call_tool` 邊界統一加入
`output_format`、`locale`、`QueryResponse` schema 及 deterministic rendering。
**理由**:
- 不需在 33 個工具函式重複輸出包裝邏輯
- MCP schema、直接 Python call 與網路 transport 使用同一份行為
- 可同時保留 main 的 simulation/HTTP 現代化及 gateway 的 agent constraint
- tool validation 前移，執行結果一律保留 status/provenance/warnings/errors

### DEC-024: 藥品 API 全面性以知識面與可執行證據管理
**日期**: 2026-07-20
**決策**: 在既有標籤、法規、化學、病人教育來源之外，加入 PubMed、
ClinicalTrials.gov、ChEMBL 與 Open Targets；以 `literature`、
`clinical_trial`、`indication`、`target`、`bioactivity` capability 明確路由。
**路由與負載界線**:
- 四個 discovery provider 不宣告通用 `search`，避免每次藥名查詢無條件扇出
- 明確 capability 或 source 才啟動，ChEMBL/Open Targets 詳情筆數有上限
- 所有回應使用 bounded projection 並保留 PMID/NCT/ChEMBL/target/disease IDs
**「全面」的可驗證定義**:
- 沒有固定且封閉的全球藥品 API 清單，因此以 identity、label/dosing、
  surveillance、literature、trial、target/bioactivity、indication、Taiwan、
  FHIR/inventory 與 organization knowledge 等 surface 建立 evidence matrix
- `ready` 必須同時具備 executable adapter、capability、provenance、mock contract、
  live probe 與文件；DrugBank/FDB/Micromedex 維持 `license_required`
**驗證**:
- 195 tests / 82.97% branch coverage，Ruff、strict mypy、Bandit、docs、package gates 全綠
- 18/18 live probes 成功，四來源 compound CLI query 經 QueryResponse v1.0 回傳

### DEC-025: 大型 MCP fan-out 與 connector 調閱採伺服器端政策
**日期**: 2026-07-24
**決策**: 統一查詢的最大 provider 數、同時執行數與 timeout 由 operator 設定；
文件完整調閱與 FHIR capability inspection 採獨立 MCP tools，但仍共用
`QueryResponse` v1.0。
**平行查詢界線**:
- `provider_max_per_query` 超限時 fail closed，且不送出任何 upstream request
- `provider_max_parallel` 以 semaphore 控制單次複合查詢的 active providers
- timeout 從 provider 取得執行 slot 後開始，避免排隊時間冒充 upstream timeout
- 實際 policy 以 additive `data.execution` 回傳，caller 不能透過 tool argument 放寬
**文件證據界線**:
- 搜尋結果以 root-relative path 衍生 opaque stable ID，不接受 caller path
- 每次抽取提供完整文字 SHA-256、exact half-open char span 與 line span
- `read_knowledge_document` 僅能依搜尋取得的 ID 做最多 50,000 字元 bounded read
**FHIR 契約界線**:
- `inspect_fhir_server` 從 CapabilityStatement 投影 resource、interaction、
  search parameter 與 profile，不回傳 token/header
- search 必須是 `Bundle.type=searchset`；錯誤型別 entry 隔離為 warning
- 合法 FHIR resource 保留 raw core fields、extension/profile 與院內自訂 keys，
  不建立會遺失資料的共同最小 schema
**相容性**:
- 不改 QueryResponse 七個 top-level fields 或 `schema_version`
- 新 execution、locator、capability 欄位均位於 `data`，屬 additive change

### DEC-026: 私有 daily WCF 流程拆成 read provider 與外部 materialization
**日期**: 2026-07-24
**決策**: 私有文件中的 no-argument SOAP/WCF operation 以泛化 `wcf` provider
接入 `query_pharmacy`；daily SQLite/Excel/vector 更新不暴露成 agent 可觸發 tool。
**隱私與設定**:
- 原始 ZIP、解壓 source、真實 endpoint/action/欄位名稱不得進 git 或 artifacts
- repo 只提供 generic `.env.example`；實際契約值只寫 ignored `.env`
- provider 只有 URL/action/operation/search/output allowlists 全部設定時才註冊
**安全與擴展性**:
- endpoint 必須是 credential-free HTTPS，TLS 預設驗證且不跟 redirects
- SOAP operation 驗證 XML name，response 使用 defused XML parser
- full snapshot 設 byte/record limits 與 TTL cache，避免每次 compound query 重抓
- query 只能搜尋 allowlisted fields，回傳只能投影 allowlisted output fields
- daily materialized SQLite 若要供 agent 查詢，沿用既有 `mode=ro` SQL provider
**理由**:
- MCP 查詢層應維持 read-mostly、bounded、可平行失敗隔離
- 寫入/atomic swap/vector rebuild 是 ops workflow，不應讓 agent 取得任意刷新權限

### DEC-027: README 與 Memory Bank 使用 repo-native 架構圖
**日期**: 2026-07-24
**決策**: 雙語 README 共用兩張版本控制內的 accessible SVG，並以 Mermaid
呈現 bounded fan-out、FHIR 相容性檢查與 citation-ready 文件調閱 sequence；
Memory Bank 同步升級為目前 35-tool gateway 架構。
**原因**:
- SVG 適合產品總覽與固定視覺層級，可在 GitHub 直接顯示且不依賴外部圖片服務
- Mermaid 適合會隨程式變動的流程，review 時可直接檢查文字 diff
- 雙語 README 共用視覺資產，避免架構圖在兩個入口各自漂移
**可維護性與隱私**:
- SVG 僅使用原生元素、內嵌樣式、`title`/`desc`，不含 script 或 remote asset
- 圖與文件只描述 generic WCF/FHIR/connector boundary，不含私有 endpoint、action、
  field contract、credential 或 archive 內容
- 架構變更需同步 README、`architect.md`、`systemPatterns.md` 與 decision log

---
*Last updated: 2026-07-24*
