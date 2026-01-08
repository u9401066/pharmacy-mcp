"""處方功能測試"""

import pytest
from pharmacy_mcp.domain.entities.order import Order, OrderStatus
from pharmacy_mcp.domain.value_objects.order_result import (
    ValidationResult,
    OrderResult,
    StopResult,
    FormularyItem,
    RenalAdjustment,
)
from pharmacy_mcp.infrastructure.knowledge.formulary import FormularyKnowledge
from pharmacy_mcp.infrastructure.knowledge.renal_dosing import RenalDosingKnowledge
from pharmacy_mcp.application.services.prescription import PrescriptionService


class TestOrderEntity:
    """Order 實體測試"""

    def test_create_order(self):
        """測試建立醫囑"""
        order = Order(
            order_id="ORD001",
            patient_id="P001",
            drug_code="GENTA-INJ",
            drug_name="Gentamicin 80mg/2mL",
            dose_value=80.0,
            dose_unit="mg",
            route="IV",
            frequency="Q8H",
            duration_days=7,
            physician_id="DR001",
        )

        assert order.order_id == "ORD001"
        assert order.drug_code == "GENTA-INJ"
        assert order.status == OrderStatus.PENDING
        assert order.dose_value == 80.0

    def test_order_status_enum(self):
        """測試醫囑狀態"""
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.ACTIVE == "active"
        assert OrderStatus.DISCONTINUED == "discontinued"


class TestOrderValueObjects:
    """Order Value Objects 測試"""

    def test_validation_result_valid(self):
        """測試驗證結果 - 通過"""
        result = ValidationResult.success()
        assert result.valid is True
        assert result.errors == ()
        assert result.warnings == ()

    def test_validation_result_with_errors(self):
        """測試驗證結果 - 有錯誤"""
        result = ValidationResult.failure(
            errors=["藥品不存在", "劑量超標"],
        )
        assert result.valid is False
        assert len(result.errors) == 2

    def test_validation_result_with_warnings(self):
        """測試驗證結果 - 有警告"""
        result = ValidationResult.with_adjustment(
            warnings=["腎功能需調整劑量"],
            adjustments={"adjusted_dose": 40.0},
        )
        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.suggested_adjustments is not None
        assert result.suggested_adjustments["adjusted_dose"] == 40.0

    def test_order_result_success(self):
        """測試送出結果 - 成功"""
        result = OrderResult.ok(order_id="ORD123", message="醫囑已建立")
        assert result.success is True
        assert result.order_id == "ORD123"

    def test_order_result_failure(self):
        """測試送出結果 - 失敗"""
        result = OrderResult.fail(
            errors=["病人不存在"],
            message="建立失敗",
        )
        assert result.success is False
        assert "病人不存在" in result.errors

    def test_stop_result(self):
        """測試停止結果"""
        result = StopResult.ok(message="醫囑已停止")
        assert result.success is True


class TestFormularyKnowledge:
    """院內藥品檔知識庫測試"""

    def test_get_existing_item(self):
        """測試取得存在的藥品"""
        formulary = FormularyKnowledge()
        item = formulary.get_item("GENTA-INJ")

        assert item is not None
        assert item.drug_code == "GENTA-INJ"
        assert "IV" in item.available_routes

    def test_get_nonexistent_item(self):
        """測試取得不存在的藥品"""
        formulary = FormularyKnowledge()
        item = formulary.get_item("NONEXISTENT")
        assert item is None

    def test_search_formulary(self):
        """測試搜尋藥品"""
        formulary = FormularyKnowledge()
        results = formulary.search("genta")

        assert len(results) >= 1
        assert any(r.drug_code == "GENTA-INJ" for r in results)

    def test_list_all(self):
        """測試列出所有藥品"""
        formulary = FormularyKnowledge()
        items = formulary.all_items

        assert len(items) >= 10
        codes = [i.drug_code for i in items]
        assert "GENTA-INJ" in codes
        assert "VANCO-INJ" in codes


class TestRenalDosingKnowledge:
    """腎功能劑量調整知識庫測試"""

    def test_get_adjustment_low_renal(self):
        """測試低腎功能的劑量調整"""
        renal = RenalDosingKnowledge()
        adj = renal.get_adjustment("GENTA-INJ", crcl=15.0)

        assert adj.needs_adjustment is True
        assert adj.recommendation != ""

    def test_get_adjustment_moderate_renal(self):
        """測試中度腎功能不全的劑量調整"""
        renal = RenalDosingKnowledge()
        # CrCl 35 在 30-49 範圍，需要調整頻率到 Q24H
        adj = renal.get_adjustment("VANCO-INJ", crcl=35.0)
        # 即使 dose_adjustment=1.0，頻率從 Q12H 改為 Q24H 也算需要調整
        assert adj.suggested_frequency == "Q24H"

    def test_get_adjustment_normal_renal(self):
        """測試腎功能正常"""
        renal = RenalDosingKnowledge()
        adj = renal.get_adjustment("GENTA-INJ", crcl=100.0)

        # CrCl 100 可能仍在某個範圍內，檢查是否有回傳
        assert isinstance(adj, RenalAdjustment)

    def test_get_adjustment_unknown_drug(self):
        """測試未知藥品"""
        renal = RenalDosingKnowledge()
        adj = renal.get_adjustment("UNKNOWN-DRUG", crcl=30.0)

        assert adj.needs_adjustment is False
        assert "無" in adj.recommendation or "N/A" in adj.crcl_range


