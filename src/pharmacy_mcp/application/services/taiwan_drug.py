"""Taiwan Drug Information Service."""

from typing import Any

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


class TaiwanDrugService:
    """Service for Taiwan-specific drug information."""
    
    def __init__(self):
        self._tfda_client = TFDAClient()
        self._nhi_client = NHIClient()
    
    async def search_tfda_drug(
        self,
        query: str,
        limit: int = 20,
        search_type: str = "name"
    ) -> dict[str, Any]:
        """
        Search Taiwan TFDA drug database.
        
        Args:
            query: Search query
            limit: Maximum number of results
            search_type: Type of search (name, ingredient, permit_number, manufacturer)
            
        Returns:
            Search results
        """
        if search_type == "permit_number":
            result = await self._tfda_client.search_drug_by_permit_number(query)
            if result:
                return {
                    "query": query,
                    "search_type": search_type,
                    "result_count": 1,
                    "results": [result]
                }
            return {
                "query": query,
                "search_type": search_type,
                "result_count": 0,
                "results": []
            }
        
        elif search_type == "ingredient":
            results = await self._tfda_client.search_drug_by_ingredient(query, limit)
        
        elif search_type == "manufacturer":
            results = await self._tfda_client.search_drug_by_manufacturer(query, limit)
        
        else:  # Default: name search
            results = await self._tfda_client.search_drug_by_name(query, limit)
        
        return {
            "query": query,
            "search_type": search_type,
            "result_count": len(results),
            "results": results
        }
    
    async def get_nhi_coverage(
        self,
        drug_name: str
    ) -> dict[str, Any]:
        """
        Get NHI coverage information for a drug.
        
        Args:
            drug_name: Drug name (generic or brand)
            
        Returns:
            NHI coverage information
        """
        # First try our built-in coverage rules
        coverage_info = get_nhi_coverage_info(drug_name)
        
        if coverage_info:
            return {
                "drug_name": drug_name,
                "found": True,
                "coverage": coverage_info,
                "source": "NHI Coverage Rules Database"
            }
        
        # Try to check via NHI client
        coverage_check = await self._nhi_client.check_coverage(drug_name)
        
        return {
            "drug_name": drug_name,
            "found": coverage_check.get("is_covered", False),
            "coverage": coverage_check,
            "source": "NHI Query"
        }
    
    async def get_nhi_drug_price(
        self,
        nhi_code: str
    ) -> dict[str, Any]:
        """
        Get NHI reimbursement price for a drug.
        
        Args:
            nhi_code: NHI drug code (e.g., "A022664100")
            
        Returns:
            Price information
        """
        price_info = await self._nhi_client.get_drug_price(nhi_code)
        
        if price_info:
            return {
                "nhi_code": nhi_code,
                "found": True,
                "price_info": price_info,
                "note": "價格為健保支付點數，實際金額依健保署公告為準"
            }
        
        return {
            "nhi_code": nhi_code,
            "found": False,
            "price_info": None,
            "note": "未找到此健保代碼，請確認代碼正確性"
        }
    
    def translate_drug_name(
        self,
        name: str,
        target_language: str = "auto"
    ) -> dict[str, Any]:
        """
        Translate drug name between English and Chinese.
        
        Args:
            name: Drug name to translate
            target_language: Target language (auto, chinese, english)
            
        Returns:
            Translation result
        """
        result = translate_drug_name(name)
        
        if result:
            return {
                "input": name,
                "found": True,
                "translation": result,
                "note": "藥名對照資料來自常用藥品對照表"
            }
        
        return {
            "input": name,
            "found": False,
            "translation": None,
            "note": "未找到此藥品的對照資料，可嘗試使用其他名稱搜尋",
            "suggestions": [
                "嘗試使用英文學名",
                "嘗試使用中文商品名",
                "使用 TFDA 藥品查詢功能"
            ]
        }
    
    async def get_prior_authorization_drugs(self) -> dict[str, Any]:
        """
        Get list of drugs requiring NHI prior authorization.
        
        Returns:
            List of prior authorization drug categories
        """
        pa_drugs = await self._nhi_client.get_prior_authorization_drugs()
        
        # Add from our coverage rules
        pa_from_rules = [
            {
                "drug_name": info["drug_name"],
                "indications": info["indications"],
                "restrictions": info.get("restrictions", "")
            }
            for key, info in NHI_COVERAGE_RULES.items()
            if info.get("prior_authorization", False)
        ]
        
        return {
            "categories": pa_drugs,
            "specific_drugs": pa_from_rules,
            "note": "事前審查藥品需依健保署規定提出申請，並檢附相關文件"
        }
    
    async def get_tfda_statistics(self) -> dict[str, Any]:
        """
        Get statistics about Taiwan drug permits.
        
        Returns:
            Statistics dictionary
        """
        stats = await self._tfda_client.get_drug_statistics()
        
        return {
            "statistics": stats,
            "source": "TFDA Open Data",
            "note": "資料來自政府開放資料平台，每週更新"
        }
    
    def list_available_translations(self) -> dict[str, Any]:
        """
        List all available drug name translations.
        
        Returns:
            List of available translations
        """
        translations = []
        for eng_name, info in DRUG_NAME_MAPPING.items():
            translations.append({
                "english": info.get("english", eng_name),
                "chinese_generic": info.get("chinese_generic", ""),
                "chinese_brands": info.get("chinese_brand", []),
                "category": info.get("category", "")
            })
        
        return {
            "count": len(translations),
            "translations": sorted(translations, key=lambda x: x["english"]),
            "note": "此為內建對照表，如需查詢更多藥品請使用 TFDA 搜尋功能"
        }
    
    def list_nhi_coverage_rules(self) -> dict[str, Any]:
        """
        List all NHI coverage rules in database.
        
        Returns:
            List of coverage rules
        """
        rules = []
        for key, info in NHI_COVERAGE_RULES.items():
            rules.append({
                "drug_key": key,
                "drug_name": info["drug_name"],
                "is_covered": info["is_covered"],
                "coverage_type": info["coverage_type"],
                "prior_authorization": info.get("prior_authorization", False)
            })
        
        return {
            "count": len(rules),
            "rules": sorted(rules, key=lambda x: x["drug_name"]),
            "coverage_types": ["一般給付", "限特定條件給付", "事前審查"],
            "note": "健保給付規則僅供參考，實際給付請依健保署公告為準"
        }


# Singleton instance
taiwan_drug_service = TaiwanDrugService()
