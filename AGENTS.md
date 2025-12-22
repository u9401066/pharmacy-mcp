# AGENTS.md - VS Code Copilot Agent 指引

此文件為 VS Code GitHub Copilot 的 Agent Mode 提供專案上下文。

---

## 專案規則

**藥品資訊 MCP Server** - 透過 Model Context Protocol 提供完整藥品功能。

### Python 環境規則

- **優先使用 uv** 管理套件和虛擬環境
- 專案使用 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

### MCP 開發規則

- 所有 Tool 必須在 `src/pharmacy_mcp/presentation/tools/` 定義
- Tool 函數必須使用 type hints
- Tool 描述必須清楚說明參數和回傳值

### 測試規則

- 單元測試放在 `tests/unit/`
- 整合測試放在 `tests/integration/`
- API 測試必須使用 Mock

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

- **memory-updater** - Memory Bank 同步
- **memory-checkpoint** - 記憶檢查點
- **readme-updater** - README 智能更新
- **changelog-updater** - CHANGELOG 自動更新
- **code-reviewer** - 程式碼審查
- **test-generator** - 測試生成

---

## 💸 Memory Checkpoint 規則

在以下情況使用 checkpoint：
1. 完成一個功能模組
2. 重要 API 整合完成
3. 長時間工作中斷前

---

## 回應風格

- 繁體中文優先
- 程式碼註解用英文
- 遵循 PEP 8 風格
- 使用 type hints

---

*Updated: 2025-12-22*
