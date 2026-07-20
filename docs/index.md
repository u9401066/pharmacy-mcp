# 一個入口，查完整的藥品知識

<div class="pharmacy-hero" markdown>

Pharmacy MCP 是一個 **MCP server + agent harness**。它把公共藥品 API、台灣
TFDA/NHI、醫院 FHIR/庫存、SQLite、向量搜尋、文件與固定 Web 資料整合成
`query_pharmacy` 單一入口，另提供可信任 PK/DDI 模擬，並以可驗證的
`QueryResponse` 回傳。

[5 分鐘開始使用](agent-harness.md){ .md-button .md-button--primary }
[查看資料來源](data-sources.md){ .md-button }

</div>

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } **穩定的 Agent 輸出**

    ---

    MCP `outputSchema`、七欄固定 envelope、deterministic renderer，以及
    `pharmacy-query-contract` prompt 共同防止格式漂移。

-   :material-source-branch:{ .lg .middle } **多來源、可追溯**

    ---

    每個 provider 保留來源 URI、版本、warning 與 error；單一來源失敗時，
    已成功資料仍以 `partial` 回傳。

-   :material-flag:{ .lg .middle } **台灣健保整合**

    ---

    官方 NHI 月資料建立版本化 SQLite 索引，和 TFDA、給付規則在同一查詢內
    合併，支援健保碼、藥價、ATC 與有效日期。

-   :material-hospital-building:{ .lg .middle } **院內預設接軌**

    ---

    設定 endpoint 即可啟用 read-only FHIR R4/R5 藥品、醫囑、調劑和
    Inventory/Supply 查詢；組織資料連接器採 operator allowlist。

</div>

## 快速查詢

=== "MCP tool"

    ```json
    {
      "query": "warfarin",
      "capabilities": ["identity", "label", "reimbursement", "formulary"],
      "sources": ["rxnorm", "dailymed", "tw-tfda", "tw-nhi", "local-formulary"],
      "limit": 10,
      "output_format": "json_compact",
      "locale": "zh-TW"
    }
    ```

=== "CLI"

    ```bash
    uv run pharmacy-query warfarin \
      --source local-formulary \
      --capability formulary \
      --format json_compact
    ```

=== "Python"

    ```python
    response = await PharmacyHarness().query(
        "warfarin",
        capabilities=["formulary"],
        sources=["local-formulary"],
        output_format="json_compact",
    )
    ```

## 統一資料流

```text
MCP client / Python agent / CLI
               │
               ▼
        query_pharmacy
               │
               ▼
  capability + source routing
               │
    ┌──────────┼───────────┬───────────┐
    ▼          ▼           ▼           ▼
 public API  TFDA/NHI  FHIR/inventory  org data
    └──────────┴───────────┴───────────┘
               │
               ▼
 QueryResponse v1.0 + provenance
```

!!! warning "臨床安全界線"
    本專案提供參考資料整合與可追溯查詢，不取代藥師、醫師或經核准的臨床
    決策支援系統。公開資料的缺漏與延遲會如實保留在 warnings/errors。

## 目前可直接使用

- RxNorm/RxClass、openFDA、DailyMed、PubChem、MedlinePlus Connect
- 台灣 TFDA 與健保署官方藥品項目月資料
- FHIR R4/R5 medication、patient order/dispense、inventory/supply
- PDF、DOC/DOCX、CSV、XLS/XLSX、Markdown、text
- read-only SQLite、vendor-neutral vector gateway、固定 HTTPS 文件
- 原有劑量、交互作用、院內 formulary 與處方 workflow tools
- 具來源、假設、限制與驗證 fixtures 的 PK/DDI formula/simulation tools

需要商業授權的 DrugBank、FDB 與 Micromedex 只列入 catalog，不會被靜默
抓取或假裝已啟用。
