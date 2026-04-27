"""Kiwoom condition search manager with realtime monitoring support."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from brokers.kiwoom.realtime import ScreenManager


def _validate_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ConditionDefinition:
    """Condition metadata loaded from Kiwoom server."""

    index: int
    name: str


class ConditionSearchManager:
    """Manage Kiwoom condition load/query/realtime lifecycle."""

    MAX_REALTIME_CONDITIONS = 10

    def __init__(
        self,
        ocx: Any,
        screen_manager: Optional[ScreenManager] = None,
        watchlist_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        signal_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        ticker_suffix_resolver: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self._ocx = ocx
        self._screen_manager = screen_manager or ScreenManager(start=3000, end=3999)
        self._watchlist_sink = watchlist_sink
        self._signal_sink = signal_sink
        self._ticker_suffix_resolver = ticker_suffix_resolver

        self._condition_loaded_event = threading.Event()
        self._condition_load_result = 0

        self._active: Dict[Tuple[int, str], str] = {}
        self._tracked_codes: Dict[Tuple[int, str], Set[str]] = {}
        self._observers: List[Callable[[Dict[str, Any]], None]] = []

        self._bind_events()

    @property
    def active_conditions(self) -> Dict[Tuple[int, str], str]:
        return dict(self._active)

    def add_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(callback)

    def remove_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def load_conditions(self, timeout: float = 5.0) -> bool:
        """Load condition catalog by calling GetConditionLoad."""
        self._condition_loaded_event.clear()
        self._condition_load_result = 0
        ret = self._ocx.dynamicCall("GetConditionLoad()")
        if int(ret) != 1:
            return False
        if not self._condition_loaded_event.wait(timeout=timeout):
            return False
        return self._condition_load_result == 1

    def get_condition_list(self) -> List[ConditionDefinition]:
        """Return parsed condition list from GetConditionNameList payload."""
        raw = self._ocx.dynamicCall("GetConditionNameList()")
        text = raw.strip() if isinstance(raw, str) else str(raw).strip()
        if not text:
            return []

        out: List[ConditionDefinition] = []
        for token in text.split(";"):
            token = token.strip()
            if not token:
                continue
            if "^" not in token:
                continue
            idx_text, name = token.split("^", 1)
            try:
                index = int(idx_text)
            except ValueError:
                continue
            if not name.strip():
                continue
            out.append(ConditionDefinition(index=index, name=name.strip()))
        return out

    def start_monitoring(self, condition_name: str, condition_index: int) -> str:
        """Start realtime monitoring for a condition and return screen number."""
        condition_name = _validate_non_empty(condition_name, "condition_name")
        if not isinstance(condition_index, int) or condition_index < 0:
            raise ValueError("condition_index must be a non-negative int")

        key = (condition_index, condition_name)
        if key in self._active:
            return self._active[key]

        if len(self._active) >= self.MAX_REALTIME_CONDITIONS:
            raise RuntimeError("maximum realtime condition limit reached (10)")

        screen_no = self._screen_manager.allocate()
        ret = self._ocx.dynamicCall(
            "SendCondition(QString, QString, int, int)",
            screen_no,
            condition_name,
            int(condition_index),
            1,
        )
        if int(ret) != 1:
            self._screen_manager.release(screen_no)
            raise RuntimeError(f"SendCondition failed: {ret}")

        self._active[key] = screen_no
        self._tracked_codes[key] = set()
        return screen_no

    def stop_monitoring(self, condition_name: str, condition_index: int) -> bool:
        """Stop realtime condition monitoring and release screen."""
        condition_name = _validate_non_empty(condition_name, "condition_name")
        if not isinstance(condition_index, int) or condition_index < 0:
            raise ValueError("condition_index must be a non-negative int")
        key = (condition_index, condition_name)
        screen_no = self._active.get(key)
        if screen_no is None:
            return False

        ret = self._ocx.dynamicCall(
            "SendConditionStop(QString, QString, int)",
            screen_no,
            condition_name,
            int(condition_index),
        )
        if int(ret) != 1:
            return False

        self._active.pop(key, None)
        self._tracked_codes.pop(key, None)
        self._screen_manager.release(screen_no)
        return True

    def _bind_events(self) -> None:
        if hasattr(self._ocx, "OnReceiveConditionVer") and hasattr(self._ocx.OnReceiveConditionVer, "connect"):
            self._ocx.OnReceiveConditionVer.connect(self.on_receive_condition_ver)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveConditionVer"] = self.on_receive_condition_ver

        if hasattr(self._ocx, "OnReceiveTrCondition") and hasattr(self._ocx.OnReceiveTrCondition, "connect"):
            self._ocx.OnReceiveTrCondition.connect(self.on_receive_tr_condition)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveTrCondition"] = self.on_receive_tr_condition

        if hasattr(self._ocx, "OnReceiveRealCondition") and hasattr(self._ocx.OnReceiveRealCondition, "connect"):
            self._ocx.OnReceiveRealCondition.connect(self.on_receive_real_condition)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveRealCondition"] = self.on_receive_real_condition

    def on_receive_condition_ver(self, ret: int, msg: str) -> None:
        self._condition_load_result = int(ret)
        payload = {
            "type": "condition_ver",
            "success": int(ret) == 1,
            "message": msg or "",
        }
        self._notify(payload)
        self._condition_loaded_event.set()

    def on_receive_tr_condition(
        self,
        screen_no: str,
        code_list: str,
        condition_name: str,
        condition_index: int,
        prev_next: int,
    ) -> None:
        _ = prev_next
        try:
            idx = int(condition_index)
        except (TypeError, ValueError):
            return

        key = (idx, str(condition_name))
        codes = self._parse_code_list(code_list)
        self._tracked_codes[key] = set(codes)
        payload = {
            "type": "tr_condition",
            "screen_no": str(screen_no),
            "condition_name": str(condition_name),
            "condition_index": idx,
            "codes": codes,
        }
        self._notify(payload)
        for code in codes:
            self._emit_discovery(action="watch", condition_name=condition_name, condition_index=idx, code=code)

    def on_receive_real_condition(self, code: str, event_type: str, condition_name: str, condition_index: str) -> None:
        norm_code = str(code).strip()
        if not norm_code:
            return
        try:
            idx = int(condition_index)
        except (TypeError, ValueError):
            return
        key = (idx, str(condition_name))
        tracked = self._tracked_codes.setdefault(key, set())

        action = str(event_type).strip().upper()
        if action == "I":
            tracked.add(norm_code)
            action_name = "IN"
            discovery_action = "watch"
        elif action == "D":
            tracked.discard(norm_code)
            action_name = "OUT"
            discovery_action = "unwatch"
        else:
            action_name = action or "UNKNOWN"
            discovery_action = "signal"

        payload = {
            "type": "real_condition",
            "code": norm_code,
            "event_type": action_name,
            "condition_name": str(condition_name),
            "condition_index": idx,
        }
        self._notify(payload)
        self._emit_discovery(
            action=discovery_action,
            condition_name=str(condition_name),
            condition_index=idx,
            code=norm_code,
        )

    @staticmethod
    def _parse_code_list(code_list: str) -> List[str]:
        text = code_list.strip() if isinstance(code_list, str) else str(code_list).strip()
        if not text:
            return []
        out: List[str] = []
        for token in text.split(";"):
            code = token.strip()
            if code:
                out.append(code)
        return out

    def _emit_discovery(self, action: str, condition_name: str, condition_index: int, code: str) -> None:
        ticker = self._to_ticker(code)
        payload = {
            "source": "kiwoom_condition",
            "action": action,
            "condition_name": condition_name,
            "condition_index": int(condition_index),
            "code": code,
            "ticker": ticker,
        }
        if self._watchlist_sink is not None:
            self._watchlist_sink(payload)
        if self._signal_sink is not None:
            self._signal_sink(payload)

    def _to_ticker(self, code: str) -> str:
        suffix = "KS"
        if self._ticker_suffix_resolver is not None:
            try:
                resolved = self._ticker_suffix_resolver(code)
            except Exception:
                resolved = None
            if resolved:
                text = str(resolved).strip().upper().lstrip(".")
                if text in {"KS", "KQ"}:
                    suffix = text
        return f"{code}.{suffix}"

    def _notify(self, payload: Dict[str, Any]) -> None:
        for callback in list(self._observers):
            try:
                callback(payload)
            except Exception:
                continue
