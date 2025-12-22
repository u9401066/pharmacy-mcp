"""Taiwan TFDA (食品藥物管理署) Open Data API client."""

import httpx
from typing import Any

from pharmacy_mcp.config import settings
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService


class TFDAClient:
    """Client for Taiwan FDA Open Data Platform.
    
    Data source: https://data.gov.tw/dataset/9122 (全部藥品許可證資料集)
    Update frequency: Weekly (every Monday)
    """
    
    # 政府開放資料 URL
    DRUG_PERMITS_JSON_URL = "https://data.fda.gov.tw/opendata/exportDataList.do?method=ExportData&InfoId=36&logType=5"
    ACTIVE_PERMITS_JSON_URL = "https://data.fda.gov.tw/opendata/exportDataList.do?method=ExportData&InfoId=37&logType=5"
    
    # Cache TTL: 7 days (matching government update frequency)
    CACHE_TTL = 7 * 24 * 60 * 60  # 604800 seconds
    
    def __init__(self, cache_service: CacheService | None = None):
        self.timeout = settings.request_timeout
        self._cache = cache_service or CacheService()
        self._drug_data: list[dict] | None = None
    
    async def _fetch_drug_permits(self, active_only: bool = True) -> list[dict]:
        """
        Fetch drug permits from TFDA open data.
        
        Args:
            active_only: If True, fetch only active (non-cancelled) permits
            
        Returns:
            List of drug permit records
        """
        cache_key = "tfda:active_permits" if active_only else "tfda:all_permits"
        
        # Check cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Fetch from API
        url = self.ACTIVE_PERMITS_JSON_URL if active_only else self.DRUG_PERMITS_JSON_URL
        
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for large file
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        # Cache the data
        self._cache.set(cache_key, data, ttl=self.CACHE_TTL)
        
        return data
    
    async def search_drug_by_name(
        self,
        query: str,
        limit: int = 20,
        active_only: bool = True
    ) -> list[dict]:
        """
        Search drugs by Chinese or English name.
        
        Args:
            query: Search query (Chinese or English drug name)
            limit: Maximum number of results
            active_only: If True, search only active permits
            
        Returns:
            List of matching drug records
        """
        data = await self._fetch_drug_permits(active_only)
        query_lower = query.lower()
        
        results = []
        for drug in data:
            chinese_name = drug.get("中文品名", "").lower()
            english_name = drug.get("英文品名", "").lower()
            ingredients = drug.get("主成分略述", "").lower()
            
            if (query_lower in chinese_name or 
                query_lower in english_name or 
                query_lower in ingredients):
                results.append(self._format_drug_record(drug))
                if len(results) >= limit:
                    break
        
        return results
    
    async def search_drug_by_permit_number(
        self,
        permit_number: str
    ) -> dict | None:
        """
        Get drug by permit number (許可證字號).
        
        Args:
            permit_number: e.g., "衛署藥製字第012345號"
            
        Returns:
            Drug record or None
        """
        data = await self._fetch_drug_permits(active_only=False)
        
        for drug in data:
            if drug.get("許可證字號") == permit_number:
                return self._format_drug_record(drug)
        
        return None
    
    async def search_drug_by_ingredient(
        self,
        ingredient: str,
        limit: int = 50,
        active_only: bool = True
    ) -> list[dict]:
        """
        Search drugs by ingredient (主成分).
        
        Args:
            ingredient: Ingredient name to search
            limit: Maximum number of results
            active_only: If True, search only active permits
            
        Returns:
            List of matching drug records
        """
        data = await self._fetch_drug_permits(active_only)
        query_lower = ingredient.lower()
        
        results = []
        for drug in data:
            ingredients = drug.get("主成分略述", "").lower()
            
            if query_lower in ingredients:
                results.append(self._format_drug_record(drug))
                if len(results) >= limit:
                    break
        
        return results
    
    async def search_drug_by_manufacturer(
        self,
        manufacturer: str,
        limit: int = 50,
        active_only: bool = True
    ) -> list[dict]:
        """
        Search drugs by manufacturer name.
        
        Args:
            manufacturer: Manufacturer name to search
            limit: Maximum number of results
            active_only: If True, search only active permits
            
        Returns:
            List of matching drug records
        """
        data = await self._fetch_drug_permits(active_only)
        query_lower = manufacturer.lower()
        
        results = []
        for drug in data:
            mfr_name = drug.get("製造廠名稱", "").lower()
            applicant = drug.get("申請商名稱", "").lower()
            
            if query_lower in mfr_name or query_lower in applicant:
                results.append(self._format_drug_record(drug))
                if len(results) >= limit:
                    break
        
        return results
    
    async def get_drug_statistics(self) -> dict:
        """
        Get statistics about Taiwan drug permits.
        
        Returns:
            Statistics dictionary
        """
        all_data = await self._fetch_drug_permits(active_only=False)
        active_data = await self._fetch_drug_permits(active_only=True)
        
        # Count by dosage form (劑型)
        dosage_forms: dict[str, int] = {}
        for drug in active_data:
            form = drug.get("劑型", "未知")
            dosage_forms[form] = dosage_forms.get(form, 0) + 1
        
        return {
            "total_permits": len(all_data),
            "active_permits": len(active_data),
            "cancelled_permits": len(all_data) - len(active_data),
            "dosage_form_distribution": dict(sorted(
                dosage_forms.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20])  # Top 20 dosage forms
        }
    
    def _format_drug_record(self, raw: dict) -> dict:
        """
        Format raw TFDA record to standardized format.
        
        Args:
            raw: Raw record from TFDA API
            
        Returns:
            Formatted drug record
        """
        return {
            "permit_number": raw.get("許可證字號", ""),
            "chinese_name": raw.get("中文品名", ""),
            "english_name": raw.get("英文品名", ""),
            "dosage_form": raw.get("劑型", ""),
            "packaging": raw.get("包裝", ""),
            "drug_category": raw.get("藥品類別", ""),
            "controlled_drug_class": raw.get("管制藥品分類級別", ""),
            "ingredients": raw.get("主成分略述", ""),
            "indications": raw.get("適應症", ""),
            "applicant": {
                "name": raw.get("申請商名稱", ""),
                "address": raw.get("申請商地址", ""),
                "tax_id": raw.get("申請商統一編號", "")
            },
            "manufacturer": {
                "name": raw.get("製造廠名稱", ""),
                "address": raw.get("製造廠廠址", ""),
                "country": raw.get("製造廠國別", "")
            },
            "dates": {
                "issue_date": raw.get("發證日期", ""),
                "expiry_date": raw.get("有效日期", ""),
                "cancellation_date": raw.get("註銷日期", "")
            },
            "status": {
                "is_cancelled": bool(raw.get("註銷狀態")),
                "cancellation_reason": raw.get("註銷理由", "")
            },
            "source": "TFDA"
        }
    
    async def clear_cache(self) -> None:
        """Clear cached TFDA data."""
        self._cache.delete("tfda:all_permits")
        self._cache.delete("tfda:active_permits")


