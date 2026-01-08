# 處方執行功能整合計畫

> 將 `mcp-med-prescribe` 的處方執行功能整併到 `pharmacy-mcp`

---

## 📊 現有架構分析

### 現有檔案結構
```
pharmacy-mcp/
├── src/pharmacy_mcp/
│   ├── application/services/     # 應用服務層
│   │   ├── dosage.py            # ✅ 劑量計算 (CrCl, BSA, 兒童, 體重)
│   │   ├── drug_info.py         # ✅ 藥品資訊 (FDA label)
│   │   ├── drug_search.py       # ✅ 藥品搜尋 (RxNorm)
│   │   ├── interaction.py       # ✅ 交互作用檢查
│   │   └── taiwan_drug.py       # ✅ 台灣健保/TFDA
│   │
│   ├── domain/                   # 領域層
│   │   ├── entities/            # Drug, Interaction
│   │   └── value_objects/       # Dosage, Severity
│   │
│   ├── infrastructure/api/       # 外部 API
│   │   ├── rxnorm.py            # ✅ RxNorm API
│   │   ├── fda.py               # ✅ openFDA API
│   │   ├── tfda.py              # ✅ 台灣 TFDA
│   │   └── nhi.py               # ✅ 台灣健保
│   │
│   └── presentation/            # MCP Server
│       └── server.py            # 19 個 Tools
```

### 現有 MCP Tools (19 個)
| 類別 | Tools | 狀態 |
|------|-------|------|
| 搜尋 | `search_drug` | ✅ |
| 資訊 | `get_drug_info`, `get_drug_dosage`, `get_drug_warnings` | ✅ |
| 交互作用 | `check_drug_interaction`, `check_multi_drug_interactions`, `check_food_drug_interaction` | ✅ |
| 劑量計算 | `calculate_dose_by_weight`, `calculate_dose_by_bsa`, `calculate_creatinine_clearance`, `calculate_pediatric_dose`, `calculate_infusion_rate`, `convert_dose_units` | ✅ |
| 台灣 | `search_tfda_drug`, `get_nhi_coverage`, `get_nhi_drug_price`, `translate_drug_name`, `list_prior_authorization_drugs`, `list_nhi_coverage_rules` | ✅ |

---

## 🆕 新增功能規劃

### 新增 Tools (5 個)

| Tool | 描述 | 類型 |
|------|------|------|
| `get_formulary_options` | 查詢院內可開立藥品選項 | Query |
| `get_dosing_recommendations` | 取得建議用法用量 | Query |
| `generate_prescription_plan` | 產生處方計畫 | Plan |
| `submit_prescription` | 確認開立處方 (寫入 HIS) | Action |
| `discontinue_order` | 停止醫囑 | Action |

### 新增檔案

```
pharmacy-mcp/
├── src/pharmacy_mcp/
│   ├── application/services/
│   │   ├── ... (existing)
│   │   └── prescription.py      # 🆕 處方服務
│   │
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── ... (existing)
│   │   │   └── prescription.py  # 🆕 處方實體
│   │   └── value_objects/
│   │       ├── ... (existing)
│   │       └── order.py         # 🆕 醫囑值物件
│   │
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── ... (existing)
│   │   │   └── his_mock.py      # 🆕 HIS Mock API
│   │   └── knowledge/           # 🆕 知識庫
│   │       ├── __init__.py
│   │       ├── renal_dosing.py  # 腎功能調整規則
│   │       └── common_regimens.py # 常見處方組合
│   │
│   └── data/                    # 🆕 靜態資料
│       ├── formulary.json       # 院內藥品檔 (mock)
│       ├── renal_adjustments.json
│       └── regimens.json
```

---

## 📋 新增 Domain Models

### 1. Prescription Entity
```python
# domain/entities/prescription.py
@dataclass
class Prescription:
    """處方實體"""
    prescription_id: str
    patient_id: str
    drug_code: str
    drug_name: str
    
    # 劑量
    dose_value: float
    dose_unit: str  # mg, g, ml
    route: str      # PO, IV, IM, SC
    frequency: str  # QD, BID, TID, Q8H
    
    # 期間
    start_time: datetime
    duration_days: int
    prn: bool = False
    prn_reason: str | None = None
    
    # 狀態
    status: PrescriptionStatus = PrescriptionStatus.DRAFT
    
    # 追蹤
    created_by: str
    created_at: datetime
    order_id: str | None = None  # HIS order ID (after submit)
```

