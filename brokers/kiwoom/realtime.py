"""Kiwoom real-time subscription helpers.

Includes screen number allocation and SetRealReg/SetRealRemove wrappers.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set


class ScreenManager:
    """Manage 4-digit Kiwoom screen numbers."""

    def __init__(self, start: int = 1000, end: int = 1999) -> None:
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            raise ValueError("invalid screen range")
        if start < 0 or end > 9999:
            raise ValueError("screen range must be within 0000-9999")

        self._start = start
        self._end = end
        self._cursor = start
        self._released: List[int] = []
        self._in_use: Set[int] = set()

    def allocate(self) -> str:
        """Allocate a screen number, reusing released numbers first."""
        if self._released:
            number = self._released.pop(0)
            self._in_use.add(number)
            return f"{number:04d}"

        if self._cursor > self._end:
            raise RuntimeError("no available screen numbers")

        number = self._cursor
        self._cursor += 1
        self._in_use.add(number)
        return f"{number:04d}"

    def release(self, screen_no: str) -> None:
        """Release a previously allocated screen number."""
        if not isinstance(screen_no, str) or len(screen_no) != 4 or not screen_no.isdigit():
            raise ValueError("screen_no must be a 4-digit string")
        number = int(screen_no)
        if number in self._in_use:
            self._in_use.remove(number)
            self._released.append(number)


class RealtimeSubscriptionManager:
    """Manage Kiwoom real-time subscriptions by stock code."""

    def __init__(self, ocx: Any, screen_manager: ScreenManager | None = None) -> None:
        self._ocx = ocx
        self._screen_manager = screen_manager or ScreenManager()
        self._code_to_screen: Dict[str, str] = {}

    @property
    def tracked_codes(self) -> Set[str]:
        """Return currently tracked codes."""
        return set(self._code_to_screen.keys())

    @staticmethod
    def _normalize_fids(fid_list: Iterable[int]) -> str:
        values: List[int] = []
        for fid in fid_list:
            try:
                values.append(int(fid))
            except (TypeError, ValueError) as exc:
                raise ValueError("fid_list must contain integer values") from exc
        if not values:
            raise ValueError("fid_list must not be empty")
        uniq_sorted = sorted(set(values))
        return ",".join(str(fid) for fid in uniq_sorted)

    def register(self, code: str, fid_list: Iterable[int], real_type: str = "1") -> str:
        """Register real-time subscription for a stock code."""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be a non-empty string")

        norm_code = code.strip()
        fid_csv = self._normalize_fids(fid_list)

        screen_no = self._code_to_screen.get(norm_code)
        if screen_no is None:
            screen_no = self._screen_manager.allocate()
            self._code_to_screen[norm_code] = screen_no

        self._ocx.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            screen_no,
            norm_code,
            fid_csv,
            str(real_type),
        )
        return screen_no

    def unregister(self, code: str) -> None:
        """Unregister real-time subscription for a stock code."""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be a non-empty string")

        norm_code = code.strip()
        screen_no = self._code_to_screen.pop(norm_code, None)
        if screen_no is None:
            return

        self._ocx.dynamicCall("SetRealRemove(QString, QString)", screen_no, norm_code)
        self._screen_manager.release(screen_no)

    def clear(self) -> None:
        """Unregister all tracked subscriptions."""
        for code in list(self._code_to_screen.keys()):
            self.unregister(code)
