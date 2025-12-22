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
@cached(ttl=86400)  # 24 hours
async def get_drug_info(rxcui: str) -> Drug: ...
```

---
*Last updated: 2025-12-22*
