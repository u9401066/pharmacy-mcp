"""院內藥品檔知識庫"""

import json
from pathlib import Path
from typing import Optional

from pharmacy_mcp.domain.value_objects.order_result import FormularyItem


class FormularyKnowledge:
    """院內藥品檔知識庫

    從 JSON 檔案載入院內藥品資料，提供查詢功能。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """初始化藥品檔

        Args:
            data_path: JSON 資料檔路徑，預設為 data/formulary.json
        """
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "formulary.json"

        self._items: dict[str, FormularyItem] = {}
        self._load_data(data_path)

    def _load_data(self, data_path: Path) -> None:
        """載入 JSON 資料"""
        if not data_path.exists():
            raise FileNotFoundError(f"Formulary data file not found: {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item_data in data.get("items", []):
            item = FormularyItem(
                drug_code=item_data["drug_code"],
                drug_name=item_data["drug_name"],
                generic_name=item_data["generic_name"],
                strength=item_data["strength"],
                unit=item_data["unit"],
                dosage_form=item_data["dosage_form"],
                available_routes=tuple(item_data["available_routes"]),
                min_dose=item_data["min_dose"],
                max_dose=item_data["max_dose"],
                default_frequency=item_data["default_frequency"],
                nhi_code=item_data.get("nhi_code"),
                atc_code=item_data.get("atc_code"),
                requires_renal_adjustment=item_data.get(
                    "requires_renal_adjustment", False
                ),
                high_alert=item_data.get("high_alert", False),
            )
            self._items[item.drug_code] = item

    def get_item(self, drug_code: str) -> Optional[FormularyItem]:
        """取得藥品項目

        Args:
            drug_code: 藥品代碼

        Returns:
            FormularyItem 或 None
        """
        return self._items.get(drug_code)

    def search(self, query: str, limit: int = 10) -> list[FormularyItem]:
        """搜尋藥品

        Args:
            query: 搜尋字串（藥品代碼、名稱、學名）
            limit: 最大回傳數量

        Returns:
            符合條件的藥品列表
        """
        query_lower = query.lower()
        results = []

        for item in self._items.values():
            if (
                query_lower in item.drug_code.lower()
                or query_lower in item.drug_name.lower()
                or query_lower in item.generic_name.lower()
            ):
                results.append(item)
                if len(results) >= limit:
                    break

        return results

    def list_high_alert_drugs(self) -> list[FormularyItem]:
        """列出高警訊藥品"""
        return [item for item in self._items.values() if item.high_alert]

    def list_renal_adjustment_drugs(self) -> list[FormularyItem]:
        """列出需腎功能調整的藥品"""
        return [item for item in self._items.values() if item.requires_renal_adjustment]

    @property
    def all_items(self) -> list[FormularyItem]:
        """取得所有藥品"""
        return list(self._items.values())

    @property
    def count(self) -> int:
        """藥品數量"""
        return len(self._items)