# 中英文藥名對照表（常用藥品）
DRUG_NAME_MAPPING: dict[str, dict[str, str]] = {
    # === 抗凝血/抗血小板藥物 ===
    "warfarin": {
        "english": "Warfarin",
        "chinese_generic": "華法林",
        "chinese_brand": ["可邁丁", "脈化寧"],
        "category": "抗凝血劑"
    },
    "clopidogrel": {
        "english": "Clopidogrel",
        "chinese_generic": "氯吡格雷",
        "chinese_brand": ["保栓通", "波維"],
        "category": "抗血小板藥"
    },
    "aspirin": {
        "english": "Aspirin",
        "chinese_generic": "乙醯水楊酸",
        "chinese_brand": ["阿斯匹靈", "伯乃百"],
        "category": "解熱鎮痛/抗血小板"
    },
    "dabigatran": {
        "english": "Dabigatran",
        "chinese_generic": "達比加群",
        "chinese_brand": ["普栓達"],
        "category": "新型口服抗凝血劑"
    },
    "rivaroxaban": {
        "english": "Rivaroxaban",
        "chinese_generic": "利伐沙班",
        "chinese_brand": ["拜瑞妥"],
        "category": "新型口服抗凝血劑"
    },
    "apixaban": {
        "english": "Apixaban",
        "chinese_generic": "阿哌沙班",
        "chinese_brand": ["艾必克凝"],
        "category": "新型口服抗凝血劑"
    },
    "edoxaban": {
        "english": "Edoxaban",
        "chinese_generic": "依度沙班",
        "chinese_brand": ["里先安"],
        "category": "新型口服抗凝血劑"
    },
    "ticagrelor": {
        "english": "Ticagrelor",
        "chinese_generic": "替格瑞洛",
        "chinese_brand": ["百無凝"],
        "category": "抗血小板藥"
    },
    "enoxaparin": {
        "english": "Enoxaparin",
        "chinese_generic": "依諾肝素",
        "chinese_brand": ["克立生"],
        "category": "低分子量肝素"
    },
    "heparin": {
        "english": "Heparin",
        "chinese_generic": "肝素",
        "chinese_brand": ["海乳寧"],
        "category": "抗凝血劑"
    },
    
    # === 降血脂藥物 ===
    "atorvastatin": {
        "english": "Atorvastatin",
        "chinese_generic": "阿托伐他汀",
        "chinese_brand": ["立普妥", "冠脂妥"],
        "category": "降血脂藥"
    },
    "rosuvastatin": {
        "english": "Rosuvastatin",
        "chinese_generic": "瑞舒伐他汀",
        "chinese_brand": ["冠脂妥", "百思寧"],
        "category": "降血脂藥"
    },
    "simvastatin": {
        "english": "Simvastatin",
        "chinese_generic": "辛伐他汀",
        "chinese_brand": ["素果", "維妥力"],
        "category": "降血脂藥"
    },
    "ezetimibe": {
        "english": "Ezetimibe",
        "chinese_generic": "依折麥布",
        "chinese_brand": ["怡妥"],
        "category": "降血脂藥"
    },
    "fenofibrate": {
        "english": "Fenofibrate",
        "chinese_generic": "非諾貝特",
        "chinese_brand": ["立寧平", "弗尼利脂"],
        "category": "降血脂藥"
    },
    "pitavastatin": {
        "english": "Pitavastatin",
        "chinese_generic": "匹伐他汀",
        "chinese_brand": ["力清之"],
        "category": "降血脂藥"
    },
    "pravastatin": {
        "english": "Pravastatin",
        "chinese_generic": "普伐他汀",
        "chinese_brand": ["美百樂鎮"],
        "category": "降血脂藥"
    },
    
    # === 降血糖藥物 ===
    "metformin": {
        "english": "Metformin",
        "chinese_generic": "二甲雙胍",
        "chinese_brand": ["庫魯化", "格華止"],
        "category": "降血糖藥"
    },
    "insulin": {
        "english": "Insulin",
        "chinese_generic": "胰島素",
        "chinese_brand": ["諾和靈", "優泌林", "蘭德仕"],
        "category": "降血糖藥"
    },
    "glimepiride": {
        "english": "Glimepiride",
        "chinese_generic": "格列美脲",
        "chinese_brand": ["瑪爾胰"],
        "category": "降血糖藥"
    },
    "gliclazide": {
        "english": "Gliclazide",
        "chinese_generic": "格列齊特",
        "chinese_brand": ["岱蜜克龍"],
        "category": "降血糖藥"
    },
    "sitagliptin": {
        "english": "Sitagliptin",
        "chinese_generic": "西格列汀",
        "chinese_brand": ["佳糖維"],
        "category": "DPP-4抑制劑"
    },
    "empagliflozin": {
        "english": "Empagliflozin",
        "chinese_generic": "恩格列淨",
        "chinese_brand": ["恩排糖"],
        "category": "SGLT2抑制劑"
    },
    "dapagliflozin": {
        "english": "Dapagliflozin",
        "chinese_generic": "達格列淨",
        "chinese_brand": ["福適佳"],
        "category": "SGLT2抑制劑"
    },
    "liraglutide": {
        "english": "Liraglutide",
        "chinese_generic": "利拉魯肽",
        "chinese_brand": ["胰妥讚", "善纖達"],
        "category": "GLP-1受體促效劑"
    },
    "semaglutide": {
        "english": "Semaglutide",
        "chinese_generic": "司美格魯肽",
        "chinese_brand": ["胰妥善", "瑞倍適"],
        "category": "GLP-1受體促效劑"
    },
    "dulaglutide": {
        "english": "Dulaglutide",
        "chinese_generic": "度拉糖肽",
        "chinese_brand": ["易週糖"],
        "category": "GLP-1受體促效劑"
    },
    "pioglitazone": {
        "english": "Pioglitazone",
        "chinese_generic": "吡格列酮",
        "chinese_brand": ["愛妥糖"],
        "category": "TZD降血糖藥"
    },
    "acarbose": {
        "english": "Acarbose",
        "chinese_generic": "阿卡波糖",
        "chinese_brand": ["醣祿"],
        "category": "α-葡萄糖苷酶抑制劑"
    },
    
    # === 降血壓藥物 ===
    "amlodipine": {
        "english": "Amlodipine",
        "chinese_generic": "氨氯地平",
        "chinese_brand": ["脈優", "絡活喜"],
        "category": "鈣離子阻斷劑"
    },
    "lisinopril": {
        "english": "Lisinopril",
        "chinese_generic": "賴諾普利",
        "chinese_brand": ["捷賜瑞"],
        "category": "ACE抑制劑"
    },
    "losartan": {
        "english": "Losartan",
        "chinese_generic": "氯沙坦",
        "chinese_brand": ["可悅您"],
        "category": "ARB"
    },
    "valsartan": {
        "english": "Valsartan",
        "chinese_generic": "纈沙坦",
        "chinese_brand": ["得安穩"],
        "category": "ARB"
    },
    "metoprolol": {
        "english": "Metoprolol",
        "chinese_generic": "美托洛爾",
        "chinese_brand": ["舒壓寧", "倍他樂克"],
        "category": "β阻斷劑"
    },
    "bisoprolol": {
        "english": "Bisoprolol",
        "chinese_generic": "比索洛爾",
        "chinese_brand": ["康肯"],
        "category": "β阻斷劑"
    },
    "carvedilol": {
        "english": "Carvedilol",
        "chinese_generic": "卡維地洛",
        "chinese_brand": ["達利全"],
        "category": "α/β阻斷劑"
    },
    "furosemide": {
        "english": "Furosemide",
        "chinese_generic": "呋塞米",
        "chinese_brand": ["來適泄", "服爾美得"],
        "category": "利尿劑"
    },
    "hydrochlorothiazide": {
        "english": "Hydrochlorothiazide",
        "chinese_generic": "氫氯噻嗪",
        "chinese_brand": ["雙乎達"],
        "category": "利尿劑"
    },
    "spironolactone": {
        "english": "Spironolactone",
        "chinese_generic": "螺內酯",
        "chinese_brand": ["安達通"],
        "category": "保鉀利尿劑"
    },
    "enalapril": {
        "english": "Enalapril",
        "chinese_generic": "依那普利",
        "chinese_brand": ["益壓穩"],
        "category": "ACE抑制劑"
    },
    "ramipril": {
        "english": "Ramipril",
        "chinese_generic": "雷米普利",
        "chinese_brand": ["心達舒"],
        "category": "ACE抑制劑"
    },
    "irbesartan": {
        "english": "Irbesartan",
        "chinese_generic": "厄貝沙坦",
        "chinese_brand": ["安普諾維"],
        "category": "ARB"
    },
    "telmisartan": {
        "english": "Telmisartan",
        "chinese_generic": "替米沙坦",
        "chinese_brand": ["必康平"],
        "category": "ARB"
    },
    "nifedipine": {
        "english": "Nifedipine",
        "chinese_generic": "硝苯地平",
        "chinese_brand": ["冠達悅", "壓達樂"],
        "category": "鈣離子阻斷劑"
    },
    "diltiazem": {
        "english": "Diltiazem",
        "chinese_generic": "地爾硫卓",
        "chinese_brand": ["乾速達"],
        "category": "鈣離子阻斷劑"
    },
    
    # === 質子幫浦抑制劑 ===
    "omeprazole": {
        "english": "Omeprazole",
        "chinese_generic": "奧美拉唑",
        "chinese_brand": ["耐適恩", "洛乎克"],
        "category": "質子幫浦抑制劑"
    },
    "esomeprazole": {
        "english": "Esomeprazole",
        "chinese_generic": "埃索美拉唑",
        "chinese_brand": ["耐適恩"],
        "category": "質子幫浦抑制劑"
    },
    "pantoprazole": {
        "english": "Pantoprazole",
        "chinese_generic": "泮托拉唑",
        "chinese_brand": ["保衛康治潰樂"],
        "category": "質子幫浦抑制劑"
    },
    "lansoprazole": {
        "english": "Lansoprazole",
        "chinese_generic": "蘭索拉唑",
        "chinese_brand": ["泰克胃通"],
        "category": "質子幫浦抑制劑"
    },
    "rabeprazole": {
        "english": "Rabeprazole",
        "chinese_generic": "雷貝拉唑",
        "chinese_brand": ["百抑潰"],
        "category": "質子幫浦抑制劑"
    },
    
    # === 抗生素 ===
    "amoxicillin": {
        "english": "Amoxicillin",
        "chinese_generic": "阿莫西林",
        "chinese_brand": ["安滅菌", "萬博黴素"],
        "category": "抗生素"
    },
    "azithromycin": {
        "english": "Azithromycin",
        "chinese_generic": "阿奇黴素",
        "chinese_brand": ["日舒"],
        "category": "抗生素"
    },
    "levofloxacin": {
        "english": "Levofloxacin",
        "chinese_generic": "左氧氟沙星",
        "chinese_brand": ["可樂必妥"],
        "category": "抗生素"
    },
    "ciprofloxacin": {
        "english": "Ciprofloxacin",
        "chinese_generic": "環丙沙星",
        "chinese_brand": ["速博新"],
        "category": "抗生素"
    },
    "cephalexin": {
        "english": "Cephalexin",
        "chinese_generic": "頭孢氨苄",
        "chinese_brand": ["乃乃靈"],
        "category": "抗生素"
    },
    "doxycycline": {
        "english": "Doxycycline",
        "chinese_generic": "多西環素",
        "chinese_brand": ["偉乃星"],
        "category": "抗生素"
    },
    "vancomycin": {
        "english": "Vancomycin",
        "chinese_generic": "萬古黴素",
        "chinese_brand": ["穩乃黴素"],
        "category": "抗生素"
    },
    
    # === 神經/精神科用藥 ===
    "gabapentin": {
        "english": "Gabapentin",
        "chinese_generic": "加巴噴丁",
        "chinese_brand": ["鎮頑癲", "紐洛平"],
        "category": "抗癲癇/神經痛藥"
    },
    "pregabalin": {
        "english": "Pregabalin",
        "chinese_generic": "普瑞巴林",
        "chinese_brand": ["利瑞卡"],
        "category": "神經痛藥"
    },
    "carbamazepine": {
        "english": "Carbamazepine",
        "chinese_generic": "卡馬西平",
        "chinese_brand": ["癲通"],
        "category": "抗癲癇藥"
    },
    "valproic acid": {
        "english": "Valproic Acid",
        "chinese_generic": "丙戊酸",
        "chinese_brand": ["帝拔癲"],
        "category": "抗癲癇藥"
    },
    "phenytoin": {
        "english": "Phenytoin",
        "chinese_generic": "苯妥英",
        "chinese_brand": ["乙內醯脲"],
        "category": "抗癲癇藥"
    },
    "levetiracetam": {
        "english": "Levetiracetam",
        "chinese_generic": "左乙拉西坦",
        "chinese_brand": ["優閒"],
        "category": "抗癲癇藥"
    },
    "sertraline": {
        "english": "Sertraline",
        "chinese_generic": "舍曲林",
        "chinese_brand": ["樂復得"],
        "category": "抗憂鬱藥"
    },
    "escitalopram": {
        "english": "Escitalopram",
        "chinese_generic": "艾司西酞普蘭",
        "chinese_brand": ["立普能"],
        "category": "抗憂鬱藥"
    },
    "fluoxetine": {
        "english": "Fluoxetine",
        "chinese_generic": "氟西汀",
        "chinese_brand": ["百憂解"],
        "category": "抗憂鬱藥"
    },
    "duloxetine": {
        "english": "Duloxetine",
        "chinese_generic": "度洛西汀",
        "chinese_brand": ["千憂解"],
        "category": "抗憂鬱藥"
    },
    "quetiapine": {
        "english": "Quetiapine",
        "chinese_generic": "喹硫平",
        "chinese_brand": ["思樂康"],
        "category": "抗精神病藥"
    },
    "olanzapine": {
        "english": "Olanzapine",
        "chinese_generic": "奧氮平",
        "chinese_brand": ["津普速"],
        "category": "抗精神病藥"
    },
    "risperidone": {
        "english": "Risperidone",
        "chinese_generic": "利培酮",
        "chinese_brand": ["理思必妥"],
        "category": "抗精神病藥"
    },
    "alprazolam": {
        "english": "Alprazolam",
        "chinese_generic": "阿普唑侖",
        "chinese_brand": ["贊安諾"],
        "category": "抗焦慮藥"
    },
    "lorazepam": {
        "english": "Lorazepam",
        "chinese_generic": "勞拉西泮",
        "chinese_brand": ["安定文"],
        "category": "抗焦慮藥"
    },
    "zolpidem": {
        "english": "Zolpidem",
        "chinese_generic": "唑吡坦",
        "chinese_brand": ["史蒂諾斯"],
        "category": "安眠藥"
    },
    "donepezil": {
        "english": "Donepezil",
        "chinese_generic": "多奈哌齊",
        "chinese_brand": ["愛憶欣"],
        "category": "失智症用藥"
    },
    "memantine": {
        "english": "Memantine",
        "chinese_generic": "美金剛",
        "chinese_brand": ["憶必佳", "威智"],
        "category": "失智症用藥"
    },
    
    # === 止痛藥 ===
    "acetaminophen": {
        "english": "Acetaminophen",
        "chinese_generic": "乙醯胺酚",
        "chinese_brand": ["普拿疼", "必理痛", "斯斯"],
        "category": "解熱鎮痛藥"
    },
    "tramadol": {
        "english": "Tramadol",
        "chinese_generic": "曲馬多",
        "chinese_brand": ["及通安"],
        "category": "中樞性止痛藥"
    },
    "morphine": {
        "english": "Morphine",
        "chinese_generic": "嗎啡",
        "chinese_brand": ["硫酸嗎啡"],
        "category": "強效止痛藥"
    },
    "fentanyl": {
        "english": "Fentanyl",
        "chinese_generic": "芬太尼",
        "chinese_brand": ["吩坦尼", "多乐坦尼"],
        "category": "強效止痛藥"
    },
    "ibuprofen": {
        "english": "Ibuprofen",
        "chinese_generic": "布洛芬",
        "chinese_brand": ["醫炎錠"],
        "category": "非類固醇消炎藥"
    },
    "naproxen": {
        "english": "Naproxen",
        "chinese_generic": "萘普生",
        "chinese_brand": ["能百鎮"],
        "category": "非類固醇消炎藥"
    },
    "diclofenac": {
        "english": "Diclofenac",
        "chinese_generic": "雙氯芬酸",
        "chinese_brand": ["服他寧", "乙乃攝"],
        "category": "非類固醇消炎藥"
    },
    "celecoxib": {
        "english": "Celecoxib",
        "chinese_generic": "塞來昔布",
        "chinese_brand": ["希樂葆"],
        "category": "COX-2抑制劑"
    },
    "etoricoxib": {
        "english": "Etoricoxib",
        "chinese_generic": "依托考昔",
        "chinese_brand": ["萬乐克"],
        "category": "COX-2抑制劑"
    },
    
    # === 類固醇 ===
    "prednisone": {
        "english": "Prednisone",
        "chinese_generic": "潑尼松",
        "chinese_brand": ["必賴克廔", "強體松"],
        "category": "類固醇"
    },
    "prednisolone": {
        "english": "Prednisolone",
        "chinese_generic": "潑尼松龍",
        "chinese_brand": ["必賴克廔"],
        "category": "類固醇"
    },
    "methylprednisolone": {
        "english": "Methylprednisolone",
        "chinese_generic": "甲潑尼龍",
        "chinese_brand": ["美乃速朗錠", "速立"],
        "category": "類固醇"
    },
    "dexamethasone": {
        "english": "Dexamethasone",
        "chinese_generic": "地塞米松",
        "chinese_brand": ["迪皮質"],
        "category": "類固醇"
    },
    "hydrocortisone": {
        "english": "Hydrocortisone",
        "chinese_generic": "氫化可體松",
        "chinese_brand": ["可體松"],
        "category": "類固醇"
    },
    
    # === 呼吸道用藥 ===
    "salbutamol": {
        "english": "Salbutamol",
        "chinese_generic": "沙丁胺醇",
        "chinese_brand": ["乙妥平", "備勞喘"],
        "category": "支氣管擴張劑"
    },
    "formoterol": {
        "english": "Formoterol",
        "chinese_generic": "福莫特羅",
        "chinese_brand": ["歐乐舒"],
        "category": "支氣管擴張劑"
    },
    "budesonide": {
        "english": "Budesonide",
        "chinese_generic": "布地奈德",
        "chinese_brand": ["普米克"],
        "category": "吸入性類固醇"
    },
    "fluticasone": {
        "english": "Fluticasone",
        "chinese_generic": "氟替卡松",
        "chinese_brand": ["輔舒酮", "使肺泰"],
        "category": "吸入性類固醇"
    },
    "tiotropium": {
        "english": "Tiotropium",
        "chinese_generic": "噻托溴銨",
        "chinese_brand": ["適喘樂"],
        "category": "COPD用藥"
    },
    "montelukast": {
        "english": "Montelukast",
        "chinese_generic": "孟魯司特",
        "chinese_brand": ["欣流"],
        "category": "白三烯拮抗劑"
    },
    
    # === 麻醉/手術用藥 ===
    "propofol": {
        "english": "Propofol",
        "chinese_generic": "丙泊酚",
        "chinese_brand": ["乳乳白安", "得普洛福"],
        "category": "全身麻醉劑",
        "nickname": "牛奶針"
    },
    "midazolam": {
        "english": "Midazolam",
        "chinese_generic": "咪達唑侖",
        "chinese_brand": ["導眠靜"],
        "category": "鎮靜劑"
    },
    "ketamine": {
        "english": "Ketamine",
        "chinese_generic": "氯胺酮",
        "chinese_brand": ["乾達明"],
        "category": "解離性麻醉劑"
    },
    "lidocaine": {
        "english": "Lidocaine",
        "chinese_generic": "利多卡因",
        "chinese_brand": ["理多快"],
        "category": "局部麻醉劑"
    },
    "bupivacaine": {
        "english": "Bupivacaine",
        "chinese_generic": "布比卡因",
        "chinese_brand": ["麻乐凱因"],
        "category": "局部麻醉劑"
    },
    "rocuronium": {
        "english": "Rocuronium",
        "chinese_generic": "羅庫溴銨",
        "chinese_brand": ["乙速朗"],
        "category": "肌肉鬆弛劑"
    },
    "sugammadex": {
        "english": "Sugammadex",
        "chinese_generic": "舒更葡糖鈉",
        "chinese_brand": ["乙順朗"],
        "category": "肌鬆解藥"
    },
    "neostigmine": {
        "english": "Neostigmine",
        "chinese_generic": "新斯的明",
        "chinese_brand": ["新的明"],
        "category": "肌鬆解藥"
    },
    "atropine": {
        "english": "Atropine",
        "chinese_generic": "阿托品",
        "chinese_brand": ["阿托平"],
        "category": "抗膽鹼藥"
    },
    "ondansetron": {
        "english": "Ondansetron",
        "chinese_generic": "昂丹司瓊",
        "chinese_brand": ["鎮吐靈"],
        "category": "止吐劑"
    },
    "dexmedetomidine": {
        "english": "Dexmedetomidine",
        "chinese_generic": "右美托咪定",
        "chinese_brand": ["普力麻"],
        "category": "鎮靜劑"
    },
    
    # === 生物製劑/標靶藥物 ===
    "adalimumab": {
        "english": "Adalimumab",
        "chinese_generic": "阿達木單抗",
        "chinese_brand": ["復邁"],
        "category": "生物製劑"
    },
    "etanercept": {
        "english": "Etanercept",
        "chinese_generic": "依那西普",
        "chinese_brand": ["恩博"],
        "category": "生物製劑"
    },
    "rituximab": {
        "english": "Rituximab",
        "chinese_generic": "利妥昔單抗",
        "chinese_brand": ["莫須瘤"],
        "category": "生物製劑"
    },
    "trastuzumab": {
        "english": "Trastuzumab",
        "chinese_generic": "曲妥珠單抗",
        "chinese_brand": ["賀癌平"],
        "category": "標靶藥物"
    },
    "bevacizumab": {
        "english": "Bevacizumab",
        "chinese_generic": "貝伐單抗",
        "chinese_brand": ["癌思停"],
        "category": "標靶藥物"
    },
    "pembrolizumab": {
        "english": "Pembrolizumab",
        "chinese_generic": "帕博利珠單抗",
        "chinese_brand": ["吉舒達"],
        "category": "免疫檢查點抑制劑"
    },
    "nivolumab": {
        "english": "Nivolumab",
        "chinese_generic": "納武利尤單抗",
        "chinese_brand": ["保疾伏"],
        "category": "免疫檢查點抑制劑"
    },
    "imatinib": {
        "english": "Imatinib",
        "chinese_generic": "伊馬替尼",
        "chinese_brand": ["基利克"],
        "category": "標靶藥物"
    },
    "gefitinib": {
        "english": "Gefitinib",
        "chinese_generic": "吉非替尼",
        "chinese_brand": ["艾瑞莎"],
        "category": "標靶藥物"
    },
    "erlotinib": {
        "english": "Erlotinib",
        "chinese_generic": "厄洛替尼",
        "chinese_brand": ["得舒緩"],
        "category": "標靶藥物"
    },
    "osimertinib": {
        "english": "Osimertinib",
        "chinese_generic": "奧希替尼",
        "chinese_brand": ["泰格莎"],
        "category": "標靶藥物"
    },
    "afatinib": {
        "english": "Afatinib",
        "chinese_generic": "阿法替尼",
        "chinese_brand": ["妥復克"],
        "category": "標靶藥物"
    },
    "sorafenib": {
        "english": "Sorafenib",
        "chinese_generic": "索拉非尼",
        "chinese_brand": ["蕾莎瓦"],
        "category": "標靶藥物"
    },
    "lenvatinib": {
        "english": "Lenvatinib",
        "chinese_generic": "樂伐替尼",
        "chinese_brand": ["樂衛瑪"],
        "category": "標靶藥物"
    },
    
    # === 甲狀腺用藥 ===
    "levothyroxine": {
        "english": "Levothyroxine",
        "chinese_generic": "左甲狀腺素",
        "chinese_brand": ["昂特欣"],
        "category": "甲狀腺素"
    },
    "propylthiouracil": {
        "english": "Propylthiouracil",
        "chinese_generic": "丙硫氧嘧啶",
        "chinese_brand": ["僕乃滿"],
        "category": "抗甲狀腺藥"
    },
    "methimazole": {
        "english": "Methimazole",
        "chinese_generic": "甲巯咪唑",
        "chinese_brand": ["乙硫乃寧"],
        "category": "抗甲狀腺藥"
    },
    
    # === 骨質疏鬆用藥 ===
    "alendronate": {
        "english": "Alendronate",
        "chinese_generic": "阿侖膦酸",
        "chinese_brand": ["福善美"],
        "category": "雙磷酸鹽"
    },
    "zoledronic acid": {
        "english": "Zoledronic Acid",
        "chinese_generic": "唑來膦酸",
        "chinese_brand": ["骨力強"],
        "category": "雙磷酸鹽"
    },
    "denosumab": {
        "english": "Denosumab",
        "chinese_generic": "地舒單抗",
        "chinese_brand": ["保骼麗"],
        "category": "骨質疏鬆用藥"
    },
    "teriparatide": {
        "english": "Teriparatide",
        "chinese_generic": "特立帕肽",
        "chinese_brand": ["骨穩"],
        "category": "骨質疏鬆用藥"
    },
    
    # === 免疫抑制劑 ===
    "tacrolimus": {
        "english": "Tacrolimus",
        "chinese_generic": "他克莫司",
        "chinese_brand": ["普樂可復"],
        "category": "免疫抑制劑"
    },
    "cyclosporine": {
        "english": "Cyclosporine",
        "chinese_generic": "環孢素",
        "chinese_brand": ["新體睦"],
        "category": "免疫抑制劑"
    },
    "mycophenolate": {
        "english": "Mycophenolate",
        "chinese_generic": "黴酚酸酯",
        "chinese_brand": ["山喜多"],
        "category": "免疫抑制劑"
    },
    "azathioprine": {
        "english": "Azathioprine",
        "chinese_generic": "硫唑嘌呤",
        "chinese_brand": ["移護寧"],
        "category": "免疫抑制劑"
    },
    "methotrexate": {
        "english": "Methotrexate",
        "chinese_generic": "甲氨蝶呤",
        "chinese_brand": ["滅殺除癌"],
        "category": "抗代謝藥/免疫調節劑"
    },
    
    # === 抗痛風用藥 ===
    "allopurinol": {
        "english": "Allopurinol",
        "chinese_generic": "別嘌呤醇",
        "chinese_brand": ["乙嘌寧"],
        "category": "降尿酸藥"
    },
    "febuxostat": {
        "english": "Febuxostat",
        "chinese_generic": "非布索坦",
        "chinese_brand": ["福避痛"],
        "category": "降尿酸藥"
    },
    "colchicine": {
        "english": "Colchicine",
        "chinese_generic": "秋水仙素",
        "chinese_brand": ["秋乙菌素"],
        "category": "抗痛風藥"
    },
    
    # === 抗組織胺 ===
    "cetirizine": {
        "english": "Cetirizine",
        "chinese_generic": "西替利嗪",
        "chinese_brand": ["驅異樂"],
        "category": "抗組織胺"
    },
    "loratadine": {
        "english": "Loratadine",
        "chinese_generic": "氯雷他定",
        "chinese_brand": ["克敏能"],
        "category": "抗組織胺"
    },
    "fexofenadine": {
        "english": "Fexofenadine",
        "chinese_generic": "非索非那定",
        "chinese_brand": ["艾來"],
        "category": "抗組織胺"
    },
    "levocetirizine": {
        "english": "Levocetirizine",
        "chinese_generic": "左西替利嗪",
        "chinese_brand": ["驅塵利"],
        "category": "抗組織胺"
    },
    "diphenhydramine": {
        "english": "Diphenhydramine",
        "chinese_generic": "苯海拉明",
        "chinese_brand": ["芬那明"],
        "category": "抗組織胺"
    }
}


def translate_drug_name(
    name: str,
    to_language: str = "chinese"
) -> dict[str, Any] | None:
    """
    Translate drug name between English and Chinese.
    
    Args:
        name: Drug name to translate
        to_language: Target language ("chinese" or "english")
        
    Returns:
        Translation result or None if not found
    """
    name_lower = name.lower().strip()
    
    # Direct lookup
    if name_lower in DRUG_NAME_MAPPING:
        return DRUG_NAME_MAPPING[name_lower]
    
    # Reverse lookup (Chinese to English)
    for eng_name, info in DRUG_NAME_MAPPING.items():
        if name_lower == info.get("chinese_generic", "").lower():
            return {"english": eng_name, **info}
        
        brands = info.get("chinese_brand", [])
        if isinstance(brands, list):
            for brand in brands:
                if name_lower == brand.lower():
                    return {"english": eng_name, **info}
    
    return None
