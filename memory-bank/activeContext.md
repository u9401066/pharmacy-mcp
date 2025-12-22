# Active Context

## 🎯 當前焦點

- v0.1.1 版本發布準備
- 修復 RxNorm Drug Interaction API 停用問題

## 📝 最近完成的變更

| 檔案 | 變更內容 |
|------|----------|
| `infrastructure/api/rxnorm.py` | 移除對已停用 API 的呼叫 |
| `application/services/interaction.py` | 新增本地藥物交互作用資料庫 |
| `CHANGELOG.md` | 更新版本記錄 |

## ⚠️ 已知限制

- RxNorm Drug Interaction API 已停用（2025 年 NLM 政策變更）
- 藥物交互作用資料現由本地資料庫 + FDA 標籤提供
- 本地資料庫僅包含 25+ 種常見交互作用，非完整資料

## 💡 重要決定

- 新增本地藥物交互作用資料庫作為備用方案
- 保持 API 回應格式一致，加入 `source` 和 `note` 說明
- 使用 httpx 作為 HTTP client（支援 async）
- 使用 diskcache 作為快取層

## 📁 相關檔案

```
src/pharmacy_mcp/
├── domain/
├── application/
│   └── services/
│       └── interaction.py  # 新增本地資料庫
├── infrastructure/
│   └── api/
│       └── rxnorm.py       # 修改 API 呼叫
└── presentation/
```

## 🔜 下一步

- 尋找替代的藥物交互作用 API（DrugBank）
- 擴充本地資料庫
- Git commit 並發布 v0.1.1

---
*Last updated: 2025-12-22*