### 2. Order Value Object
```python
# domain/value_objects/order.py
class OrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class OrderResult:
    """醫囑執行結果"""
    status: Literal["SUCCESS", "FAILED", "BLOCKED", "PENDING"]
    order_id: str | None = None
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    blocked_reason: str | None = None
    can_override: bool = False
```

---

## 🔧 新增 Services

### PrescriptionService
```python
# application/services/prescription.py
class PrescriptionService:
    """處方服務 - 整合查詢、規劃、執行"""
    
    def __init__(
        self,
        drug_info: DrugInfoService,
        dosage: DosageService,
        interaction: InteractionService,
        knowledge: KnowledgeService,
        his_client: HISClient,
    ):
        ...
    
    # === Query Tools ===
    async def get_formulary_options(
        self,
        keyword: str,
        route_filter: str | None = None,
    ) -> list[FormularyItem]:
        """查詢院內可開立藥品"""
        ...
    
    async def get_dosing_recommendations(
        self,
        drug_code: str,
        indication: str | None = None,
        patient_context: PatientContext | None = None,
    ) -> DosingRecommendation:
        """取得建議用法用量"""
        # 整合：FDA label + 知識庫 + 腎功能調整
        ...
    
    # === Plan Tools ===
    async def generate_prescription_plan(
        self,
        drug_code: str,
        dose: str,
        route: str,
        frequency: str,
        duration_days: int = 7,
        patient_id: str | None = None,
    ) -> PrescriptionPlan:
        """產生處方計畫（驗證 + 警告）"""
        ...
    
    # === Action Tools ===
    async def submit_prescription(
        self,
        plan_id: str,
        physician_id: str,
        override_warnings: bool = False,
    ) -> OrderResult:
        """確認開立處方"""
        ...
    
    async def discontinue_order(
        self,
        order_id: str,
        reason: str,
    ) -> OrderResult:
        """停止醫囑"""
        ...
```

---

## 📊 資料來源整合

### 現有 (可直接使用)
| 資料 | 來源 | Service |
|------|------|---------|
| 藥品搜尋 | RxNorm API | DrugSearchService |
| 藥品標籤 | openFDA API | DrugInfoService |
| 劑量計算 | 內建公式 | DosageService |
| 交互作用 | FDA + 內建 | InteractionService |
| 台灣藥品 | TFDA + NHI | TaiwanDrugService |

### 需新增
| 資料 | 來源 | 說明 |
|------|------|------|
| 院內藥品檔 | Mock JSON | 模擬院內 formulary |
| 腎功能調整 | 知識庫 JSON | 手動建立 Top 30 藥物 |
| 常見處方 | 知識庫 JSON | 常見組合建議 |
| HIS 接口 | Mock API | 模擬寫入/查詢 |

---

## 🚀 實作階段

### Phase 1: Domain + Data (今天)
- [ ] 建立 `domain/entities/prescription.py`
- [ ] 建立 `domain/value_objects/order.py`
- [ ] 建立 `data/formulary.json` (Mock 院內藥品)
- [ ] 建立 `data/renal_adjustments.json` (Top 10 藥物)

### Phase 2: Infrastructure (Day 2)
- [ ] 建立 `infrastructure/api/his_mock.py`
- [ ] 建立 `infrastructure/knowledge/` 模組

### Phase 3: Service (Day 3)
- [ ] 建立 `application/services/prescription.py`
- [ ] 整合現有 services

### Phase 4: MCP Tools (Day 4)
- [ ] 新增 5 個 Tools 到 `server.py`
- [ ] 測試完整流程

### Phase 5: 測試 + 文檔 (Day 5)
- [ ] 單元測試
- [ ] 更新 README
- [ ] 更新 ROADMAP

---

## 📝 決議

| 決議 | 說明 |
|------|------|
| 整併到 pharmacy-mcp | 共用現有 API clients 和 services |
| Plan-First 模式 | Query → Plan → Action 三階段 |
| Mock HIS | 先用 Mock，之後可替換真實 API |
| 知識庫手動建立 | 先做 Top 30 常用藥物 |

---

## 🔗 相關文件

- [SPEC.md](../mcp-med-prescribe/SPEC.md) - 原始規格
- [ROADMAP.md](./ROADMAP.md) - 版本規劃
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架構說明

---

*Created: 2026-01-08*
