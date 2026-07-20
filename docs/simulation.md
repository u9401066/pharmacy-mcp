# 可信任 PK/DDI 模擬

Pharmacy MCP 隨附一份版本化、唯讀的公式 catalog，用於可重現的藥動學與
藥品交互作用 screening。模擬結果仍使用 `QueryResponse` v1.0，並保留公式
ID、輸入、輸出、假設、限制與免責聲明。

## MCP tools

| Tool | 用途 |
|---|---|
| `list_formula_catalog` | 列出可信任公式與 metadata |
| `get_formula_details` | 讀取公式、參數單位、來源與驗證案例 |
| `explain_interaction_mechanism` | 說明支援的 DDI pathway 與所需參數 |
| `simulate_pk_interaction` | 以明確參數執行 CYP reversible inhibition screening |
| `simulate_concentration_time` | 執行 one-compartment 濃度時間估算 |

Formula metadata 也可透過 `pharmacy://formulas`、公式 resource template 與
`pharmacy://validation/formulas` 讀取。

## 信任邊界

- 只有 catalog 中標記為 trusted、具來源且通過 fixtures 的 implementation
  才能由 runtime 執行。
- 所有病人/藥品參數都必須由呼叫方明確提供；server 不推測未知參數。
- NaN、infinity、負值、不穩定分母與 catalog/implementation 不一致會
  fail closed。
- 計算是教育與 workflow screening，不是 PBPK 平台，也不可直接產生臨床
  處方建議。

## 新增公式

外部工具可以協助草擬公式，但不能直接注入 runtime。promotion 前必須補齊：

1. 來源與版本；
2. expression、參數名稱與單位；
3. 假設、限制及適用範圍；
4. 至少一組 deterministic validation case；
5. service implementation、測試與 reviewer 核准。

可先載入 `formula_review_checklist` MCP prompt，再依上述項目完成審查。
