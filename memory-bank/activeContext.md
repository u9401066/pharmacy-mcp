# Active Context

## 🎯 當前焦點

- 完成 v0.8.6 MCP SDK 現代化與部署入口
- 以 FastMCP 提供 stdio / sse / streamable-http 三種 transport

## 📝 最近完成的變更（v0.8.6）

| 檔案 | 變更內容 |
|------|----------|
| `src/pharmacy_mcp/presentation/server.py` | 以 FastMCP 重寫 server，新增 ASGI app 與 CLI transport |
| `src/pharmacy_mcp/config.py` | 新增 MCP 部署設定 |
| `src/pharmacy_mcp/presentation/__init__.py` | 匯出 `app` 與部署 helper |
| `src/pharmacy_mcp/__init__.py` | 同步套件版本資訊 |
| `pyproject.toml` | 修正 `pharmacy-mcp` script entrypoint |
| `tests/test_server.py` | 補齊 FastMCP / Streamable HTTP / CLI 測試 |
| `README.md` | 補充新 transport 與部署文件 |
| `README.zh-TW.md` | 補充新 transport 與部署文件 |

## ✅ 驗證狀態

- `uv run pytest -v` → 75 passed
- `uv run ruff check src/pharmacy_mcp/presentation/server.py src/pharmacy_mcp/config.py src/pharmacy_mcp/presentation/__init__.py tests/test_server.py` → passed
- `uv run pharmacy-mcp --help` / `uv run python -m pharmacy_mcp --help` → passed
- `uv run mypy ...` → repository 仍有既存型別錯誤，未在本次任務處理

## 🔜 下一步

- 若要正式雲端部署，可再補 health check / auth / reverse proxy 文件
- 評估是否要把剩餘 mypy debt 納入 v0.9.0 清理
