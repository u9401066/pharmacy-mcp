"""醫囑結果值物件"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ValidationResult:
    """醫囑驗證結果

    不可變的值物件，表示醫囑驗證的結果。

    Attributes:
        valid: 是否驗證通過
        errors: 錯誤訊息列表（驗證失敗原因）
        warnings: 警告訊息列表（可覆寫的問題）
        suggested_adjustments: 建議的調整（如腎功能調整劑量）
    """

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    suggested_adjustments: Optional[dict] = None

    @classmethod
    def success(cls, warnings: list[str] | None = None) -> "ValidationResult":
        """建立成功的驗證結果"""
        return cls(
            valid=True,
            errors=tuple(),
            warnings=tuple(warnings) if warnings else tuple(),
        )

    @classmethod
    def failure(
        cls, errors: list[str], warnings: list[str] | None = None
    ) -> "ValidationResult":
        """建立失敗的驗證結果"""
        return cls(
            valid=False,
            errors=tuple(errors),
            warnings=tuple(warnings) if warnings else tuple(),
        )

    @classmethod
    def with_adjustment(
        cls,
        warnings: list[str],
        adjustments: dict,
    ) -> "ValidationResult":
        """建立需要調整的驗證結果"""
        return cls(
            valid=True,
            errors=tuple(),
            warnings=tuple(warnings),
            suggested_adjustments=adjustments,
        )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "suggested_adjustments": self.suggested_adjustments,
        }


@dataclass(frozen=True)
class OrderResult:
    """醫囑執行結果

    不可變的值物件，表示醫囑送出的結果。

    Attributes:
        success: 是否成功
        order_id: 醫囑編號（成功時由 HIS 回傳）
        message: 結果訊息
        errors: 錯誤訊息列表
    """

    success: bool
    order_id: Optional[str] = None
    message: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def ok(cls, order_id: str, message: str = "醫囑已送出") -> "OrderResult":
        """建立成功結果"""
        return cls(success=True, order_id=order_id, message=message)

    @classmethod
    def fail(cls, errors: list[str], message: str = "醫囑送出失敗") -> "OrderResult":
        """建立失敗結果"""
        return cls(success=False, errors=tuple(errors), message=message)

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "message": self.message,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class StopResult:
    """停止醫囑結果

    不可變的值物件，表示停止醫囑的結果。

    Attributes:
        success: 是否成功
        message: 結果訊息
    """

    success: bool
    message: str = ""

    @classmethod
    def ok(cls, message: str = "醫囑已停止") -> "StopResult":
        """建立成功結果"""
        return cls(success=True, message=message)

    @classmethod
    def fail(cls, message: str) -> "StopResult":
        """建立失敗結果"""
        return cls(success=False, message=message)

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "success": self.success,
            "message": self.message,
        }


@dataclass(frozen=True)
class FormularyItem:
    """院內藥品項目

    不可變的值物件，表示院內藥品檔中的一筆藥品。

    Attributes:
        drug_code: 藥品代碼
        drug_name: 藥品名稱
        generic_name: 學名
        strength: 規格/含量
        unit: 單位
        dosage_form: 劑型
        available_routes: 可用給藥途徑
        min_dose: 最小劑量
        max_dose: 最大劑量
        default_frequency: 預設頻率
        nhi_code: 健保代碼
        atc_code: ATC 代碼
        requires_renal_adjustment: 是否需腎功能調整
        high_alert: 是否為高警訊藥品
    """

    drug_code: str
    drug_name: str
    generic_name: str
    strength: str
    unit: str
    dosage_form: str
    available_routes: tuple[str, ...]
    min_dose: float
    max_dose: float
    default_frequency: str
    nhi_code: Optional[str] = None
    atc_code: Optional[str] = None
    requires_renal_adjustment: bool = False
    high_alert: bool = False

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "drug_code": self.drug_code,
            "drug_name": self.drug_name,
            "generic_name": self.generic_name,
            "strength": self.strength,
            "unit": self.unit,
            "dosage_form": self.dosage_form,
            "available_routes": list(self.available_routes),
            "min_dose": self.min_dose,
            "max_dose": self.max_dose,
            "default_frequency": self.default_frequency,
            "nhi_code": self.nhi_code,
            "atc_code": self.atc_code,
            "requires_renal_adjustment": self.requires_renal_adjustment,
            "high_alert": self.high_alert,
        }


@dataclass(frozen=True)
class RenalAdjustment:
    """腎功能劑量調整

    不可變的值物件，表示特定 CrCl 下的劑量調整建議。

    Attributes:
        drug_code: 藥品代碼
        crcl_range: CrCl 範圍描述
        needs_adjustment: 是否需要調整
        recommendation: 調整建議文字
        suggested_dose: 建議劑量
        suggested_frequency: 建議頻率
        contraindicated: 是否禁忌使用
    """

    drug_code: str
    crcl_range: str
    needs_adjustment: bool
    recommendation: str
    suggested_dose: Optional[float] = None
    suggested_frequency: Optional[str] = None
    contraindicated: bool = False

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "drug_code": self.drug_code,
            "crcl_range": self.crcl_range,
            "needs_adjustment": self.needs_adjustment,
            "recommendation": self.recommendation,
            "suggested_dose": self.suggested_dose,
            "suggested_frequency": self.suggested_frequency,
            "contraindicated": self.contraindicated,
        }
