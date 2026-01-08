# 處方執行功能整合計畫

> 將 `mcp-med-prescribe` 的處方執行功能整併到 `pharmacy-mcp`

---

## 🎯 設計原則

### 目標 Agent 類型
本 MCP Server 設計給 **低階自動化 Agent** 使用（如 LangGraph Auto Workflow），而非高階對話式 Agent。

```
設計原則：
✅ 原子化 - 每個 Tool 做一件事
✅ 無狀態 - 狀態由外部 workflow 管理
✅ 確定性 - 固定 input → 固定 output
✅ 可組合 - 由 workflow 編排多個 tools
❌ 避免 - 複雜 session、多步驟整合、需要「思考」的操作
```

### 架構分層

```
┌─────────────────────────────────────────────────────┐
│  MCP Server (提供原子操作)                           │
│                                                     │
│  Query Tools          Calculate Tools               │
│  ├─ search_drug       ├─ calculate_dose_by_weight  │
│  ├─ get_drug_info     ├─ calculate_dose_by_bsa     │
│  ├─ get_formulary     └─ calculate_crcl            │
│  └─ get_renal_adjust                               │
│                                                     │
│  Check Tools          Action Tools                  │
│  ├─ check_interaction ├─ submit_order              │
│  ├─ check_multi_inter └─ stop_order                │
│  └─ validate_order                                 │
└─────────────────────────────────────────────────────┘
                    ↑ 呼叫
                    │
┌─────────────────────────────────────────────────────┐
│  LangGraph Workflow (編排 + 狀態管理)               │
│                                                     │
│  ┌────────┐    ┌────────┐    ┌────────┐            │
│  │ search │───▶│get_info│───▶│calc_crcl│           │
│  └────────┘    └────────┘    └────────┘            │
│       │              │              │               │
│       ▼              ▼              ▼               │
│  ┌─────────────────────────────────────┐           │
│  │         Graph State                  │           │
│  │  { drug, info, crcl, orders: [] }   │           │
│  └─────────────────────────────────────┘           │
│       │                                             │
│       ▼                                             │
│  ┌────────┐    ┌────────┐    ┌────────┐            │
│  │ adjust │───▶│validate│───▶│ submit │            │
│  └────────┘    └────────┘    └────────┘            │
└─────────────────────────────────────────────────────┘
```

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

### 新增 Tools (6 個) - 原子化設計

#### 查詢類（Query）- 無狀態，單純回傳

| Tool | 描述 | Input | Output |
|------|------|-------|--------|
| `search_drug` | 擴展：新增 `source` 參數 | `query`, `source=rxnorm\|formulary\|both` | `list[DrugResult]` |
| `get_formulary_item` | 取得院內藥品詳情 | `drug_code` | `FormularyItem` |
| `get_renal_adjustment` | 取得腎功能劑量調整 | `drug_code`, `crcl` | `RenalAdjustment` |

#### 檢查類（Check）- 驗證用

| Tool | 描述 | Input | Output |
|------|------|-------|--------|
| `validate_order` | 驗證單一醫囑項目 | `drug_code`, `dose`, `route`, `frequency`, `patient_crcl?` | `ValidationResult` |

#### 執行類（Action）- 原子動作

| Tool | 描述 | Input | Output |
|------|------|-------|--------|
| `submit_order` | 送出單一醫囑 | `patient_id`, `drug_code`, `dose`, `route`, `frequency`, `duration_days`, `physician_id` | `OrderResult` |
| `stop_order` | 停止醫囑 | `order_id`, `reason` | `StopResult` |

### 新增檔案結構

```
pharmacy-mcp/
├── src/pharmacy_mcp/
│   ├── application/services/
│   │   ├── ... (existing)
│   │   └── prescription.py      # 🆕 處方服務（原子操作）
│   │
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── ... (existing)
│   │   │   └── order.py         # 🆕 醫囑實體
│   │   └── value_objects/
│   │       ├── ... (existing)
│   │       └── order_result.py  # 🆕 醫囑結果值物件
│   │
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── ... (existing)
│   │   │   └── his_mock.py      # 🆕 HIS Mock API
│   │   └── knowledge/           # 🆕 知識庫
│   │       ├── __init__.py
│   │       ├── formulary.py     # 院內藥品檔
│   │       └── renal_dosing.py  # 腎功能調整規則
│   │
│   └── data/                    # 🆕 靜態資料
│       ├── formulary.json       # 院內藥品檔 (mock)
│       └── renal_adjustments.json
│
├── examples/                    # 🆕 範例模組
│   └── langgraph_prescription/  # LangGraph 處方範例
│       ├── __init__.py
│       ├── workflow.py          # Workflow 定義
│       ├── nodes.py             # Node 函數
│       ├── state.py             # State 定義
│       └── demo.py              # 執行範例
```

