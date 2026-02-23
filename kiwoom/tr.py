"""Kiwoom TR request helpers.

Provides a thin, testable wrapper over OCX TR-related dynamicCall APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _validate_screen_no(screen_no: str) -> str:
    """Validate that screen number is a 4-digit string."""
    if not isinstance(screen_no, str) or len(screen_no) != 4 or not screen_no.isdigit():
        raise ValueError("screen_no must be a 4-digit string")
    return screen_no


def _validate_non_empty(value: str, field_name: str) -> str:
    """Validate non-empty string inputs used for TR requests."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class TrRequest:
    """Metadata describing a Kiwoom TR request."""

    rq_name: str
    tr_code: str
    prev_next: int
    screen_no: str

    def __post_init__(self) -> None:
        rq_name = _validate_non_empty(self.rq_name, "rq_name")
        tr_code = _validate_non_empty(self.tr_code, "tr_code")
        if not isinstance(self.prev_next, int):
            raise ValueError("prev_next must be an int")
        screen_no = _validate_screen_no(self.screen_no)
        object.__setattr__(self, "rq_name", rq_name)
        object.__setattr__(self, "tr_code", tr_code)
        object.__setattr__(self, "screen_no", screen_no)


class KiwoomTrClient:
    """Thin wrapper over Kiwoom OCX TR request APIs."""

    def __init__(self, ocx: Any) -> None:
        self._ocx = ocx

    def set_input_value(self, key: str, value: str) -> None:
        """Set input value used by subsequent TR request."""
        key = _validate_non_empty(key, "key")
        if value is None:
            raise ValueError("value must not be None")
        self._ocx.dynamicCall("SetInputValue(QString, QString)", key, str(value))

    def comm_rq_data(self, request: TrRequest) -> int:
        """Send TR request and return Kiwoom return code."""
        ret = self._ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            request.rq_name,
            request.tr_code,
            request.prev_next,
            request.screen_no,
        )
        return int(ret)

    def get_comm_data(self, tr_code: str, record_name: str, index: int, item_name: str) -> str:
        """Read string data from a TR response payload."""
        tr_code = _validate_non_empty(tr_code, "tr_code")
        record_name = _validate_non_empty(record_name, "record_name")
        item_name = _validate_non_empty(item_name, "item_name")
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative int")

        result = self._ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code,
            record_name,
            index,
            item_name,
        )
        return result.strip() if isinstance(result, str) else str(result).strip()

    def get_repeat_cnt(self, tr_code: str, record_name: str) -> int:
        """Return repeat row count for a TR response record."""
        tr_code = _validate_non_empty(tr_code, "tr_code")
        record_name = _validate_non_empty(record_name, "record_name")
        ret = self._ocx.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, record_name)
        return int(ret)
