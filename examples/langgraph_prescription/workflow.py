"""處方 Workflow 定義

使用 LangGraph StateGraph 組裝處方開立流程。

Workflow 流程：
    START
      │
      ▼
    calc_crcl (計算腎功能)
      │
      ▼
    validate (驗證醫囑)
      │
      ├── has_errors=True ──────────► END (錯誤停止)
      │
      ├── has_warnings=True ────────► END (等待確認)
      │   (user_confirmed=False)
      │
      └── otherwise ────────────────► check_interactions
                                          │
                                          ▼
                                       submit (送出醫囑)
                                          │
                                          ▼
                                        END
"""

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
    """建立處方開立 Workflow
    
    完整版本，包含交互作用檢查。
    
    Returns:
        編譯後的 StateGraph
    """
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
            "stop_with_errors": END,            # 有錯誤，停止
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
    """建立簡化版 Workflow
    
    不含交互作用檢查，適合快速開立單一藥物。
    
    Returns:
        編譯後的 StateGraph
    """
    workflow = StateGraph(PrescriptionState)
    
    # Nodes
    workflow.add_node("calc_crcl", calculate_renal_function)
    workflow.add_node("validate", validate_orders)
    workflow.add_node("submit", submit_orders)
    
    # Edges
    workflow.set_entry_point("calc_crcl")
    workflow.add_edge("calc_crcl", "validate")
    workflow.add_edge("validate", "submit")
    workflow.add_edge("submit", END)
    
    return workflow.compile()


def create_validation_only_workflow() -> StateGraph:
    """建立僅驗證的 Workflow
    
    只執行 CrCl 計算和驗證，不送出醫囑。
    適合用於預覽/檢查。
    
    Returns:
        編譯後的 StateGraph
    """
    workflow = StateGraph(PrescriptionState)
    
    # Nodes
    workflow.add_node("calc_crcl", calculate_renal_function)
    workflow.add_node("validate", validate_orders)
    workflow.add_node("check_interactions", check_interactions)
    
    # Edges
    workflow.set_entry_point("calc_crcl")
    workflow.add_edge("calc_crcl", "validate")
    workflow.add_edge("validate", "check_interactions")
    workflow.add_edge("check_interactions", END)
    
    return workflow.compile()