---

## 📋 新增 Domain Models

### 1. Order Entity
```python
# domain/entities/order.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"
    CANCELLED = "cancelled"

@dataclass
class Order:
    """醫囑實體（單一藥品）"""
    order_id: str
    patient_id: str
    drug_code: str
    drug_name: str
    
    # 劑量
    dose_value: float
    dose_unit: str      # mg, g, ml
    route: str          # PO, IV, IM, SC
    frequency: str      # QD, BID, TID, Q8H
    duration_days: int
    
    # 狀態
    status: OrderStatus = OrderStatus.PENDING
    
    # 追蹤
    physician_id: str
    created_at: datetime
    discontinued_at: datetime | None = None
    discontinue_reason: str | None = None
```

### 2. Order Result Value Object
```python
# domain/value_objects/order_result.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class ValidationResult:
    """醫囑驗證結果"""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_adjustments: dict | None = None

@dataclass(frozen=True)
class OrderResult:
    """醫囑執行結果"""
    success: bool
    order_id: str | None = None
    message: str = ""
    errors: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class StopResult:
    """停止醫囑結果"""
    success: bool
    message: str = ""
```

---

## 🔧 新增 Services

### PrescriptionService（原子操作）
```python
# application/services/prescription.py
class PrescriptionService:
    """處方服務 - 提供原子操作給 MCP Tools"""
    
    def __init__(
        self,
        formulary: FormularyKnowledge,
        renal_dosing: RenalDosingKnowledge,
        his_client: HISClient,
    ):
        self.formulary = formulary
        self.renal_dosing = renal_dosing
        self.his_client = his_client
    
    # === Query ===
    async def get_formulary_item(
        self,
        drug_code: str,
    ) -> FormularyItem | None:
        """取得院內藥品詳情"""
        return self.formulary.get_item(drug_code)
    
    async def get_renal_adjustment(
        self,
        drug_code: str,
        crcl: float,
    ) -> RenalAdjustment:
        """取得腎功能劑量調整建議"""
        return self.renal_dosing.get_adjustment(drug_code, crcl)
    
    # === Check ===
    async def validate_order(
        self,
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        patient_crcl: float | None = None,
    ) -> ValidationResult:
        """驗證單一醫囑"""
        errors = []
        warnings = []
        suggested = None
        
        # 1. 檢查藥品是否存在
        item = self.formulary.get_item(drug_code)
        if not item:
            errors.append(f"藥品代碼 {drug_code} 不存在於院內藥品檔")
            return ValidationResult(valid=False, errors=errors)
        
        # 2. 檢查給藥途徑
        if route not in item.available_routes:
            errors.append(f"給藥途徑 {route} 不適用於此藥品")
        
        # 3. 檢查劑量範圍
        if dose < item.min_dose or dose > item.max_dose:
            warnings.append(f"劑量 {dose}{dose_unit} 超出建議範圍 ({item.min_dose}-{item.max_dose})")
        
        # 4. 腎功能調整
        if patient_crcl is not None:
            adj = self.renal_dosing.get_adjustment(drug_code, patient_crcl)
            if adj.needs_adjustment:
                warnings.append(f"CrCl={patient_crcl}: {adj.recommendation}")
                suggested = {"adjusted_dose": adj.suggested_dose}
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggested_adjustments=suggested,
        )
    
    # === Action ===
    async def submit_order(
        self,
        patient_id: str,
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        duration_days: int,
        physician_id: str,
        override_warnings: bool = False,
    ) -> OrderResult:
        """送出單一醫囑到 HIS"""
        # 1. 先驗證
        validation = await self.validate_order(
            drug_code, dose, dose_unit, route, frequency
        )
        
        if not validation.valid:
            return OrderResult(
                success=False,
                errors=validation.errors,
                message="驗證失敗",
            )
        
        if validation.warnings and not override_warnings:
            return OrderResult(
                success=False,
                errors=[f"有警告需確認: {validation.warnings}"],
                message="請設定 override_warnings=True 以忽略警告",
            )
        
        # 2. 送出到 HIS
        result = await self.his_client.create_order(
            patient_id=patient_id,
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            duration_days=duration_days,
            physician_id=physician_id,
        )
        
        return OrderResult(
            success=result.success,
            order_id=result.order_id,
            message=result.message,
        )
    
    async def stop_order(
        self,
        order_id: str,
        reason: str,
    ) -> StopResult:
        """停止醫囑"""
        result = await self.his_client.discontinue_order(order_id, reason)
        return StopResult(success=result.success, message=result.message)
```

