"""Taiwan NHI (健保署) Drug Data Client."""

import httpx
from typing import Any

from pharmacy_mcp.config import settings
from pharmacy_mcp.infrastructure.cache.disk_cache import CacheService


class NHIClient:
    """Client for Taiwan NHI (National Health Insurance) drug data.
    
    Data sources:
    - 健保用藥品項: https://data.nhi.gov.tw/
    - 藥品給付規定: https://www.nhi.gov.tw/
    
    Note: NHI doesn't provide direct API, data is from open data portal.
    """
    
    # 健保藥品開放資料 URL (政府資料開放平台)
    NHI_DRUG_PRICE_URL = "https://data.nhi.gov.tw/resource/Opendata/%e5%81%a5%e4%bf%9d%e7%94%a8%e8%97%a5%e5%93%81%e9%a0%85.csv"
    
    # Cache TTL: 30 days (NHI updates less frequently)
    CACHE_TTL = 30 * 24 * 60 * 60  # 2592000 seconds
    
    def __init__(self, cache_service: CacheService | None = None):
        self.timeout = settings.request_timeout
        self._cache = cache_service or CacheService()
    
    async def search_by_nhi_code(
        self,
        nhi_code: str
    ) -> dict | None:
        """
        Search drug by NHI code (健保代碼).
        
        Args:
            nhi_code: NHI drug code (e.g., "A000000000")
            
        Returns:
            Drug coverage information or None
        """
        # Check cache first
        cache_key = f"nhi:code:{nhi_code}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Since NHI data requires downloading large CSV,
        # we use a simplified lookup from our built-in database
        result = self._lookup_nhi_code(nhi_code)
        
        if result:
            self._cache.set(cache_key, result, ttl=self.CACHE_TTL)
        
        return result
    
    async def search_by_drug_name(
        self,
        drug_name: str,
        limit: int = 20
    ) -> list[dict]:
        """
        Search NHI coverage by drug name.
        
        Args:
            drug_name: Drug name (Chinese or English)
            limit: Maximum number of results
            
        Returns:
            List of NHI coverage records
        """
        # This would typically query a database or API
        # For now, return empty list as placeholder
        return []
    
    async def get_drug_price(
        self,
        nhi_code: str
    ) -> dict | None:
        """
        Get NHI reimbursement price for a drug.
        
        Args:
            nhi_code: NHI drug code
            
        Returns:
            Price information or None
        """
        drug_info = await self.search_by_nhi_code(nhi_code)
        if drug_info:
            return {
                "nhi_code": nhi_code,
                "price": drug_info.get("price"),
                "unit": drug_info.get("unit"),
                "effective_date": drug_info.get("effective_date")
            }
        return None
    
    async def check_coverage(
        self,
        drug_name: str
    ) -> dict:
        """
        Check if a drug is covered by NHI.
        
        Args:
            drug_name: Drug name to check
            
        Returns:
            Coverage status and details
        """
        results = await self.search_by_drug_name(drug_name)
        
        if results:
            return {
                "is_covered": True,
                "drug_name": drug_name,
                "coverage_details": results,
                "note": "此藥品有健保給付"
            }
        else:
            return {
                "is_covered": False,
                "drug_name": drug_name,
                "coverage_details": [],
                "note": "此藥品可能為自費藥品或需查詢更詳細資料"
            }
    
    def _lookup_nhi_code(self, nhi_code: str) -> dict | None:
        """
        Internal lookup for NHI code.
        
        This is a placeholder - in production, this would query
        a proper database or downloaded NHI data.
        """
        # Common NHI codes for reference
        common_drugs = {
            "A022664100": {
                "nhi_code": "A022664100",
                "chinese_name": "可邁丁錠 5毫克",
                "english_name": "COUMADIN TABLETS 5MG",
                "ingredient": "WARFARIN SODIUM",
                "price": 5.50,
                "unit": "錠",
                "manufacturer": "臺灣百乃愛藥品股份有限公司",
                "effective_date": "2024-01-01",
                "notes": "需定期監測INR"
            },
            "BC26aborvsc": {
                "nhi_code": "BC26aborvsc",
                "chinese_name": "立普妥膜衣錠 20毫克",
                "english_name": "LIPITOR F.C. TABLETS 20MG",
                "ingredient": "ATORVASTATIN CALCIUM",
                "price": 18.80,
                "unit": "錠",
                "manufacturer": "輝瑞大藥廠股份有限公司",
                "effective_date": "2024-01-01"
            }
        }
        
        return common_drugs.get(nhi_code.upper())
    
    async def get_prior_authorization_drugs(self) -> list[dict]:
        """
        Get list of drugs requiring prior authorization (事前審查).
        
        Returns:
            List of drugs requiring prior authorization
        """
        # Placeholder - would fetch from NHI database
        return [
            {
                "category": "癌症標靶藥物",
                "examples": ["Iressa", "Tarceva", "Herceptin"],
                "note": "需檢附相關檢驗報告"
            },
            {
                "category": "生物製劑",
                "examples": ["Humira", "Enbrel", "Remicade"],
                "note": "需符合特定適應症條件"
            },
            {
                "category": "罕見疾病用藥",
                "examples": ["Fabrazyme", "Cerezyme"],
                "note": "需經專案審查"
            }
        ]


