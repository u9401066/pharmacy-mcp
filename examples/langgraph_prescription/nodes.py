"""Workflow Node 函數

每個 Node 函數負責：
1. 從 state 取得需要的資料
2. 呼叫對應的 MCP Tool
3. 回傳要更新到 state 的資料

設計原則：
- 每個 Node 專注做一件事
- 透過 MCP Client 呼叫 pharmacy-mcp Tools
- 不直接修改 state，而是回傳更新
"""

import json
from typing import Any

from mcp import ClientSession

from .state import (
    PrescriptionState,
    ValidationInfo,
    InteractionInfo,
    SubmittedOrder,
    FailedOrder,
)


# 全域 MCP Client（由 workflow 初始化時設定）
_mcp_client: ClientSession | None = None


def set_mcp_client(client: ClientSession) -> None:
    """設定全域 MCP Client
    
    Args:
        client: 已初始化的 MCP ClientSession
    """
    global _mcp_client
    _mcp_client = client


def get_mcp_client() -> ClientSession:
    """取得 MCP Client"""
    if _mcp_client is None:
        raise RuntimeError("MCP Client not initialized. Call set_mcp_client() first.")
    return _mcp_client


async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """呼叫 MCP Tool 並解析結果
    
    Args:
        tool_name: Tool 名稱
        arguments: Tool 參數
        
    Returns:
        解析後的 JSON 結果
    """
    client = get_mcp_client()
    result = await client.call_tool(tool_name, arguments=arguments)
    
    # 解析 TextContent 中的 JSON
    if result.content and len(result.content) > 0:
        text = result.content[0].text
        return json.loads(text)
    
    return {}


# =============================================================================
# Node: 計算腎功能
# =============================================================================

async def calculate_renal_function(state: PrescriptionState) -> dict[str, Any]:
    """計算病人腎功能 (CrCl)
    
    使用 Cockcroft-Gault 公式計算 CrCl。
    
    Args:
        state: 當前 workflow 狀態
        
    Returns:
        更新 patient_crcl 的字典
    """
    patient = state["patient"]
    
    result = await _call_tool(
        "calculate_creatinine_clearance",
        {
            "age_years": patient["age"],
            "weight_kg": patient["weight_kg"],
            "serum_creatinine": patient["creatinine"],
            "gender": patient["sex"],
        }
    )
    
    crcl = result.get("creatinine_clearance", 0)
    
    return {"patient_crcl": float(crcl)}


# =============================================================================
# Node: 驗證醫囑
# =============================================================================

async def validate_orders(state: PrescriptionState) -> dict[str, Any]:
    """驗證所有待開立醫囑
    
    對每個醫囑呼叫 validate_order Tool。
    
    Args:
        state: 當前 workflow 狀態
        
    Returns:
        更新 validation_results, has_errors, has_warnings 的字典
    """
    results: list[ValidationInfo] = []
    has_errors = False
    has_warnings = False
    
    patient_crcl = state.get("patient_crcl")
    
    for order in state["orders_to_create"]:
        result = await _call_tool(
            "validate_order",
            {
                "drug_code": order["drug_code"],
                "dose": order["dose"],
                "dose_unit": order["dose_unit"],
                "route": order["route"],
                "frequency": order["frequency"],
                "patient_crcl": patient_crcl,
            }
        )
        
        validation: ValidationInfo = {
            "drug_code": order["drug_code"],
            "valid": result.get("valid", False),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
        }
        results.append(validation)
        
        if not validation["valid"]:
            has_errors = True
        if validation["warnings"]:
            has_warnings = True
    
    return {
        "validation_results": results,
        "has_errors": has_errors,
        "has_warnings": has_warnings,
    }


# =============================================================================
# Node: 檢查交互作用
# =============================================================================

async def check_interactions(state: PrescriptionState) -> dict[str, Any]:
    """檢查所有藥物間的交互作用
    
    使用兩兩配對檢查。如果藥物數量 < 2 則跳過。
    
    Args:
        state: 當前 workflow 狀態
        
    Returns:
        更新 interactions 的字典
    """
    drugs = [order["drug_code"] for order in state["orders_to_create"]]
    
    if len(drugs) < 2:
        return {"interactions": []}
    
    interactions: list[InteractionInfo] = []
    
    # 兩兩檢查
    for i, drug_a in enumerate(drugs):
        for drug_b in drugs[i + 1:]:
            result = await _call_tool(
                "check_drug_interaction",
                {"drug1": drug_a, "drug2": drug_b}
            )
            
            # 如果有交互作用
            if result.get("interactions"):
                for inter in result["interactions"]:
                    interactions.append({
                        "drug_a": drug_a,
                        "drug_b": drug_b,
                        "severity": inter.get("severity", "unknown"),
                        "description": inter.get("description", ""),
                    })
    
    return {"interactions": interactions}


# =============================================================================
# Node: 送出醫囑
# =============================================================================

async def submit_orders(state: PrescriptionState) -> dict[str, Any]:
    """送出所有驗證通過的醫囑
    
    只送出驗證通過的醫囑。失敗的醫囑會記錄到 failed_orders。
    
    Args:
        state: 當前 workflow 狀態
        
    Returns:
        更新 submitted_orders, failed_orders 的字典
    """
    submitted: list[SubmittedOrder] = []
    failed: list[FailedOrder] = []
    
    # 建立 drug_code -> validation 的映射
    validation_map = {
        v["drug_code"]: v 
        for v in state.get("validation_results", [])
    }
    
    for order in state["orders_to_create"]:
        # 檢查驗證結果
        validation = validation_map.get(order["drug_code"])
        
        if validation and not validation["valid"]:
            failed.append({
                "drug_code": order["drug_code"],
                "reason": "驗證失敗",
                "errors": validation["errors"],
            })
            continue
        
        # 送出醫囑
        result = await _call_tool(
            "submit_order",
            {
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
        
        if result.get("success"):
            submitted.append({
                "drug_code": order["drug_code"],
                "order_id": result.get("order_id", ""),
            })
        else:
            failed.append({
                "drug_code": order["drug_code"],
                "reason": result.get("message", "送出失敗"),
                "errors": result.get("errors", []),
            })
    
    return {
        "submitted_orders": submitted,
        "failed_orders": failed,
    }


# =============================================================================
# 條件判斷函數
# =============================================================================

def should_proceed_after_validation(state: PrescriptionState) -> str:
    """驗證後決定下一步
    
    根據驗證結果決定 workflow 走向：
    - 有錯誤 → 停止
    - 有警告但未確認 → 停止等待確認
    - 都通過 → 繼續檢查交互作用
    
    Args:
        state: 當前 workflow 狀態
        
    Returns:
        下一個 node 的名稱或 END
    """
    if state.get("has_errors", False):
        return "stop_with_errors"
    
    if state.get("has_warnings", False) and not state.get("user_confirmed", False):
        return "wait_for_confirmation"
    
    return "proceed_to_submit"