---

## 🤖 LangGraph 範例模組

### 目錄結構
```
examples/langgraph_prescription/
├── __init__.py
├── state.py          # State 定義
├── nodes.py          # Node 函數（呼叫 MCP Tools）
├── workflow.py       # Workflow 組裝
└── demo.py           # 執行範例
```

### state.py - 狀態定義
```python
"""處方 Workflow 狀態定義"""
from typing import TypedDict, Annotated
from operator import add

class PatientInfo(TypedDict):
    patient_id: str
    age: int
    weight_kg: float
    sex: str
    creatinine: float  # mg/dL

class OrderItem(TypedDict):
    drug_code: str
    drug_name: str
    dose: float
    dose_unit: str
    route: str
    frequency: str
    duration_days: int

class PrescriptionState(TypedDict):
    """處方 Workflow 狀態"""
    # 輸入
    patient: PatientInfo
    orders_to_create: list[OrderItem]
    physician_id: str
    
    # 計算結果（由 nodes 填入）
    patient_crcl: float | None
    
    # 驗證結果
    validation_results: Annotated[list[dict], add]
    
    # 交互作用檢查
    interactions: list[dict]
    
    # 最終結果
    submitted_orders: Annotated[list[dict], add]
    failed_orders: Annotated[list[dict], add]
    
    # 流程控制
    has_errors: bool
    has_warnings: bool
    user_confirmed: bool
```

### nodes.py - Node 函數
```python
"""Workflow Node 函數 - 呼叫 MCP Tools"""
from mcp import ClientSession
from .state import PrescriptionState

# MCP Client（由 workflow 初始化時注入）
mcp_client: ClientSession = None

def set_mcp_client(client: ClientSession):
    global mcp_client
    mcp_client = client

# === Node: 計算腎功能 ===
async def calculate_renal_function(state: PrescriptionState) -> dict:
    """計算病人腎功能 (CrCl)"""
    patient = state["patient"]
    
    result = await mcp_client.call_tool(
        "calculate_creatinine_clearance",
        arguments={
            "age": patient["age"],
            "weight_kg": patient["weight_kg"],
            "creatinine": patient["creatinine"],
            "sex": patient["sex"],
        }
    )
    
    crcl = result.content[0].text  # 解析結果
    return {"patient_crcl": float(crcl)}

# === Node: 驗證每個醫囑 ===
async def validate_orders(state: PrescriptionState) -> dict:
    """驗證所有待開立醫囑"""
    results = []
    has_errors = False
    has_warnings = False
    
    for order in state["orders_to_create"]:
        result = await mcp_client.call_tool(
            "validate_order",
            arguments={
                "drug_code": order["drug_code"],
                "dose": order["dose"],
                "dose_unit": order["dose_unit"],
                "route": order["route"],
                "frequency": order["frequency"],
                "patient_crcl": state.get("patient_crcl"),
            }
        )
        
        validation = parse_validation_result(result)
        results.append({
            "drug_code": order["drug_code"],
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        })
        
        if not validation["valid"]:
            has_errors = True
        if validation["warnings"]:
            has_warnings = True
    
    return {
        "validation_results": results,
        "has_errors": has_errors,
        "has_warnings": has_warnings,
    }

# === Node: 檢查交互作用 ===
async def check_interactions(state: PrescriptionState) -> dict:
    """檢查所有藥物間的交互作用"""
    drugs = [o["drug_code"] for o in state["orders_to_create"]]
    
    if len(drugs) < 2:
        return {"interactions": []}
    
    interactions = []
    # 兩兩檢查
    for i, drug_a in enumerate(drugs):
        for drug_b in drugs[i+1:]:
            result = await mcp_client.call_tool(
                "check_drug_interaction",
                arguments={"drug_a": drug_a, "drug_b": drug_b}
            )
            interaction = parse_interaction_result(result)
            if interaction["has_interaction"]:
                interactions.append(interaction)
    
    return {"interactions": interactions}

# === Node: 送出醫囑 ===
async def submit_orders(state: PrescriptionState) -> dict:
    """送出所有驗證通過的醫囑"""
    submitted = []
    failed = []
    
    for order in state["orders_to_create"]:
        # 找到對應的驗證結果
        validation = next(
            (v for v in state["validation_results"] 
             if v["drug_code"] == order["drug_code"]),
            None
        )
        
        if validation and not validation["valid"]:
            failed.append({
                "drug_code": order["drug_code"],
                "reason": "驗證失敗",
                "errors": validation["errors"],
            })
            continue
        
        result = await mcp_client.call_tool(
            "submit_order",
            arguments={
                "patient_id": state["patient"]["patient_id"],
                "drug_code": order["drug_code"],
                "dose": order["dose"],
                "dose_unit": order["dose_unit"],
                "route": order["route"],
                "frequency": order["frequency"],
                "duration_days": order["duration_days"],
                "physician_id": state["physician_id"],
                "override_warnings": state.get("user_confirmed", False),
            }
        )
        
        order_result = parse_order_result(result)
        if order_result["success"]:
            submitted.append({
                "drug_code": order["drug_code"],
                "order_id": order_result["order_id"],
            })
        else:
            failed.append({
                "drug_code": order["drug_code"],
                "reason": order_result["message"],
                "errors": order_result["errors"],
            })
    
    return {
        "submitted_orders": submitted,
        "failed_orders": failed,
    }

# === 條件判斷函數 ===
def should_proceed_after_validation(state: PrescriptionState) -> str:
    """驗證後決定下一步"""
    if state["has_errors"]:
        return "stop_with_errors"
    elif state["has_warnings"] and not state.get("user_confirmed"):
        return "wait_for_confirmation"
    else:
        return "proceed_to_submit"

# === Helper 函數 ===
def parse_validation_result(result) -> dict:
    """解析 MCP 驗證結果"""
    import json
    data = json.loads(result.content[0].text)
    return data

def parse_interaction_result(result) -> dict:
    """解析 MCP 交互作用結果"""
    import json
    data = json.loads(result.content[0].text)
    return data

def parse_order_result(result) -> dict:
    """解析 MCP 送出結果"""
    import json
    data = json.loads(result.content[0].text)
    return data
```

