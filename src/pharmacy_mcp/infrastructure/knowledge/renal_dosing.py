"""腎功能劑量調整知識庫"""

import json
from pathlib import Path
from typing import Optional

from pharmacy_mcp.domain.value_objects.order_result import RenalAdjustment


class RenalDosingKnowledge:
    """腎功能劑量調整知識庫

    從 JSON 檔案載入腎功能調整規則，提供查詢功能。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """初始化知識庫

        Args:
            data_path: JSON 資料檔路徑，預設為 data/renal_adjustments.json
        """
        if data_path is None:
            data_path = (
                Path(__file__).parent.parent.parent / "data" / "renal_adjustments.json"
            )

        self._adjustments: dict[str, dict] = {}
        self._load_data(data_path)

    def _load_data(self, data_path: Path) -> None:
        """載入 JSON 資料"""
        if not data_path.exists():
            raise FileNotFoundError(
                f"Renal adjustments data file not found: {data_path}"
            )

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._adjustments = data.get("adjustments", {})

    def get_adjustment(self, drug_code: str, crcl: float) -> RenalAdjustment:
        """取得腎功能劑量調整建議

        Args:
            drug_code: 藥品代碼
            crcl: 肌酸酐清除率 (mL/min)

        Returns:
            RenalAdjustment 值物件
        """
        # 檢查是否有此藥品的調整規則
        if drug_code not in self._adjustments:
            return RenalAdjustment(
                drug_code=drug_code,
                crcl_range="N/A",
                needs_adjustment=False,
                recommendation="此藥品無腎功能調整資料",
            )

        drug_data = self._adjustments[drug_code]
        ranges = drug_data.get("ranges", [])

        # 找出適用的 CrCl 範圍
        for range_data in ranges:
            crcl_min = range_data.get("crcl_min", 0)
            crcl_max = range_data.get("crcl_max", 999)

            if crcl_min <= crcl <= crcl_max:
                dose_adj = range_data.get("dose_adjustment", 1.0)
                freq = range_data.get("frequency", "")
                is_contraindicated = range_data.get("contraindicated", False)
                # 判斷是否需要調整：劑量改變 OR 頻率改變 OR 禁忌
                normal_freq = drug_data.get("normal_dose", "").split()[-1] if drug_data.get("normal_dose") else ""
                needs_adj = bool(
                    dose_adj != 1.0 
                    or is_contraindicated
                    or (freq and normal_freq and freq != normal_freq)
                )

                return RenalAdjustment(
                    drug_code=drug_code,
                    crcl_range=f"{crcl_min}-{crcl_max}",
                    needs_adjustment=needs_adj,
                    recommendation=range_data.get("recommendation", ""),
                    suggested_dose=None,  # 由呼叫端根據 dose_adjustment 計算
                    suggested_frequency=range_data.get("frequency"),
                    contraindicated=range_data.get("contraindicated", False),
                )

        # 未找到適用範圍
        return RenalAdjustment(
            drug_code=drug_code,
            crcl_range="未知",
            needs_adjustment=False,
            recommendation=f"CrCl {crcl} 未找到適用的調整規則",
        )

    def get_all_drugs_with_adjustments(self) -> list[str]:
        """取得所有有調整規則的藥品代碼"""
        return list(self._adjustments.keys())

    def get_drug_normal_dose(self, drug_code: str) -> Optional[str]:
        """取得藥品的正常劑量

        Args:
            drug_code: 藥品代碼

        Returns:
            正常劑量字串或 None
        """
        if drug_code in self._adjustments:
            return self._adjustments[drug_code].get("normal_dose")
        return None

    def is_contraindicated(self, drug_code: str, crcl: float) -> bool:
        """檢查是否為禁忌

        Args:
            drug_code: 藥品代碼
            crcl: 肌酸酐清除率 (mL/min)

        Returns:
            是否禁忌使用
        """
        adjustment = self.get_adjustment(drug_code, crcl)
        return adjustment.contraindicated

    @property
    def count(self) -> int:
        """有調整規則的藥品數量"""
        return len(self._adjustments)
