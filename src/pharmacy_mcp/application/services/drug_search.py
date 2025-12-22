"""Drug search service."""

import hashlib
from typing import Any

from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService
from pharmacy_mcp.domain.entities.drug import DrugConcept


class DrugSearchService:
    """Service for searching drugs across multiple sources."""
    
    def __init__(
        self,
        rxnorm_client: RxNormClient | None = None,
        fda_client: FDAClient | None = None,
        cache: CacheService | None = None,
    ):
        self.rxnorm = rxnorm_client or RxNormClient()
        self.fda = fda_client or FDAClient()
        self.cache = cache or CacheService()
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """
        Search for drugs by name.
        
        Args:
            query: Search query (drug name)
            max_results: Maximum results to return
            
        Returns:
            Search results from multiple sources
        """
        cache_key = self._cache_key("search", query, max_results)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Search RxNorm
        rxnorm_results = await self.rxnorm.search_by_name(query, max_results)
        
        # Search FDA
        fda_results = await self.fda.search_drug_labels(query, max_results)
        
        result = {
            "query": query,
            "rxnorm": [
                {
                    "rxcui": r.rxcui,
                    "name": r.name,
                    "synonym": r.synonym,
                    "term_type": r.tty,
                }
                for r in rxnorm_results
            ],
            "fda": [
                {
                    "brand_name": r.get("openfda", {}).get("brand_name", []),
                    "generic_name": r.get("openfda", {}).get("generic_name", []),
                    "manufacturer": r.get("openfda", {}).get("manufacturer_name", []),
                }
                for r in fda_results
            ],
            "total_count": len(rxnorm_results) + len(fda_results),
        }
        
        self.cache.set(cache_key, result)
        return result
    
    async def search_by_rxcui(self, rxcui: str) -> dict[str, Any] | None:
        """
        Get drug details by RxCUI.
        
        Args:
            rxcui: RxNorm Concept Unique Identifier
            
        Returns:
            Drug details or None
        """
        cache_key = self._cache_key("rxcui", rxcui)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        drug = await self.rxnorm.get_by_rxcui(rxcui)
        if not drug:
            return None
        
        result = {
            "rxcui": drug.rxcui,
            "name": drug.name,
            "drug_type": drug.drug_type.value,
            "drug_classes": drug.drug_classes,
            "atc_codes": drug.atc_codes,
        }
        
        self.cache.set(cache_key, result)
        return result
    
    async def autocomplete(
        self,
        prefix: str,
        max_results: int = 5
    ) -> list[DrugConcept]:
        """
        Autocomplete drug names.
        
        Args:
            prefix: Start of drug name
            max_results: Maximum suggestions
            
        Returns:
            List of drug suggestions
        """
        # Use RxNorm approximate term search for autocomplete
        return await self.rxnorm.search_by_name(prefix, max_results)
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = ":".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
