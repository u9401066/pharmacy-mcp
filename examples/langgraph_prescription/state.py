"""處方 Workflow 狀態定義

定義 LangGraph StateGraph 使用的狀態結構。
"""

from typing import Annotated, TypedDict
from operator import add


class PatientInfo(TypedDict):
    """病人資訊"""
    
    patient_id: str
    name: str
    age: int
    weight_kg: float
    sex: str  # male / female
    creatinine: float  # mg/dL


class OrderItem(TypedDict):
    """待開立醫囑項目"""
    
    drug_code: str
    drug_name: str
    dose: float
    dose_unit: str
    route: str
    frequency: str
    duration_days: int


class ValidationInfo(TypedDict):
    """驗證結果"""
    
    drug_code: str
    valid: bool
    errors: list[str]
    warnings: list[str]


class InteractionInfo(TypedDict):
    """交互作用資訊"""
    
    drug_a: str
    drug_b: str
    severity: str
    description: str


class SubmittedOrder(TypedDict):
    """已送出醫囑"""
    
    drug_code: str
    order_id: str


class FailedOrder(TypedDict):
    """失敗醫囑"""
    
    drug_code: str
    reason: str
    errors: list[str]


class PrescriptionState(TypedDict):
    """處方 Workflow 狀態
    
    這是 LangGraph StateGraph 的狀態定義。
    
    使用 Annotated[list, add] 可讓多個 node 累加結果到同一個 list。
    
    Workflow 流程：
    1. calc_crcl: 計算病人 CrCl → 填入 patient_crcl
    2. validate: 驗證所有醫囑 → 填入 validation_results, has_errors, has_warnings
    3. check_interactions: 檢查交互作用 → 填入 interactions
    4. submit: 送出醫囑 → 填入 submitted_orders, failed_orders
    """
    
    # =========================================================================
    # 輸入（由呼叫端提供）
    # =========================================================================
    patient: PatientInfo
    orders_to_create: list[OrderItem]
    physician_id: str
    
    # =========================================================================
    # 計算結果（由 nodes 填入）
    # =========================================================================
    patient_crcl: float | None
    
    # =========================================================================
    # 驗證結果
    # =========================================================================
    validation_results: Annotated[list[ValidationInfo], add]
    
    # =========================================================================
    # 交互作用檢查
    # =========================================================================
    interactions: list[InteractionInfo]
    
    # =========================================================================
    # 最終結果
    # =========================================================================
    submitted_orders: Annotated[list[SubmittedOrder], add]
    failed_orders: Annotated[list[FailedOrder], add]
    
    # =========================================================================
    # 流程控制
    # =========================================================================
    has_errors: bool
    has_warnings: bool
    user_confirmed: bool
