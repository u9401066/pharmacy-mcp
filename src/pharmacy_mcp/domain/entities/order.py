"""醫囑實體定義"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    """醫囑狀態"""

    PENDING = "pending"  # 待送出
    ACTIVE = "active"  # 進行中
    COMPLETED = "completed"  # 已完成
    DISCONTINUED = "discontinued"  # 已停止
    CANCELLED = "cancelled"  # 已取消


class Route(str, Enum):
    """給藥途徑"""

    PO = "PO"  # 口服
    IV = "IV"  # 靜脈注射
    IM = "IM"  # 肌肉注射
    SC = "SC"  # 皮下注射
    SL = "SL"  # 舌下
    TOP = "TOP"  # 外用
    INH = "INH"  # 吸入
    PR = "PR"  # 直腸
    IVPB = "IVPB"  # 靜脈點滴
    IVP = "IVP"  # 靜脈推注


class Frequency(str, Enum):
    """給藥頻率"""

    STAT = "STAT"  # 立即
    QD = "QD"  # 每天一次
    BID = "BID"  # 每天兩次
    TID = "TID"  # 每天三次
    QID = "QID"  # 每天四次
    Q4H = "Q4H"  # 每4小時
    Q6H = "Q6H"  # 每6小時
    Q8H = "Q8H"  # 每8小時
    Q12H = "Q12H"  # 每12小時
    QHS = "QHS"  # 睡前
    PRN = "PRN"  # 需要時
    QOD = "QOD"  # 隔天
    QW = "QW"  # 每週


@dataclass
class Order:
    """醫囑實體

    代表單一藥品的醫囑項目，包含完整的用藥資訊。

    Attributes:
        order_id: 醫囑編號（由 HIS 產生）
        patient_id: 病人編號
        drug_code: 藥品代碼
        drug_name: 藥品名稱
        dose_value: 劑量數值
        dose_unit: 劑量單位 (mg, g, mL, etc.)
        route: 給藥途徑
        frequency: 給藥頻率
        duration_days: 療程天數
        status: 醫囑狀態
        physician_id: 開立醫師
        created_at: 建立時間
        discontinued_at: 停止時間
        discontinue_reason: 停止原因
        notes: 備註
    """

    order_id: str
    patient_id: str
    drug_code: str
    drug_name: str

    # 劑量資訊
    dose_value: float
    dose_unit: str
    route: str
    frequency: str
    duration_days: int

    # 狀態追蹤
    physician_id: str
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    discontinued_at: Optional[datetime] = None
    discontinue_reason: Optional[str] = None
    notes: Optional[str] = None

    def discontinue(self, reason: str) -> None:
        """停止醫囑

        Args:
            reason: 停止原因
        """
        self.status = OrderStatus.DISCONTINUED
        self.discontinued_at = datetime.now()
        self.discontinue_reason = reason

    def activate(self) -> None:
        """啟用醫囑"""
        self.status = OrderStatus.ACTIVE

    def complete(self) -> None:
        """完成醫囑"""
        self.status = OrderStatus.COMPLETED

    def cancel(self) -> None:
        """取消醫囑"""
        self.status = OrderStatus.CANCELLED

    @property
    def is_active(self) -> bool:
        """是否為進行中"""
        return self.status == OrderStatus.ACTIVE

    @property
    def dose_display(self) -> str:
        """劑量顯示格式"""
        return f"{self.dose_value} {self.dose_unit}"

    @property
    def prescription_display(self) -> str:
        """完整處方顯示"""
        return f"{self.drug_name} {self.dose_display} {self.route} {self.frequency}"

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "order_id": self.order_id,
            "patient_id": self.patient_id,
            "drug_code": self.drug_code,
            "drug_name": self.drug_name,
            "dose_value": self.dose_value,
            "dose_unit": self.dose_unit,
            "route": self.route,
            "frequency": self.frequency,
            "duration_days": self.duration_days,
            "status": self.status.value,
            "physician_id": self.physician_id,
            "created_at": self.created_at.isoformat(),
            "discontinued_at": (
                self.discontinued_at.isoformat() if self.discontinued_at else None
            ),
            "discontinue_reason": self.discontinue_reason,
            "notes": self.notes,
        }
