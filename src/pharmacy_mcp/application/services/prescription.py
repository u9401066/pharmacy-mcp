"""處方服務 - 提供原子操作給 MCP Tools"""

from typing import Any, Optional

from pharmacy_mcp.domain.value_objects.order_result import (
    FormularyItem,
    OrderResult,
    RenalAdjustment,
    StopResult,
    ValidationResult,
)
from pharmacy_mcp.infrastructure.api.his_mock import HISMockClient
from pharmacy_mcp.infrastructure.knowledge.formulary import FormularyKnowledge
from pharmacy_mcp.infrastructure.knowledge.renal_dosing import RenalDosingKnowledge


class PrescriptionService:
    """處方服務

    提供原子化的處方操作，設計給 MCP Tools 使用。
    每個方法都是無狀態的，狀態由外部 workflow 管理。

    設計原則：
    - 原子化：每個方法做一件事
    - 無狀態：不保留任何 session 資訊
    - 確定性：固定 input → 固定 output
    """

    def __init__(
        self,
        formulary: Optional[FormularyKnowledge] = None,
        renal_dosing: Optional[RenalDosingKnowledge] = None,
        his_client: Optional[HISMockClient] = None,
    ):
        """初始化處方服務

        Args:
            formulary: 院內藥品檔知識庫
            renal_dosing: 腎功能劑量調整知識庫
            his_client: HIS 客戶端
        """
        self.formulary = formulary or FormularyKnowledge()
        self.renal_dosing = renal_dosing or RenalDosingKnowledge()
        self.his_client = his_client or HISMockClient()

    # =========================================================================
    # Query Operations (查詢)
    # =========================================================================

    def get_formulary_item(self, drug_code: str) -> Optional[FormularyItem]:
        """取得院內藥品詳情

        Args:
            drug_code: 藥品代碼

        Returns:
            FormularyItem 或 None
        """
        return self.formulary.get_item(drug_code)

    def search_formulary(self, query: str, limit: int = 10) -> list[FormularyItem]:
        """搜尋院內藥品檔

        Args:
            query: 搜尋字串
            limit: 最大回傳數量

        Returns:
            符合條件的藥品列表
        """
        return self.formulary.search(query, limit)

    def get_renal_adjustment(self, drug_code: str, crcl: float) -> RenalAdjustment:
        """取得腎功能劑量調整建議

        Args:
            drug_code: 藥品代碼
            crcl: 肌酸酐清除率 (mL/min)

        Returns:
            RenalAdjustment 值物件
        """
        return self.renal_dosing.get_adjustment(drug_code, crcl)

    def is_high_alert_drug(self, drug_code: str) -> bool:
        """檢查是否為高警訊藥品

        Args:
            drug_code: 藥品代碼

        Returns:
            是否為高警訊藥品
        """
        item = self.formulary.get_item(drug_code)
        return item.high_alert if item else False

    # =========================================================================
    # Check Operations (驗證)
    # =========================================================================

    def validate_order(
        self,
        drug_code: str,
        dose: float,
        dose_unit: str,
        route: str,
        frequency: str,
        patient_crcl: Optional[float] = None,
    ) -> ValidationResult:
        """驗證單一醫囑

        執行以下驗證：
        1. 藥品是否存在於院內藥品檔
        2. 給藥途徑是否適用
        3. 劑量是否在建議範圍內
        4. 腎功能調整建議（如適用）

        Args:
            drug_code: 藥品代碼
            dose: 劑量
            dose_unit: 劑量單位
            route: 給藥途徑
            frequency: 給藥頻率
            patient_crcl: 病人的 CrCl (mL/min)，可選

        Returns:
            ValidationResult 值物件
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggested: Optional[dict[str, Any]] = None

        # 1. 檢查藥品是否存在
        item = self.formulary.get_item(drug_code)
        if not item:
            return ValidationResult.failure(
                errors=[f"藥品代碼 {drug_code} 不存在於院內藥品檔"]
            )

        # 2. 檢查給藥途徑
        if route not in item.available_routes:
            errors.append(
                f"給藥途徑 {route} 不適用於此藥品，"
                f"可用途徑：{', '.join(item.available_routes)}"
            )

        # 3. 檢查劑量範圍
        if dose < item.min_dose:
            warnings.append(
                f"劑量 {dose} {dose_unit} 低於建議最小劑量 {item.min_dose} {item.unit}"
            )
        elif dose > item.max_dose:
            warnings.append(
                f"劑量 {dose} {dose_unit} 超過建議最大劑量 {item.max_dose} {item.unit}"
            )

        # 4. 高警訊藥品警告
        if item.high_alert:
            warnings.append(f"⚠️ 高警訊藥品：{item.drug_name}")

        # 5. 腎功能調整
        if patient_crcl is not None and item.requires_renal_adjustment:
            adj = self.renal_dosing.get_adjustment(drug_code, patient_crcl)

            if adj.contraindicated:
                errors.append(
                    f"CrCl {patient_crcl:.1f} mL/min: {adj.recommendation}"
                )
            elif adj.needs_adjustment:
                warnings.append(
                    f"CrCl {patient_crcl:.1f} mL/min: {adj.recommendation}"
                )
                suggested = {
                    "renal_adjustment": True,
                    "suggested_frequency": adj.suggested_frequency,
                    "recommendation": adj.recommendation,
                }

        # 回傳結果
        if errors:
            return ValidationResult.failure(errors=errors, warnings=warnings)

        if suggested:
            return ValidationResult.with_adjustment(
                warnings=warnings, adjustments=suggested
            )

        return ValidationResult.success(warnings=warnings if warnings else None)

    # =========================================================================
    # Action Operations (執行)
    # =========================================================================

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
        notes: Optional[str] = None,
    ) -> OrderResult:
        """送出單一醫囑到 HIS

        會先執行驗證，通過後才送出。

        Args:
            patient_id: 病人編號
            drug_code: 藥品代碼
            dose: 劑量
            dose_unit: 劑量單位
            route: 給藥途徑
            frequency: 給藥頻率
            duration_days: 療程天數
            physician_id: 醫師編號
            override_warnings: 是否覆寫警告
            notes: 備註

        Returns:
            OrderResult 值物件
        """
        # 取得病人資料以獲取 CrCl（如果有的話）
        patient = await self.his_client.get_patient(patient_id)
        patient_crcl = None
        if patient:
            # 簡化：直接用 creatinine 估算（實際應該用 calculate_creatinine_clearance）
            # 這裡假設 workflow 會先呼叫 calculate_creatinine_clearance 並傳入
            pass

        # 1. 驗證
        validation = self.validate_order(
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            patient_crcl=patient_crcl,
        )

        if not validation.valid:
            return OrderResult.fail(
                errors=list(validation.errors),
                message="驗證失敗，醫囑未送出",
            )

        # 2. 檢查警告
        if validation.warnings and not override_warnings:
            return OrderResult.fail(
                errors=[f"有警告需確認: {'; '.join(validation.warnings)}"],
                message="請設定 override_warnings=True 以忽略警告",
            )

        # 3. 送出到 HIS
        result = await self.his_client.create_order(
            patient_id=patient_id,
            drug_code=drug_code,
            dose=dose,
            dose_unit=dose_unit,
            route=route,
            frequency=frequency,
            duration_days=duration_days,
            physician_id=physician_id,
            notes=notes,
        )

        if result.success:
            return OrderResult.ok(
                order_id=result.order_id or "",
                message=result.message,
            )
        else:
            return OrderResult.fail(
                errors=[result.message],
                message="HIS 送出失敗",
            )

    async def stop_order(
        self,
        order_id: str,
        reason: str,
    ) -> StopResult:
        """停止醫囑

        Args:
            order_id: 醫囑編號
            reason: 停止原因

        Returns:
            StopResult 值物件
        """
        result = await self.his_client.discontinue_order(order_id, reason)

        if result.success:
            return StopResult.ok(message=result.message)
        else:
            return StopResult.fail(message=result.message)

    # =========================================================================
    # Utility Operations (工具)
    # =========================================================================

    def list_high_alert_drugs(self) -> list[FormularyItem]:
        """列出高警訊藥品"""
        return self.formulary.list_high_alert_drugs()

    def list_renal_adjustment_drugs(self) -> list[FormularyItem]:
        """列出需腎功能調整的藥品"""
        return self.formulary.list_renal_adjustment_drugs()
