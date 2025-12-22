# CLAUDE.md - Claude Code 專案指引

此文件為 Claude Code（Anthropic 的 AI 編程助手）提供專案上下文。
當使用 Claude Code 時，它會自動讀取此文件以了解專案規範。

---

## 專案概述

**藥品資訊 MCP Server** - 一個完整的藥品查詢、資訊取得、劑量計算、交互作用檢查的 Model Context Protocol Server。

## 法規層級

1. **憲法** (`CONSTITUTION.md`) - 最高原則
2. **子法** (`.github/bylaws/`) - 特定領域規範
3. **Skills** (`.claude/skills/`) - 可組合技能

---

## 核心原則

### 1. MCP Server 開發
- 所有功能透過 MCP Tools 提供
- 使用 `mcp` Python SDK
- Tool 必須有清楚的描述和參數說明

### 2. Python 環境（uv 優先）
```bash
# 初始化
uv venv && uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff mypy
```

### 3. Memory Bank 同步
每次重要操作必須更新：
- `memory-bank/progress.md` - 進度追蹤
- `memory-bank/activeContext.md` - 當前焦點
- `memory-bank/decisionLog.md` - 重要決策

### 4. Git 工作流
提交前執行檢查清單：
1. Memory Bank 同步
2. README 更新（如需要）
3. CHANGELOG 更新

---

## 可用 Skills

| Skill | 用途 |
|-------|------|
| `memory-updater` | Memory Bank 同步 |
| `memory-checkpoint` | 記憶檢查點 |
| `readme-updater` | README 智能更新 |
| `changelog-updater` | CHANGELOG 自動更新 |
| `code-reviewer` | 程式碼審查 |
| `test-generator` | 測試生成 |

---

## 💸 Memory Checkpoint 規則

在以下情況使用 `memory-checkpoint`：
1. Summarize 對話前
2. 完成重大功能後
3. 長時間工作中斷前

---

## 常用指令

| 指令 | 動作 |
|------|------|
| 「同步 Memory」 | 更新 memory-bank |
| 「checkpoint」 | 保存當前狀態 |
| 「新增 tool X」 | 建立 MCP Tool |
| 「生成測試」 | 自動生成測試 |

---

## 目錄結構約定

```
src/pharmacy_mcp/
├── domain/              # 領域層 - 純業務邏輯
│   ├── entities/        # 實體
│   └── value_objects/   # 值物件
├── application/         # 應用層 - 用例
├── infrastructure/      # 基礎設施 - 外部服務
│   ├── api/             # API 客戶端
│   └── cache/           # 快取
└── presentation/        # 呈現層 - MCP Tools
    └── tools/           # Tool 定義
```

---

## 注意事項

1. **藥品資訊免責**：所有藥品資訊必須附帶免責聲明
2. **API Rate Limit**：注意 FDA、RxNorm API 限制
3. **快取策略**：藥品資訊可快取 24 小時
4. **錯誤處理**：API 失敗時應優雅降級

---

*Updated: 2025-12-22*