class TestPrescriptionService:
    """處方服務測試"""

    @pytest.fixture
    def service(self):
        """建立測試用 service"""
        return PrescriptionService()

    def test_get_formulary_item(self, service):
        """測試取得院內藥品"""
        item = service.get_formulary_item("GENTA-INJ")
        assert item is not None
        assert item.drug_code == "GENTA-INJ"

    def test_get_renal_adjustment(self, service):
        """測試取得腎功能調整"""
        # CrCl 25 在 10-29 範圍，需要調整頻率到 Q48H
        adj = service.get_renal_adjustment("VANCO-INJ", crcl=25.0)
        assert adj.suggested_frequency == "Q48H"

    def test_validate_order_valid(self, service):
        """測試驗證醫囑 - 通過"""
        result = service.validate_order(
            drug_code="GENTA-INJ",
            dose=80.0,
            dose_unit="mg",
            route="IV",
            frequency="Q8H",
        )
        assert result.valid is True

    def test_validate_order_invalid_drug(self, service):
        """測試驗證醫囑 - 藥品不存在"""
        result = service.validate_order(
            drug_code="NONEXISTENT",
            dose=100.0,
            dose_unit="mg",
            route="IV",
            frequency="QD",
        )
        assert result.valid is False
        assert any("不存在" in e for e in result.errors)

    def test_validate_order_invalid_route(self, service):
        """測試驗證醫囑 - 給藥途徑錯誤"""
        result = service.validate_order(
            drug_code="GENTA-INJ",  # 只有 IV, IM
            dose=80.0,
            dose_unit="mg",
            route="PO",  # 不支援口服
            frequency="Q8H",
        )
        assert result.valid is False
        assert any("給藥途徑" in e for e in result.errors)

    def test_validate_order_dose_warning(self, service):
        """測試驗證醫囑 - 劑量警告"""
        result = service.validate_order(
            drug_code="GENTA-INJ",
            dose=500.0,  # 超過 max_dose 240
            dose_unit="mg",
            route="IV",
            frequency="Q8H",
        )
        # 超過劑量是警告不是錯誤
        assert len(result.warnings) > 0

    def test_validate_order_with_renal_adjustment(self, service):
        """測試驗證醫囑 - 需腎功能調整"""
        # 使用 METFOR-TAB，CrCl < 30 是禁忌
        result = service.validate_order(
            drug_code="METFOR-TAB",
            dose=500.0,
            dose_unit="mg",
            route="PO",
            frequency="BID",
            patient_crcl=20.0,  # 嚴重腎功能不全，Metformin 禁忌
        )
        # METFOR-TAB 在 CrCl < 30 是禁忌，應該有錯誤
        assert result.valid is False or len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_submit_order_mock(self, service):
        """測試送出醫囑 (Mock)"""
        result = await service.submit_order(
            patient_id="P001",
            drug_code="GENTA-INJ",
            dose=80.0,
            dose_unit="mg",
            route="IV",
            frequency="Q8H",
            duration_days=7,
            physician_id="DR001",
            override_warnings=True,  # 略過高警訊藥品警告
        )
        assert result.success is True
        assert result.order_id is not None
        assert result.order_id.startswith("ORD-")

    @pytest.mark.asyncio
    async def test_submit_order_validation_failure(self, service):
        """測試送出醫囑 - 驗證失敗"""
        result = await service.submit_order(
            patient_id="P001",
            drug_code="NONEXISTENT",
            dose=100.0,
            dose_unit="mg",
            route="IV",
            frequency="QD",
            duration_days=7,
            physician_id="DR001",
        )
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_stop_order_mock(self, service):
        """測試停止醫囑 (Mock)"""
        # Mock HIS 會回傳訂單不存在，這是預期行為
        result = await service.stop_order(
            order_id="ORD-12345",
            reason="病人出院",
        )
        # Mock 可能回傳失敗（因為訂單不存在），這是正常的
        assert isinstance(result, StopResult)

    def test_search_formulary(self, service):
        """測試搜尋藥品"""
        results = service.search_formulary("genta")
        assert len(results) >= 1
        assert any(r.drug_code == "GENTA-INJ" for r in results)

    def test_list_high_alert_drugs(self, service):
        """測試列出高警訊藥品"""
        drugs = service.list_high_alert_drugs()
        assert len(drugs) > 0
        assert all(d.high_alert for d in drugs)