# 常見健保給付規定 (擴充版)
NHI_COVERAGE_RULES: dict[str, dict[str, Any]] = {
    # ========== 抗凝血/抗血小板藥物 ==========
    "warfarin": {
        "drug_name": "Warfarin (可邁丁)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "心房顫動",
            "深部靜脈栓塞",
            "肺栓塞",
            "機械瓣膜置換術後"
        ],
        "restrictions": "需定期監測INR",
        "prior_authorization": False,
        "nhi_codes": ["A022664100", "A0226641G0"]
    },
    "clopidogrel": {
        "drug_name": "Clopidogrel (保栓通/Plavix)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "急性冠心症候群",
            "經皮冠狀動脈介入術後"
        ],
        "restrictions": "1. ACS使用不超過12個月\n2. PCI術後依支架類型限制使用期間",
        "prior_authorization": False,
        "nhi_codes": ["BC22391100", "BC223911G0"]
    },
    "aspirin": {
        "drug_name": "Aspirin (阿斯匹靈)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "解熱鎮痛",
            "心血管疾病預防",
            "急性冠心症候群"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["A003092100", "N004949100"]
    },
    "dabigatran": {
        "drug_name": "Dabigatran (普栓達/Pradaxa)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "非瓣膜性心房顫動"
        ],
        "restrictions": "1. CHA2DS2-VASc ≥ 2 (男) 或 ≥ 3 (女)\n2. 不適合使用warfarin者",
        "prior_authorization": False,
        "nhi_codes": ["BC25908100", "BC25909100"]
    },
    "rivaroxaban": {
        "drug_name": "Rivaroxaban (拜瑞妥/Xarelto)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "非瓣膜性心房顫動",
            "深部靜脈栓塞治療與預防",
            "肺栓塞治療"
        ],
        "restrictions": "需符合CHA2DS2-VASc評分條件",
        "prior_authorization": False,
        "nhi_codes": ["BC26148100", "BC26149100"]
    },
    "apixaban": {
        "drug_name": "Apixaban (艾乐妥/Eliquis)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "非瓣膜性心房顫動"
        ],
        "restrictions": "需符合CHA2DS2-VASc評分條件",
        "prior_authorization": False,
        "nhi_codes": ["BC26454100", "BC26455100"]
    },
    "edoxaban": {
        "drug_name": "Edoxaban (里先安/Lixiana)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "非瓣膜性心房顫動",
            "深部靜脈栓塞"
        ],
        "restrictions": "需符合CHA2DS2-VASc評分條件",
        "prior_authorization": False,
        "nhi_codes": ["BC26793100", "BC26794100"]
    },
    "ticagrelor": {
        "drug_name": "Ticagrelor (百無凝/Brilinta)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "急性冠心症候群"
        ],
        "restrictions": "ACS使用不超過12個月",
        "prior_authorization": False,
        "nhi_codes": ["BC26036100"]
    },
    
    # ========== 降血脂藥物 ==========
    "atorvastatin": {
        "drug_name": "Atorvastatin (立普妥/Lipitor)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高膽固醇血症",
            "混合性高脂血症",
            "心血管疾病預防"
        ],
        "restrictions": "需有血脂檢驗報告 (TC>200 或 LDL>130)",
        "prior_authorization": False,
        "nhi_codes": ["BC22571100", "BC22572100"]
    },
    "rosuvastatin": {
        "drug_name": "Rosuvastatin (冠脂妥/Crestor)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高膽固醇血症",
            "混合性高脂血症"
        ],
        "restrictions": "需有血脂檢驗報告",
        "prior_authorization": False,
        "nhi_codes": ["BC24591100", "BC24592100"]
    },
    "simvastatin": {
        "drug_name": "Simvastatin (素果/Zocor)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高膽固醇血症"
        ],
        "restrictions": "需有血脂檢驗報告",
        "prior_authorization": False,
        "nhi_codes": ["BC21908100"]
    },
    "ezetimibe": {
        "drug_name": "Ezetimibe (怡妥/Ezetrol)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "高膽固醇血症"
        ],
        "restrictions": "需 statin 類藥物無法達標或不耐受",
        "prior_authorization": False,
        "nhi_codes": ["BC24100100"]
    },
    "fenofibrate": {
        "drug_name": "Fenofibrate (弗尼利脂寧/Lipanthyl)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高三酸甘油酯血症",
            "混合性高脂血症"
        ],
        "restrictions": "TG > 200 mg/dL",
        "prior_authorization": False,
        "nhi_codes": ["BC21287100"]
    },
    
    # ========== 降血糖藥物 ==========
    "metformin": {
        "drug_name": "Metformin (庫魯化/Glucophage)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "第2型糖尿病"
        ],
        "restrictions": "eGFR < 30 禁用，30-45 需減量",
        "prior_authorization": False,
        "nhi_codes": ["A020444100", "A020445100"]
    },
    "glimepiride": {
        "drug_name": "Glimepiride (瑪爾胰/Amaryl)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "第2型糖尿病"
        ],
        "restrictions": "注意低血糖風險",
        "prior_authorization": False,
        "nhi_codes": ["BC22018100", "BC22019100"]
    },
    "sitagliptin": {
        "drug_name": "Sitagliptin (佳糖維/Januvia)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第2型糖尿病"
        ],
        "restrictions": "需併用metformin或SU類",
        "prior_authorization": False,
        "nhi_codes": ["BC25257100", "BC25258100"]
    },
    "linagliptin": {
        "drug_name": "Linagliptin (糖漸平/Trajenta)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第2型糖尿病"
        ],
        "restrictions": "腎功能不全可使用，不需調整劑量",
        "prior_authorization": False,
        "nhi_codes": ["BC25935100"]
    },
    "empagliflozin": {
        "drug_name": "Empagliflozin (恩排糖/Jardiance)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第2型糖尿病",
            "心衰竭"
        ],
        "restrictions": "需併用metformin或有心血管疾病",
        "prior_authorization": False,
        "nhi_codes": ["BC26607100", "BC26608100"]
    },
    "dapagliflozin": {
        "drug_name": "Dapagliflozin (福適佳/Forxiga)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第2型糖尿病",
            "心衰竭",
            "慢性腎臟病"
        ],
        "restrictions": "心衰竭適應症需EF≤40%",
        "prior_authorization": False,
        "nhi_codes": ["BC26279100"]
    },
    "liraglutide": {
        "drug_name": "Liraglutide (胰妥善/Victoza)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第2型糖尿病"
        ],
        "restrictions": "BMI ≥ 27，需併用其他口服藥",
        "prior_authorization": False,
        "nhi_codes": ["BC25679235"]
    },
    "insulin_glargine": {
        "drug_name": "Insulin Glargine (蘭德仕/Lantus)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "第1型糖尿病",
            "第2型糖尿病"
        ],
        "restrictions": "第2型需口服藥控制不良 (HbA1c > 8.5%)",
        "prior_authorization": False,
        "nhi_codes": ["BC24113221"]
    },
    
    # ========== 降血壓藥物 ==========
    "amlodipine": {
        "drug_name": "Amlodipine (脈優/Norvasc)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "心絞痛"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC21430100", "BC21431100"]
    },
    "valsartan": {
        "drug_name": "Valsartan (得安穩/Diovan)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "心衰竭",
            "心肌梗塞後"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC22123100", "BC22124100"]
    },
    "losartan": {
        "drug_name": "Losartan (可悅您/Cozaar)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "糖尿病腎病變"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC21589100", "BC21590100"]
    },
    "lisinopril": {
        "drug_name": "Lisinopril (捷賜瑞/Zestril)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "心衰竭"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC20730100"]
    },
    "bisoprolol": {
        "drug_name": "Bisoprolol (康肯/Concor)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "心衰竭",
            "心律不整"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC21100100"]
    },
    "carvedilol": {
        "drug_name": "Carvedilol (達利全/Dilatrend)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "高血壓",
            "心衰竭"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC21772100", "BC21773100"]
    },
    
    # ========== 質子幫浦抑制劑 ==========
    "omeprazole": {
        "drug_name": "Omeprazole (耐適恩/Losec)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "消化性潰瘍",
            "胃食道逆流",
            "Zollinger-Ellison症候群"
        ],
        "restrictions": "需有內視鏡檢查報告，最長使用16週",
        "prior_authorization": False,
        "nhi_codes": ["BC21153100", "BC21154100"]
    },
    "esomeprazole": {
        "drug_name": "Esomeprazole (耐適恩/Nexium)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "消化性潰瘍",
            "胃食道逆流"
        ],
        "restrictions": "需有內視鏡檢查報告",
        "prior_authorization": False,
        "nhi_codes": ["BC23905100", "BC23906100"]
    },
    "pantoprazole": {
        "drug_name": "Pantoprazole (保衛康/Pantoloc)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "消化性潰瘍",
            "胃食道逆流"
        ],
        "restrictions": "需有內視鏡檢查報告",
        "prior_authorization": False,
        "nhi_codes": ["BC21987100"]
    },
    
    # ========== 抗生素 ==========
    "amoxicillin": {
        "drug_name": "Amoxicillin (安莫西林)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "呼吸道感染",
            "泌尿道感染",
            "幽門桿菌除菌"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["A005813100", "A005814100"]
    },
    "azithromycin": {
        "drug_name": "Azithromycin (日舒/Zithromax)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "呼吸道感染",
            "皮膚軟組織感染"
        ],
        "restrictions": "限其他抗生素無效或不適用時",
        "prior_authorization": False,
        "nhi_codes": ["BC21550100"]
    },
    "levofloxacin": {
        "drug_name": "Levofloxacin (可樂必妥/Cravit)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "呼吸道感染",
            "泌尿道感染"
        ],
        "restrictions": "限其他抗生素無效或培養證實",
        "prior_authorization": False,
        "nhi_codes": ["BC22179100"]
    },
    
    # ========== 神經/精神科用藥 ==========
    "gabapentin": {
        "drug_name": "Gabapentin (鎮頑癲/Neurontin)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "癲癇",
            "帶狀皰疹後神經痛"
        ],
        "restrictions": "神經痛需為帶狀皰疹後神經痛",
        "prior_authorization": False,
        "nhi_codes": ["BC21368100", "BC21369100"]
    },
    "pregabalin": {
        "drug_name": "Pregabalin (利瑞卡/Lyrica)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "帶狀皰疹後神經痛",
            "糖尿病周邊神經痛",
            "纖維肌痛症"
        ],
        "restrictions": "需有明確診斷，纖維肌痛需事前審查",
        "prior_authorization": False,
        "nhi_codes": ["BC25040100", "BC25041100"]
    },
    "sertraline": {
        "drug_name": "Sertraline (樂復得/Zoloft)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "憂鬱症",
            "恐慌症",
            "強迫症"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC21434100"]
    },
    "escitalopram": {
        "drug_name": "Escitalopram (立普能/Lexapro)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "憂鬱症",
            "焦慮症"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC24225100", "BC24226100"]
    },
    "quetiapine": {
        "drug_name": "Quetiapine (思樂康/Seroquel)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "思覺失調症",
            "雙極性疾患"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC22225100", "BC22226100"]
    },
    
    # ========== 止痛藥 ==========
    "acetaminophen": {
        "drug_name": "Acetaminophen (普拿疼)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "解熱",
            "鎮痛"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["N004942100"]
    },
    "tramadol": {
        "drug_name": "Tramadol (及通安/Tramal)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "中度至重度疼痛"
        ],
        "restrictions": "屬第四級管制藥品",
        "prior_authorization": False,
        "nhi_codes": ["BC21179100"]
    },
    "celecoxib": {
        "drug_name": "Celecoxib (希樂葆/Celebrex)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "骨關節炎",
            "類風濕性關節炎"
        ],
        "restrictions": "需有消化道出血高風險因子",
        "prior_authorization": False,
        "nhi_codes": ["BC22515100", "BC22516100"]
    },
    
    # ========== 生物製劑/標靶藥物 (事前審查) ==========
    "trastuzumab": {
        "drug_name": "Trastuzumab (賀癌平/Herceptin)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "HER2陽性乳癌",
            "HER2陽性胃癌"
        ],
        "restrictions": "需檢附HER2檢測報告 (IHC 3+ 或 FISH陽性)",
        "prior_authorization": True,
        "nhi_codes": ["KC00785209"]
    },
    "bevacizumab": {
        "drug_name": "Bevacizumab (癌思停/Avastin)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "轉移性大腸直腸癌",
            "非小細胞肺癌"
        ],
        "restrictions": "需符合各癌別給付規定",
        "prior_authorization": True,
        "nhi_codes": ["KC00808209"]
    },
    "rituximab": {
        "drug_name": "Rituximab (莫須瘤/MabThera)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "非乎杰金氏淋巴瘤",
            "慢性淋巴性白血病",
            "類風濕性關節炎"
        ],
        "restrictions": "需符合各適應症給付規定",
        "prior_authorization": True,
        "nhi_codes": ["KC00757209"]
    },
    "adalimumab": {
        "drug_name": "Adalimumab (復邁/Humira)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "類風濕性關節炎",
            "乾癬",
            "克隆氏症",
            "僵直性脊椎炎"
        ],
        "restrictions": "需傳統治療無效 (如MTX, DMARD) 且符合特定條件",
        "prior_authorization": True,
        "nhi_codes": ["KC00817221"]
    },
    "etanercept": {
        "drug_name": "Etanercept (恩博/Enbrel)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "類風濕性關節炎",
            "乾癬性關節炎",
            "僵直性脊椎炎"
        ],
        "restrictions": "需傳統治療無效且符合特定條件",
        "prior_authorization": True,
        "nhi_codes": ["KC00763209"]
    },
    "secukinumab": {
        "drug_name": "Secukinumab (可善挺/Cosentyx)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "中重度乾癬",
            "乾癬性關節炎"
        ],
        "restrictions": "PASI > 10，BSA > 10%，傳統治療無效",
        "prior_authorization": True,
        "nhi_codes": ["KC00872221"]
    },
    
    # ========== 抗癌標靶藥物 ==========
    "imatinib": {
        "drug_name": "Imatinib (基利克/Glivec)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "慢性骨髓性白血病",
            "胃腸道乢質瘤"
        ],
        "restrictions": "CML需有Philadelphia染色體陽性",
        "prior_authorization": True,
        "nhi_codes": ["BC23457100"]
    },
    "gefitinib": {
        "drug_name": "Gefitinib (艾瑞莎/Iressa)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "EGFR突變陽性非小細胞肺癌"
        ],
        "restrictions": "需有EGFR基因檢測陽性報告",
        "prior_authorization": True,
        "nhi_codes": ["BC24039100"]
    },
    "erlotinib": {
        "drug_name": "Erlotinib (得舒緩/Tarceva)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "EGFR突變陽性非小細胞肺癌"
        ],
        "restrictions": "需有EGFR基因檢測陽性報告",
        "prior_authorization": True,
        "nhi_codes": ["BC24589100", "BC24590100"]
    },
    "osimertinib": {
        "drug_name": "Osimertinib (泰格莎/Tagrisso)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "T790M陽性非小細胞肺癌",
            "EGFR突變陽性非小細胞肺癌一線治療"
        ],
        "restrictions": "需有T790M或EGFR突變檢測報告",
        "prior_authorization": True,
        "nhi_codes": ["BC26962100"]
    },
    "pembrolizumab": {
        "drug_name": "Pembrolizumab (吉舒達/Keytruda)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "黑色素瘤",
            "非小細胞肺癌",
            "典型乎杰金氏淋巴瘤"
        ],
        "restrictions": "需符合各癌別給付規定及PD-L1檢測",
        "prior_authorization": True,
        "nhi_codes": ["KC00873209"]
    },
    "nivolumab": {
        "drug_name": "Nivolumab (保疾伏/Opdivo)",
        "is_covered": True,
        "coverage_type": "事前審查",
        "indications": [
            "黑色素瘤",
            "非小細胞肺癌",
            "腎細胞癌"
        ],
        "restrictions": "需符合各癌別給付規定",
        "prior_authorization": True,
        "nhi_codes": ["KC00859209"]
    },
    
    # ========== 其他常用藥物 ==========
    "montelukast": {
        "drug_name": "Montelukast (欣流/Singulair)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "氣喘",
            "過敏性鼻炎"
        ],
        "restrictions": "氣喘需為中重度，鼻炎需有過敏檢測",
        "prior_authorization": False,
        "nhi_codes": ["BC22237100", "BC22238100"]
    },
    "levothyroxine": {
        "drug_name": "Levothyroxine (昂特欣/Eltroxin)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "甲狀腺功能低下"
        ],
        "restrictions": "無",
        "prior_authorization": False,
        "nhi_codes": ["BC09714100", "BC09715100"]
    },
    "allopurinol": {
        "drug_name": "Allopurinol (乙乙錠)",
        "is_covered": True,
        "coverage_type": "一般給付",
        "indications": [
            "痛風",
            "高尿酸血症"
        ],
        "restrictions": "尿酸 > 9.0 mg/dL 或有痛風發作史",
        "prior_authorization": False,
        "nhi_codes": ["A008464100"]
    },
    "febuxostat": {
        "drug_name": "Febuxostat (福避痛/Feburic)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "痛風",
            "高尿酸血症"
        ],
        "restrictions": "限allopurinol無效或禁忌症者",
        "prior_authorization": False,
        "nhi_codes": ["BC25678100"]
    },
    "sildenafil": {
        "drug_name": "Sildenafil (威而鋼/Viagra, 瑞肺得/Revatio)",
        "is_covered": True,
        "coverage_type": "限特定條件給付",
        "indications": [
            "肺動脈高壓"
        ],
        "restrictions": "勃起功能障礙非健保給付適應症",
        "prior_authorization": False,
        "nhi_codes": ["BC25104100"]
    },
}


def get_nhi_coverage_info(drug_name: str) -> dict | None:
    """
    Get NHI coverage information for a drug.
    
    Args:
        drug_name: Drug name (generic or brand)
        
    Returns:
        Coverage information or None
    """
    drug_lower = drug_name.lower().strip()
    
    # Direct lookup
    if drug_lower in NHI_COVERAGE_RULES:
        return NHI_COVERAGE_RULES[drug_lower]
    
    # Search in drug names
    for key, info in NHI_COVERAGE_RULES.items():
        if drug_lower in info["drug_name"].lower():
            return info
    
    return None
