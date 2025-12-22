"""Drug information service."""

import hashlib
from typing import Any

from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService
from pharmacy_mcp.infrastructure.api.tfda import translate_drug_name
from pharmacy_mcp.infrastructure.api.nhi import get_nhi_coverage_info


class DrugInfoService:
    """Service for retrieving comprehensive drug information."""
    
    def __init__(
        self,
        rxnorm_client: RxNormClient | None = None,
        fda_client: FDAClient | None = None,
        cache: CacheService | None = None,
    ):
        self.rxnorm = rxnorm_client or RxNormClient()
        self.fda = fda_client or FDAClient()
        self.cache = cache or CacheService()
    
    async def get_full_info(self, drug_name: str) -> dict[str, Any]:
        """
        Get comprehensive drug information.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Complete drug information from all sources
        """
        cache_key = self._cache_key("full_info", drug_name)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Get FDA label sections
        label_info = await self.fda.get_drug_label_sections(drug_name)
        
        # Search RxNorm for drug
        rxnorm_concepts = await self.rxnorm.search_by_name(drug_name, max_results=1)
        
        rxnorm_info = None
        if rxnorm_concepts:
            drug = await self.rxnorm.get_by_rxcui(rxnorm_concepts[0].rxcui)
            if drug:
                rxnorm_info = {
                    "rxcui": drug.rxcui,
                    "name": drug.name,
                    "drug_type": drug.drug_type.value,
                    "drug_classes": drug.drug_classes,
                }
        
        # Get Taiwan-specific information
        taiwan_info = self._get_taiwan_info(drug_name)
        
        result = {
            "drug_name": drug_name,
            "rxnorm": rxnorm_info,
            "label": label_info,
            "taiwan": taiwan_info,
        }
        
        self.cache.set(cache_key, result)
        return result
    
    def _get_taiwan_info(self, drug_name: str) -> dict[str, Any] | None:
        """
        Get Taiwan-specific drug information.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Taiwan drug information including translation and NHI coverage
        """
        # Get Chinese name translation
        translation = translate_drug_name(drug_name)
        
        # Get NHI coverage information (synchronous lookup)
        nhi_coverage = get_nhi_coverage_info(drug_name)
        
        if not translation and not nhi_coverage:
            return None
        
        result = {}
        
        if translation:
            result["translation"] = {
                "english": translation.get("english"),
                "chinese_generic": translation.get("chinese_generic"),
                "chinese_brand": translation.get("chinese_brand", []),
                "category": translation.get("category"),
            }
            if translation.get("nickname"):
                result["translation"]["nickname"] = translation.get("nickname")
        
        if nhi_coverage:
            result["nhi"] = {
                "is_covered": nhi_coverage.get("is_covered", False),
                "coverage_type": nhi_coverage.get("coverage_type"),
                "indications": nhi_coverage.get("indications", []),
                "restrictions": nhi_coverage.get("restrictions", []),
                "prior_authorization_required": nhi_coverage.get("prior_authorization", False),
                "nhi_codes": nhi_coverage.get("nhi_codes", []),
            }
        
        return result
    
    async def get_dosage_info(self, drug_name: str) -> dict[str, Any]:
        """
        Get dosage and administration information.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Dosage information
        """
        cache_key = self._cache_key("dosage_info", drug_name)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        label_info = await self.fda.get_drug_label_sections(drug_name)
        
        if not label_info:
            return {"drug_name": drug_name, "dosage_info": None}
        
        result = {
            "drug_name": drug_name,
            "dosage_and_administration": label_info.get("dosage_and_administration", []),
            "indications_and_usage": label_info.get("indications_and_usage", []),
            "route": label_info.get("route", []),
            "pediatric_use": label_info.get("pediatric_use", []),
            "geriatric_use": label_info.get("geriatric_use", []),
        }
        
        self.cache.set(cache_key, result)
        return result
    
    async def get_warnings(self, drug_name: str) -> dict[str, Any]:
        """
        Get warnings and contraindications.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Warning information
        """
        cache_key = self._cache_key("warnings", drug_name)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        label_info = await self.fda.get_drug_label_sections(drug_name)
        
        if not label_info:
            return {"drug_name": drug_name, "warnings": None}
        
        result = {
            "drug_name": drug_name,
            "contraindications": label_info.get("contraindications", []),
            "warnings": label_info.get("warnings", []),
            "warnings_and_cautions": label_info.get("warnings_and_cautions", []),
            "adverse_reactions": label_info.get("adverse_reactions", []),
            "overdosage": label_info.get("overdosage", []),
        }
        
        self.cache.set(cache_key, result)
        return result
    
    async def get_pharmacology(self, drug_name: str) -> dict[str, Any]:
        """
        Get pharmacology information.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Pharmacology information
        """
        cache_key = self._cache_key("pharmacology", drug_name)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        label_info = await self.fda.get_drug_label_sections(drug_name)
        
        if not label_info:
            return {"drug_name": drug_name, "pharmacology": None}
        
        result = {
            "drug_name": drug_name,
            "clinical_pharmacology": label_info.get("clinical_pharmacology", []),
            "mechanism_of_action": label_info.get("mechanism_of_action", []),
            "pharmacokinetics": label_info.get("pharmacokinetics", []),
        }
        
        self.cache.set(cache_key, result)
        return result
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = ":".join(str(a).lower() for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
