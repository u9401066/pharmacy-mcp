# Product Context

## 📋 專案概述

**專案名稱**：藥品資訊 MCP Server (Pharmacy MCP)

**一句話描述**：透過 Model Context Protocol 提供完整藥品查詢、資訊取得、劑量計算、交互作用檢查的 AI 工具。

**目標用戶**：
- 醫療專業人員
- 藥師
- 開發 AI 醫療應用的工程師

## 🏗️ 架構

```
MCP Server
├── Presentation (MCP Tools)
├── Application (Services)
├── Domain (Entities, Value Objects)
└── Infrastructure (API Clients, Cache)
```

### 分層架構 (DDD)

```
Presentation → Application → Domain ← Infrastructure
```

## ✨ 核心功能

- 🔍 藥品查詢 (RxNorm)
- 📋 藥品資訊 (FDA, DailyMed)
- 🧮 劑量計算
- ⚠️ 交互作用檢查
- 🍎 食品藥品衝突

## 🔧 技術棧

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.11+ |
| 套件管理 | uv |
| MCP SDK | mcp |
| HTTP | httpx (async) |
| 驗證 | Pydantic v2 |
| 快取 | diskcache |
| Linting | Ruff, MyPy, Bandit |
| 測試 | pytest |

## 📦 依賴

### 核心依賴
- mcp >= 1.0.0
- httpx >= 0.27.0
- pydantic >= 2.5.0
- diskcache >= 5.6.0

### 開發依賴
- pytest, pytest-cov, pytest-asyncio
- ruff, mypy, bandit

---
*Last updated: 2025-12-22*
