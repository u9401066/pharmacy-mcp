# System Patterns

## 設計模式

### 1. Repository Pattern
用於 API 資料存取，將資料來源抽象化。

```python
class DrugRepository(Protocol):
    async def get_by_rxcui(self, rxcui: str) -> Drug | None: ...
    async def search_by_name(self, name: str) -> list[Drug]: ...
```

### 2. Service Pattern
應用層服務封裝業務邏輯。

```python
class DrugSearchService:
    def __init__(self, repo: DrugRepository, cache: CacheService):
        self.repo = repo
        self.cache = cache
    
    async def search(self, query: str) -> list[Drug]: ...
```

### 3. Factory Pattern
用於建立 API Client 實例。

```python
class APIClientFactory:
    @staticmethod
    def create_rxnorm_client() -> RxNormClient: ...
    @staticmethod
    def create_fda_client() -> FDAClient: ...
```

### 4. Integration Pattern (台灣整合)
自動整合本地化資訊到現有查詢流程。

```python
class DrugInfoService:
    def _get_taiwan_info(self, drug_name: str) -> dict | None:
        """Get Taiwan-specific drug information."""
        translation = translate_drug_name(drug_name)
        nhi_coverage = get_nhi_coverage_info(drug_name)
        return {"translation": translation, "nhi": nhi_coverage}
    
    async def get_full_info(self, drug_name: str) -> dict:
        # ... 原有查詢 ...
        result["taiwan"] = self._get_taiwan_info(drug_name)
        return result
```

## 編碼慣例

### 命名規範
- 類別: PascalCase (`DrugSearchService`)
- 函數/變數: snake_case (`search_drug_by_name`)
- 常數: UPPER_SNAKE_CASE (`API_BASE_URL`)
- MCP Tool: snake_case (`search_drug_by_name`)

### 目錄結構
```
domain/
├── entities/      # 實體類別
├── value_objects/ # 值物件
└── services/      # Domain Services
```

### 錯誤處理
```python
class DrugNotFoundError(Exception):
    """藥品不存在"""
    pass

class APIRateLimitError(Exception):
    """API 速率限制"""
    pass
```

## API 整合模式

### 重試機制
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10)
)
async def fetch_drug(rxcui: str) -> dict: ...
```

### 快取策略
```python
# 台灣資料 - 7 天 TTL（配合政府更新頻率）
TFDA_CACHE_TTL = 7 * 24 * 60 * 60  # 604800 seconds

# 健保資料 - 30 天 TTL（更新頻率較低）
NHI_CACHE_TTL = 30 * 24 * 60 * 60  # 2592000 seconds

@cached(ttl=86400)  # 24 hours
async def get_drug_info(rxcui: str) -> Drug: ...
```

## 台灣本地化模式

### 資料來源整合
```python
# 不自建資料庫，使用政府開放資料 + disk cache

TFDA_SOURCE = "https://data.fda.gov.tw/opendata/exportDataList.do"
NHI_SOURCE = "https://data.nhi.gov.tw/"

# 本地規則資料庫（因無公開 API）
NHI_COVERAGE_RULES: dict[str, dict] = {
    "warfarin": {...},
    "clopidogrel": {...},
    # 60+ 藥品規則
}

DRUG_NAME_MAPPING: dict[str, dict] = {
    "warfarin": {"chinese_generic": "華法林", ...},
    # 120+ 藥品對照
}
```

---
*Last updated: 2025-12-22*