### workflow.py - Workflow 組裝
```python
"""處方 Workflow 定義"""
from langgraph.graph import StateGraph, END
from .state import PrescriptionState
from .nodes import (
    calculate_renal_function,
    validate_orders,
    check_interactions,
    submit_orders,
    should_proceed_after_validation,
)

def create_prescription_workflow() -> StateGraph:
    """建立處方開立 Workflow"""
    
    workflow = StateGraph(PrescriptionState)
    
    # === 新增 Nodes ===
    workflow.add_node("calc_crcl", calculate_renal_function)
    workflow.add_node("validate", validate_orders)
    workflow.add_node("check_interactions", check_interactions)
    workflow.add_node("submit", submit_orders)
    
    # === 定義邊 (Edges) ===
    
    # 起點 → 計算腎功能
    workflow.set_entry_point("calc_crcl")
    
    # 計算腎功能 → 驗證
    workflow.add_edge("calc_crcl", "validate")
    
    # 驗證 → 條件分支
    workflow.add_conditional_edges(
        "validate",
        should_proceed_after_validation,
        {
            "stop_with_errors": END,           # 有錯誤，停止
            "wait_for_confirmation": END,       # 有警告，等待確認
            "proceed_to_submit": "check_interactions",  # 繼續
        }
    )
    
    # 交互作用檢查 → 送出
    workflow.add_edge("check_interactions", "submit")
    
    # 送出 → 結束
    workflow.add_edge("submit", END)
    
    return workflow.compile()


def create_simple_workflow() -> StateGraph:
    """簡化版 Workflow（無交互檢查）"""
    
    workflow = StateGraph(PrescriptionState)
    
    workflow.add_node("calc_crcl", calculate_renal_function)
    workflow.add_node("validate", validate_orders)
    workflow.add_node("submit", submit_orders)
    
    workflow.set_entry_point("calc_crcl")
    workflow.add_edge("calc_crcl", "validate")
    workflow.add_edge("validate", "submit")
    workflow.add_edge("submit", END)
    
    return workflow.compile()
```

