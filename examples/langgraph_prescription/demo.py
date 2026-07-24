"""LangGraph 處方 Workflow 執行範例

此範例展示如何：
1. 連接 pharmacy-mcp MCP Server
2. 建立 LangGraph Workflow
3. 執行處方開立流程

執行方式：
    # 確保已安裝依賴
    pip install langgraph mcp

    # 執行範例
    python -m examples.langgraph_prescription.demo

    # 或直接執行
    cd examples/langgraph_prescription
    python demo.py
"""

import asyncio
import sys
from pathlib import Path

# 將專案根目錄加入 path（方便直接執行）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.langgraph_prescription.nodes import set_mcp_client
from examples.langgraph_prescription.state import PrescriptionState
from examples.langgraph_prescription.workflow import create_prescription_workflow
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_prescription_workflow():
    """執行處方開立 Workflow 範例"""

    print("=" * 60)
    print("🏥 處方開立 Workflow 範例")
    print("=" * 60)

    # === 1. 連接 MCP Server ===
    print("\n📡 連接 pharmacy-mcp Server...")

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "pharmacy_mcp"],
        cwd=str(project_root),
    )

    async with (
        stdio_client(server_params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        # 設定全域 MCP client
        set_mcp_client(session)

        print("✅ MCP Server 連接成功")

        # 列出可用 Tools
        tools = await session.list_tools()
        print(f"📦 可用 Tools: {len(tools.tools)} 個")

        # === 2. 建立 Workflow ===
        print("\n🔧 建立處方 Workflow...")
        workflow = create_prescription_workflow()

        # === 3. 準備輸入狀態 ===
        print("\n📋 準備病人資料和醫囑...")

        initial_state: PrescriptionState = {
            # 病人資訊
            "patient": {
                "patient_id": "P001",
                "name": "王大明",
                "age": 75,
                "weight_kg": 60,
                "sex": "male",
                "creatinine": 1.8,  # 偏高，需要腎功能調整
            },
            # 待開立醫囑
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
            # 初始化其他欄位
            "patient_crcl": None,
            "validation_results": [],
            "interactions": [],
            "submitted_orders": [],
            "failed_orders": [],
            "has_errors": False,
            "has_warnings": False,
            "user_confirmed": False,  # 設為 True 可覆寫警告
        }

        print(
            f"  病人: {initial_state['patient']['name']} "
            f"(ID: {initial_state['patient']['patient_id']})"
        )
        print(f"  年齡: {initial_state['patient']['age']} 歲")
        print(f"  體重: {initial_state['patient']['weight_kg']} kg")
        print(f"  血清肌酸酐: {initial_state['patient']['creatinine']} mg/dL")
        print(f"  待開立藥品: {len(initial_state['orders_to_create'])} 項")

        for order in initial_state["orders_to_create"]:
            print(
                f"    - {order['drug_name']} {order['dose']}{order['dose_unit']} "
                f"{order['route']} {order['frequency']}"
            )

        # === 4. 執行 Workflow ===
        print("\n🚀 執行 Workflow...")
        print("-" * 60)

        final_state = await workflow.ainvoke(initial_state)

        # === 5. 顯示結果 ===
        print("-" * 60)
        print("\n📊 執行結果:")

        # CrCl
        crcl = final_state.get("patient_crcl")
        if crcl:
            print(f"\n  💊 病人 CrCl: {crcl:.1f} mL/min")
            if crcl < 30:
                print("     ⚠️ 嚴重腎功能不全")
            elif crcl < 60:
                print("     ⚠️ 中度腎功能不全")

        # 驗證結果
        print("\n  ✅ 驗證結果:")
        for v in final_state.get("validation_results", []):
            status = "✓" if v["valid"] else "✗"
            print(f"     {status} {v['drug_code']}")
            for err in v.get("errors", []):
                print(f"        ❌ {err}")
            for warn in v.get("warnings", []):
                print(f"        ⚠️ {warn}")

        # 交互作用
        interactions = final_state.get("interactions", [])
        if interactions:
            print("\n  ⚠️ 交互作用:")
            for inter in interactions:
                print(
                    f"     - {inter['drug_a']} + {inter['drug_b']}: "
                    f"{inter['severity']} - {inter['description']}"
                )

        # 送出結果
        print("\n  📝 送出結果:")
        for order in final_state.get("submitted_orders", []):
            print(f"     ✅ {order['drug_code']} → Order ID: {order['order_id']}")

        for order in final_state.get("failed_orders", []):
            print(f"     ❌ {order['drug_code']} → {order['reason']}")
            for err in order.get("errors", []):
                print(f"        - {err}")

        # 摘要
        print("\n" + "=" * 60)
        submitted_count = len(final_state.get("submitted_orders", []))
        failed_count = len(final_state.get("failed_orders", []))
        print(f"📈 摘要: 成功 {submitted_count} 項, 失敗 {failed_count} 項")
        print("=" * 60)


async def run_with_confirmation():
    """執行帶確認的 Workflow

    第一次執行不覆寫警告，顯示警告後再執行一次覆寫警告。
    """
    print("\n" + "=" * 60)
    print("🔄 測試警告覆寫流程")
    print("=" * 60)

    # 這裡可以實作更複雜的確認流程
    # 例如：先執行 validation_only_workflow，確認後再執行完整 workflow
    pass


def main():
    """主程式進入點"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     LangGraph + pharmacy-mcp 處方 Workflow 範例           ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        asyncio.run(run_prescription_workflow())
    except KeyboardInterrupt:
        print("\n\n⚠️ 使用者中斷執行")
    except Exception as e:
        print(f"\n\n❌ 執行錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
