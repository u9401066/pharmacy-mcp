"""Tests for Taiwan TFDA and NHI API clients."""

import pytest

from pharmacy_mcp.infrastructure.api.tfda import (
    TFDAClient,
    translate_drug_name,
    DRUG_NAME_MAPPING,
)
from pharmacy_mcp.infrastructure.api.nhi import (
    NHIClient,
    get_nhi_coverage_info,
    NHI_COVERAGE_RULES,
)


class TestDrugNameTranslation:
    """Test drug name translation functionality."""
    
    def test_translate_english_to_chinese(self):
        """Test translating English drug name to Chinese."""
        result = translate_drug_name("warfarin")
        
        assert result is not None
        assert result["chinese_generic"] == "華法林"
        assert "可邁丁" in result["chinese_brand"]
        assert result["category"] == "抗凝血劑"
    
    def test_translate_propofol(self):
        """Test propofol translation with nickname."""
        result = translate_drug_name("propofol")
        
        assert result is not None
        assert result["chinese_generic"] == "丙泊酚"
        assert result.get("nickname") == "牛奶針"
    
    def test_translate_chinese_generic_to_english(self):
        """Test reverse lookup from Chinese generic name."""
        result = translate_drug_name("華法林")
        
        assert result is not None
        assert result["english"].lower() == "warfarin"
    
    def test_translate_chinese_brand_to_english(self):
        """Test reverse lookup from Chinese brand name."""
        result = translate_drug_name("普拿疼")
        
        assert result is not None
        assert result["english"].lower() == "acetaminophen"
    
    def test_translate_unknown_drug(self):
        """Test translation of unknown drug returns None."""
        result = translate_drug_name("unknown_drug_xyz")
        
        assert result is None
    
    def test_translate_case_insensitive(self):
        """Test translation is case insensitive."""
        result1 = translate_drug_name("WARFARIN")
        result2 = translate_drug_name("Warfarin")
        result3 = translate_drug_name("warfarin")
        
        assert result1 == result2 == result3
    
    def test_drug_mapping_completeness(self):
        """Test that drug mapping has required fields."""
        for drug_name, info in DRUG_NAME_MAPPING.items():
            assert "english" in info
            assert "chinese_generic" in info
            assert "chinese_brand" in info
            assert "category" in info


class TestNHICoverage:
    """Test NHI coverage lookup functionality."""
    
    def test_get_warfarin_coverage(self):
        """Test getting coverage info for warfarin."""
        result = get_nhi_coverage_info("warfarin")
        
        assert result is not None
        assert result["is_covered"] is True
        assert result["coverage_type"] == "一般給付"
        assert result["prior_authorization"] is False
    
    def test_get_herceptin_coverage(self):
        """Test getting coverage info for prior authorization drug."""
        result = get_nhi_coverage_info("trastuzumab")
        
        assert result is not None
        assert result["is_covered"] is True
        assert result["coverage_type"] == "事前審查"
        assert result["prior_authorization"] is True
    
    def test_get_coverage_by_brand_name(self):
        """Test getting coverage by brand name."""
        result = get_nhi_coverage_info("Lipitor")
        
        assert result is not None
        assert "atorvastatin" in result["drug_name"].lower()
    
    def test_get_unknown_drug_coverage(self):
        """Test coverage for unknown drug returns None."""
        result = get_nhi_coverage_info("unknown_xyz_123")
        
        assert result is None
    
    def test_coverage_rules_completeness(self):
        """Test that coverage rules have required fields."""
        required_fields = [
            "drug_name",
            "is_covered",
            "coverage_type",
            "indications",
            "prior_authorization"
        ]
        
        for drug_key, info in NHI_COVERAGE_RULES.items():
            for field in required_fields:
                assert field in info, f"Missing {field} in {drug_key}"


