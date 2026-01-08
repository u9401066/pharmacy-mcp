# Copilot 自定義指令

> 此文件整合 AGENTS.md 和 CLAUDE.md 內容，為 VS Code Copilot 和 Claude Code 提供統一指引

---

## 開發哲學 💡

> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
>
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

- 不要另開檔案寫筆記，直接寫進 Memory Bank
- 今天的零散測試，就是明天的回歸測試

---

## 專案概述

**藥品資訊 MCP Server v0.8.0** - 透過 Model Context Protocol 提供完整藥品功能。

| 指標 | 數值 |
|------|------|
| 版本 | v0.8.0 |
| MCP Tools | 19 個 |
| 測試數量 | 43 個 (全部通過) |
| 藥名對照 | 120+ 藥品 |
| 健保規則 | 60+ 藥品 |

---

## 法規遵循

你必須遵守以下法規層級：

```
CONSTITUTION.md          ← 最高原則（不可違反）
  │
  ├── .github/bylaws/    ← 子法（細則規範）
  │     ├── ddd-architecture.md
  │     ├── git-workflow.md
  │     ├── memory-bank.md
  │     └── python-environment.md
  │
  └── .claude/skills/    ← 實施細則（操作程序）
```

---

## 架構原則

- 採用 **DDD (Domain-Driven Design)**
- **DAL (Data Access Layer) 必須獨立**
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`
- 參見子法：`.github/bylaws/ddd-architecture.md`

### 目錄結構約定

```
src/pharmacy_mcp/
├── domain/              # 領域層 - 純業務邏輯（無外部依賴）
│   ├── entities/        # 實體
│   └── value_objects/   # 值物件
├── application/         # 應用層 - 用例編排
│   └── services/        # 應用服務
├── infrastructure/      # 基礎設施 - 外部服務
│   ├── api/             # API 客戶端 (FDA, RxNorm, TFDA)
│   └── cache/           # 快取
└── presentation/        # 呈現層 - MCP Tools
    └── server.py        # MCP Server 定義
```

---

## Python 環境（uv 優先）

- **優先使用 uv** 管理套件和虛擬環境
- 專案使用 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff mypy
```

參見子法：`.github/bylaws/python-environment.md`

---

## MCP 開發規則

- 所有 Tool 定義在 `src/pharmacy_mcp/presentation/server.py`
- Tool 函數必須使用 type hints
- Tool 描述必須清楚說明參數和回傳值
- 台灣相關 Tools 使用 TaiwanDrugService

### 可用 MCP Tools (19 個)

#### 基礎功能 (13 個)
- `search_drug` - 藥品搜尋
- `get_drug_info` - 藥品資訊（含台灣資訊）
- `get_drug_dosage` - 劑量資訊
- `get_drug_warnings` - 警告資訊
- `check_drug_interaction` - 藥物交互作用
- `check_multi_drug_interactions` - 多藥物交互作用
- `check_food_drug_interaction` - 食品藥物交互
- `calculate_dose_by_weight` - 體重劑量計算
- `calculate_dose_by_bsa` - BSA 劑量計算
- `calculate_creatinine_clearance` - 腎功能計算
- `calculate_pediatric_dose` - 小兒劑量
- `calculate_infusion_rate` - 輸液速率
- `convert_dose_units` - 劑量單位轉換

#### 台灣功能 (6 個) 🇹🇼
- `search_tfda_drug` - TFDA 藥品查詢
- `get_nhi_coverage` - 健保給付查詢
- `get_nhi_drug_price` - 健保藥價查詢
- `translate_drug_name` - 中英藥名對照
- `list_prior_authorization_drugs` - 事前審查清單
- `list_nhi_coverage_rules` - 健保給付規則

---

## Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|----------|
| 完成任務 | `progress.md` (Done) |
| 開始任務 | `progress.md` (Doing), `activeContext.md` |
| 重大決策 | `decisionLog.md` |
| 架構變更 | `architect.md` |

參見子法：`.github/bylaws/memory-bank.md`

---

## Git 工作流

提交前必須執行檢查清單：
1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

參見子法：`.github/bylaws/git-workflow.md`
觸發 Skill：`git-precommit`

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

| Skill | 用途 |
|-------|------|
| `git-precommit` | Git 提交前編排器 |
| `ddd-architect` | DDD 架構輔助與檢查 |
| `code-refactor` | 主動重構與模組化 |
| `memory-updater` | Memory Bank 同步 |
| `memory-checkpoint` | 記憶檢查點（Summarize 前外部化） |
| `readme-updater` | README 智能更新 |
| `changelog-updater` | CHANGELOG 自動更新 |
| `roadmap-updater` | ROADMAP 狀態追蹤 |
| `code-reviewer` | 程式碼審查 |
| `test-generator` | 測試生成（Unit/Integration/E2E） |
| `project-init` | 專案初始化 |

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機
1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令
```
「記憶檢查點」「checkpoint」「存檔」
「保存記憶」「sync memory」
```

### 必須記錄
- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 常用指令

| 指令 | 動作 |
|------|------|
| 「準備 commit」 | 執行完整提交流程 |
| 「快速 commit」 | 只同步 Memory Bank |
| 「建立新功能 X」 | 生成 DDD 結構 |
| 「review 程式碼」 | 程式碼審查 |
| 「更新 memory bank」 | 同步專案記憶 |
| 「checkpoint」 | 保存當前狀態 |
| 「新增 tool X」 | 建立 MCP Tool |
| 「生成測試」 | 自動生成測試 |

---

## 測試規則

- 測試放在 `tests/` 目錄
- API 測試必須使用 Mock
- 執行測試: `uv run pytest tests/ -v`

---

## 注意事項

1. **藥品資訊免責**：所有藥品資訊必須附帶免責聲明
2. **API Rate Limit**：注意 FDA、RxNorm API 限制
3. **快取策略**：藥品資訊可快取 24 小時
4. **錯誤處理**：API 失敗時應優雅降級
5. **程式碼風格**：遵循 PEP 8，使用 type hints
6. **語言風格**：繁體中文優先，程式碼註解用英文

---

## 🔬 Zotero + PubMed MCP 工具

> 此區塊為 Zotero + PubMed MCP Extension 自動生成

### Zotero Keeper
管理 Zotero 書目庫的工具：
- 文獻搜尋與瀏覽
- PubMed 文獻匯入
- Collection 管理

### PubMed Search
搜尋醫學文獻的工具：
- 文獻搜尋（支援 PICO 策略）
- 引用分析
- 全文連結取得

### 核心工作流程

#### 🔍 搜尋新文獻
1. 使用 `parse_pico` 分析研究問題
2. 使用 `generate_search_queries` 產生搜尋策略
3. 使用 `search_literature` 搜尋 PubMed
4. 結果自動快取，用 `get_session_pmids` 取回

#### 📥 匯入到 Zotero
**重要**: 匯入前必須詢問用戶要存入哪個 Collection！

1. 使用 `list_collections` 取得 Collection 列表
2. 詢問用戶選擇 Collection
3. 使用 `quick_import_pmids` 或 `batch_import_from_pubmed` 匯入

---

*Updated: 2026-01-08 (v0.8.0)*