### demo.py - 執行範例
```python
"""LangGraph 處方 Workflow 執行範例"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .workflow import create_prescription_workflow
from .nodes import set_mcp_client
from .state import PrescriptionState

async def main():
    """執行處方開立範例"""
    
    # === 1. 連接 MCP Server ===
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "pharmacy_mcp"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 設定全域 MCP client
            set_mcp_client(session)
            
            # === 2. 建立 Workflow ===
            workflow = create_prescription_workflow()
            
            # === 3. 準備輸入狀態 ===
            initial_state: PrescriptionState = {
                "patient": {
                    "patient_id": "P001",
                    "age": 75,
                    "weight_kg": 60,
                    "sex": "male",
                    "creatinine": 1.8,  # 偏高，需要腎功能調整
                },
                "orders_to_create": [
                    {
                        "drug_code": "GENTA-INJ",
                        "drug_name": "Gentamicin 80mg/2mL",
                        "dose": 80,
                        "dose_unit": "mg",
                        "route": "IV",
                        "frequency": "Q8H",
                        "duration_days": 7,
                    },
                    {
                        "drug_code": "VANCO-INJ",
                        "drug_name": "Vancomycin 500mg",
                        "dose": 1000,
                        "dose_unit": "mg",
                        "route": "IV",
                        "frequency": "Q12H",
                        "duration_days": 14,
                    },
                ],
                "physician_id": "DR001",
                "patient_crcl": None,
                "validation_results": [],
                "interactions": [],
                "submitted_orders": [],
                "failed_orders": [],
                "has_errors": False,
                "has_warnings": False,
                "user_confirmed": False,
            }
            
            # === 4. 執行 Workflow ===
            print("=" * 50)
            print("開始執行處方開立 Workflow")
            print("=" * 50)
            
            final_state = await workflow.ainvoke(initial_state)
            
            # === 5. 顯示結果 ===
            print("\n📊 執行結果:")
            print(f"  病人 CrCl: {final_state['patient_crcl']:.1f} mL/min")
            
            print("\n✅ 驗證結果:")
            for v in final_state["validation_results"]:
                status = "✓" if v["valid"] else "✗"
                print(f"  {status} {v['drug_code']}")
                for err in v["errors"]:
                    print(f"      ❌ {err}")
                for warn in v["warnings"]:
                    print(f"      ⚠️ {warn}")
            
            if final_state["interactions"]:
                print("\n⚠️ 交互作用:")
                for inter in final_state["interactions"]:
                    print(f"  - {inter}")
            
            print("\n📝 送出結果:")
            for order in final_state["submitted_orders"]:
                print(f"  ✅ {order['drug_code']} → Order ID: {order['order_id']}")
            for order in final_state["failed_orders"]:
                print(f"  ❌ {order['drug_code']} → {order['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📊 資料來源整合

### 現有（可直接使用）
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
| 腎功能調整 | 知識庫 JSON | Top 20 需調整藥物 |
| HIS 接口 | Mock API | 模擬寫入/查詢 |

---

## 🚀 實作階段

### Phase 1: Domain + Data
- [ ] 建立 `domain/entities/order.py`
- [ ] 建立 `domain/value_objects/order_result.py`
- [ ] 建立 `data/formulary.json` (Mock 院內藥品)
- [ ] 建立 `data/renal_adjustments.json` (Top 20 藥物)

### Phase 2: Infrastructure
- [ ] 建立 `infrastructure/api/his_mock.py`
- [ ] 建立 `infrastructure/knowledge/formulary.py`
- [ ] 建立 `infrastructure/knowledge/renal_dosing.py`

### Phase 3: Service + Tools
- [ ] 建立 `application/services/prescription.py`
- [ ] 擴展 `search_drug` 加入 source 參數
- [ ] 新增 4 個 Tools 到 `server.py`

### Phase 4: LangGraph 範例
- [ ] 建立 `examples/langgraph_prescription/` 目錄
- [ ] 實作 state.py, nodes.py, workflow.py
- [ ] 實作 demo.py 並測試

### Phase 5: 測試 + 文檔
- [ ] 單元測試
- [ ] 整合測試（Workflow 端到端）
- [ ] 更新 README
- [ ] 更新 ROADMAP

---

## 📝 設計決議

| 決議 | 說明 | 日期 |
|------|------|------|
| 原子化設計 | 每個 Tool 做一件事，無狀態 | 2026-01-08 |
| 狀態外部管理 | 由 LangGraph 管理，非 MCP Session | 2026-01-08 |
| 提供範例模組 | `examples/langgraph_prescription/` | 2026-01-08 |
| Mock HIS | 先用 Mock，之後可替換真實 API | 2026-01-08 |
| 目標 Agent | 低階 Auto Workflow Agent (LangGraph) | 2026-01-08 |

---

## 🔗 相關文件

- [ROADMAP.md](./ROADMAP.md) - 版本規劃
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架構說明
- [.github/bylaws/ddd-architecture.md](.github/bylaws/ddd-architecture.md) - DDD 子法

---

*Created: 2026-01-08*
*Updated: 2026-01-08 - 改為原子化設計 + LangGraph 範例*
