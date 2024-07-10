import re
from typing import List

import tqdm

from justbuild.codediff.git_diff_calculations import CodeDiffs
from justbuild.config import Config


class GreedyModel:
    """Heuristic-based model to revert code sections that are likely to be omitted"""

    def __init__(self, **kwargs):
        self.params = kwargs

    def fit(self, features: List[dict]) -> None:
        pass  # no training required

    def _formula(self, features: dict) -> dict:
        # Per the definition of a code omission, we are looking for 'replaced_previous' changes
        if features.get("change_sequence_type") != "replaced_previous":
            return {"is_code_omission": False, "confidence": 0.95}

        # A common false positive for the LLM model
        if (
            features.get("segment_size") >= features.get("prev_segment_size")
        ) and features.get("segment_size") >= 3:
            return {"is_code_omission": False, "confidence": 0.90}

        # Common predictive features for code omissions
        fcast = (
            features.get("segment_size") == 1
            and features.get("prev_segment_size") > 5
            and (features.get("has_ellipsis") or features.get("has_comment"))
        )
        return {
            "is_code_omission": fcast,
            "confidence": 0.3 + 0.6 * float(fcast),
        }

    def predict(self, features: List[dict]) -> List[dict]:
        return [
            {
                "_id": d["_id"],
                "omitted_code": d["_prev_segment"],
                "replaced_code": d["_curr_segment"],
                **self._formula(d),
            }
            for d in features
        ]
