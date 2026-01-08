"""Mock HIS API 客戶端

模擬醫院資訊系統 (HIS) 的醫囑相關 API。
實際部署時可替換為真實的 HIS 接口。
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HISOrderResponse:
    """HIS 醫囑回應"""

    success: bool
    order_id: Optional[str] = None
    message: str = ""
    error_code: Optional[str] = None


@dataclass
class HISPatient:
    """HIS 病人資料"""

    patient_id: str
    name: str
    age: int
    weight_kg: float
    sex: str
    creatinine: float  # mg/dL
    admission_date: datetime


class HISMockClient:
    """Mock HIS 客戶端

    模擬 HIS 系統的醫囑 API，用於開發和測試。

    注意：
    - 這是 Mock 實作，不會真的寫入任何系統
    - 實際部署時需替換為真實的 HIS API 客戶端
    - 保留相同的介面以便切換
    """

    def __init__(self):
        """初始化 Mock 客戶端"""
        # 模擬的訂單儲存（記憶體）
        self._orders: dict[str, dict] = {}

        # 模擬的病人資料
        self._patients: dict[str, HISPatient] = {
            "P001": HISPatient(
                patient_id="P001",
                name="王大明",
                age=75,
                weight_kg=60,
                sex="male",
                creatinine=1.8,
                admission_date=datetime(2026, 1, 5),
            ),
            "P002": HISPatient(
                patient_id="P002",
                name="李小美",
                age=45,
                weight_kg=55,
                sex="female",
                creatinine=0.9,
                admission_date=datetime(2026, 1, 7),
            ),
            "P003": HISPatient(
                patient_id="P003",
                name="張老先生",
                age=85,
                weight_kg=50,
                sex="male",
                creatinine=2.5,
                admission_date=datetime(2026, 1, 3),
            ),
        }

    async def create_order(
        self,
        patient_id: str,
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        duration_days: int,
        physician_id: str,
        notes: Optional[str] = None,
    ) -> HISOrderResponse:
        """建立醫囑

        Args:
            patient_id: 病人編號
            drug_code: 藥品代碼
            dose: 劑量
            dose_unit: 劑量單位
            route: 給藥途徑
            frequency: 給藥頻率
            duration_days: 療程天數
            physician_id: 醫師編號
            notes: 備註

        Returns:
            HISOrderResponse
        """
        # 模擬驗證
        if patient_id not in self._patients:
            return HISOrderResponse(
                success=False,
                message=f"病人 {patient_id} 不存在",
                error_code="PATIENT_NOT_FOUND",
            )

        # 產生訂單 ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # 儲存訂單
        self._orders[order_id] = {
            "order_id": order_id,
            "patient_id": patient_id,
            "drug_code": drug_code,
            "dose": dose,
            "dose_unit": dose_unit,
            "route": route,
            "frequency": frequency,
            "duration_days": duration_days,
            "physician_id": physician_id,
            "notes": notes,
            "status": "ACTIVE",
            "created_at": datetime.now().isoformat(),
        }

        return HISOrderResponse(
            success=True,
            order_id=order_id,
            message="醫囑已成功建立",
        )

    async def discontinue_order(
        self,
        order_id: str,
        reason: str,
    ) -> HISOrderResponse:
        """停止醫囑

        Args:
            order_id: 醫囑編號
            reason: 停止原因

        Returns:
            HISOrderResponse
        """
        if order_id not in self._orders:
            return HISOrderResponse(
                success=False,
                message=f"醫囑 {order_id} 不存在",
                error_code="ORDER_NOT_FOUND",
            )

        order = self._orders[order_id]

        if order["status"] == "DISCONTINUED":
            return HISOrderResponse(
                success=False,
                message="醫囑已停止",
                error_code="ALREADY_DISCONTINUED",
            )

        # 更新狀態
        order["status"] = "DISCONTINUED"
        order["discontinued_at"] = datetime.now().isoformat()
        order["discontinue_reason"] = reason

        return HISOrderResponse(
            success=True,
            order_id=order_id,
            message="醫囑已停止",
        )

    async def get_order(self, order_id: str) -> Optional[dict]:
        """取得醫囑資料

        Args:
            order_id: 醫囑編號

        Returns:
            醫囑資料字典或 None
        """
        return self._orders.get(order_id)

    async def get_patient(self, patient_id: str) -> Optional[HISPatient]:
        """取得病人資料

        Args:
            patient_id: 病人編號

        Returns:
            HISPatient 或 None
        """
        return self._patients.get(patient_id)

    async def get_patient_active_orders(self, patient_id: str) -> list[dict]:
        """取得病人的進行中醫囑

        Args:
            patient_id: 病人編號

        Returns:
            醫囑列表
        """
        return [
            order
            for order in self._orders.values()
            if order["patient_id"] == patient_id and order["status"] == "ACTIVE"
        ]

    def add_mock_patient(self, patient: HISPatient) -> None:
        """新增模擬病人（測試用）"""
        self._patients[patient.patient_id] = patient

    def clear_orders(self) -> None:
        """清除所有訂單（測試用）"""
        self._orders.clear()