class TestTFDAClient:
    """Test TFDA API client."""
    
    @pytest.fixture
    def client(self):
        """Create TFDA client instance."""
        return TFDAClient()
    
    def test_format_drug_record(self, client):
        """Test drug record formatting."""
        raw_record = {
            "許可證字號": "衛署藥製字第012345號",
            "中文品名": "測試藥品",
            "英文品名": "TEST DRUG",
            "劑型": "錠劑",
            "主成分略述": "TEST INGREDIENT",
            "適應症": "測試適應症",
            "申請商名稱": "測試公司",
            "申請商地址": "台北市",
            "製造廠名稱": "製造公司",
            "發證日期": "2020-01-01",
            "有效日期": "2025-01-01",
        }
        
        formatted = client._format_drug_record(raw_record)
        
        assert formatted["permit_number"] == "衛署藥製字第012345號"
        assert formatted["chinese_name"] == "測試藥品"
        assert formatted["english_name"] == "TEST DRUG"
        assert formatted["dosage_form"] == "錠劑"
        assert formatted["source"] == "TFDA"
        assert formatted["applicant"]["name"] == "測試公司"
        assert formatted["manufacturer"]["name"] == "製造公司"


class TestNHIClient:
    """Test NHI API client."""
    
    @pytest.fixture
    def client(self):
        """Create NHI client instance."""
        return NHIClient()
    
    def test_lookup_known_nhi_code(self, client):
        """Test looking up known NHI code."""
        result = client._lookup_nhi_code("A022664100")
        
        assert result is not None
        assert result["ingredient"] == "WARFARIN SODIUM"
        assert "可邁丁" in result["chinese_name"]
    
    def test_lookup_unknown_nhi_code(self, client):
        """Test looking up unknown NHI code."""
        result = client._lookup_nhi_code("UNKNOWN123")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_coverage(self, client):
        """Test coverage check returns proper format."""
        result = await client.check_coverage("test_drug")
        
        assert "is_covered" in result
        assert "drug_name" in result
        assert "coverage_details" in result
        assert "note" in result


class TestDrugInfoServiceTaiwanIntegration:
    """Test Taiwan info integration in DrugInfoService."""
    
    def test_get_taiwan_info_warfarin(self):
        """Test _get_taiwan_info returns correct data for warfarin."""
        from pharmacy_mcp.application.services.drug_info import DrugInfoService
        
        service = DrugInfoService()
        result = service._get_taiwan_info("warfarin")
        
        assert result is not None
        
        # Check translation
        assert "translation" in result
        assert result["translation"]["chinese_generic"] == "華法林"
        assert "可邁丁" in result["translation"]["chinese_brand"]
        assert result["translation"]["category"] == "抗凝血劑"
        
        # Check NHI coverage
        assert "nhi" in result
        assert result["nhi"]["is_covered"] is True
        assert result["nhi"]["coverage_type"] is not None
    
    def test_get_taiwan_info_propofol(self):
        """Test _get_taiwan_info returns nickname for propofol."""
        from pharmacy_mcp.application.services.drug_info import DrugInfoService
        
        service = DrugInfoService()
        result = service._get_taiwan_info("propofol")
        
        assert result is not None
        assert "translation" in result
        assert result["translation"]["chinese_generic"] == "丙泊酚"
        assert result["translation"]["nickname"] == "牛奶針"
    
    def test_get_taiwan_info_unknown_drug(self):
        """Test _get_taiwan_info returns None for unknown drug."""
        from pharmacy_mcp.application.services.drug_info import DrugInfoService
        
        service = DrugInfoService()
        result = service._get_taiwan_info("unknown_random_drug_xyz")
        
        assert result is None
    
    def test_get_taiwan_info_with_nhi_only(self):
        """Test drug with NHI coverage but no translation."""
        from pharmacy_mcp.application.services.drug_info import DrugInfoService
        
        service = DrugInfoService()
        # Test a drug that's in both mappings
        result = service._get_taiwan_info("pembrolizumab")
        
        assert result is not None
        # Should have NHI info
        assert "nhi" in result
        assert result["nhi"]["prior_authorization_required"] is True
