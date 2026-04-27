"""Kiwoom OpenAPI+ OCX connection, login, and session management.

Provides ``KiwoomConnection`` for real OCX control on Windows and a
transparent mock stub on non-Windows platforms (macOS / Linux) so that
the rest of the codebase can be developed and tested without a live
Kiwoom environment.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from brokers.kiwoom.constants import ErrorCode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"


def _error_description(code: int) -> str:
    """Return a human-readable description for a Kiwoom error code."""
    try:
        return f"{ErrorCode(code).name} ({code})"
    except ValueError:
        return f"Unknown error ({code})"


# ---------------------------------------------------------------------------
# Mock OCX stub (비-Windows 환경용 스텁)
# ---------------------------------------------------------------------------

class _MockOcx:
    """Lightweight stub that mimics the QAxWidget dynamic-call interface.

    Every ``dynamicCall`` invocation returns a sensible default so that
    ``KiwoomConnection`` can run its full login / query flow without a real
    OCX control.  A background thread simulates the *OnEventConnect*
    callback shortly after ``CommConnect()`` is issued.
    """

    # 콜백 함수 저장용
    _callbacks: Dict[str, Any]

    def __init__(self) -> None:
        self._callbacks = {}

    # -- QAxWidget-compatible helpers --

    def dynamicCall(self, func_spec: str, *args: Any) -> Any:  # noqa: N802
        """Route ``dynamicCall`` to the appropriate mock handler."""

        # CommConnect() 호출 시 → 비동기로 OnEventConnect 트리거
        if "CommConnect()" in func_spec:
            self._schedule_event_connect()
            return 0

        # GetLoginInfo(QString) 호출 시 → 태그별 기본값 반환
        if "GetLoginInfo" in func_spec:
            tag: str = args[0] if args else ""
            return self._mock_login_info(tag)

        # 그 외 호출은 빈 문자열 반환
        return ""

    def setControl(self, prog_id: str) -> None:  # noqa: N802
        """Pretend to load an OCX control (no-op on mock)."""
        logger.debug("Mock OCX: setControl('%s') — no-op", prog_id)

    # -- Signal / slot helpers (이벤트 연결) --

    def connect(self, signal: Any, slot: Any) -> None:
        """Register a Python callback for a named signal."""
        # signal은 보통 문자열이 아니라 QAxWidget 시그널이지만,
        # 여기서는 단순히 이름으로 저장한다.
        name = getattr(signal, "__name__", str(signal))
        self._callbacks[name] = slot
        logger.debug("Mock OCX: connected signal '%s'", name)

    # -- Internal helpers (내부 유틸) --

    def _schedule_event_connect(self) -> None:
        """Simulate OnEventConnect firing after a short delay."""

        def _fire() -> None:
            time.sleep(0.1)  # 약간의 지연으로 비동기 콜백 시뮬레이션
            cb = self._callbacks.get("OnEventConnect")
            if cb is not None:
                logger.debug("Mock OCX: firing OnEventConnect(0)")
                cb(0)

        t = threading.Thread(target=_fire, daemon=True)
        t.start()

    @staticmethod
    def _mock_login_info(tag: str) -> str:
        """Return plausible default values for each login-info tag."""
        defaults: Dict[str, str] = {
            "ACCNO": "8012345678;8098765432;",
            "ACCOUNT_CNT": "2",
            "USER_ID": "testuser",
            "USER_NAME": "테스트유저",
            "GetServerGubun": "1",  # 1 = 모의투자
            "KEY_BSECGB": "0",
            "FIREW_SECGB": "0",
        }
        return defaults.get(tag, "")


# ---------------------------------------------------------------------------
# Main connection class (키움 연결 관리 클래스)
# ---------------------------------------------------------------------------

class KiwoomConnection:
    """Manage the lifecycle of a Kiwoom OpenAPI+ OCX session.

    Parameters
    ----------
    mock : bool
        When *True* (or when running on a non-Windows OS), an internal
        ``_MockOcx`` is used instead of the real QAxWidget.  This allows
        development and testing without the Kiwoom HTS environment.

    Examples
    --------
    >>> conn = KiwoomConnection(mock=True)
    >>> conn.login()
    True
    >>> conn.get_account_list()
    ['8012345678', '8098765432']
    """

    _LOGIN_TIMEOUT: int = 60  # 로그인 대기 타임아웃 (초)

    def __init__(
        self,
        mock: bool = False,
        reconnect_attempts: int = 3,
        reconnect_interval: float = 2.0,
        on_disconnect: Optional[Callable[[int], None]] = None,
        on_reconnect_failure: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._mock = mock or (not IS_WINDOWS)
        self._connected: bool = False
        self._login_event = threading.Event()
        self._login_error_code: Optional[int] = None
        self._login_lock = threading.RLock()
        self._reconnect_lock = threading.RLock()
        self._reconnecting: bool = False
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_interval = reconnect_interval
        self._on_disconnect = on_disconnect
        self._on_reconnect_failure = on_reconnect_failure

        # OCX 컨트롤 초기화
        if self._mock:
            logger.info("Initialising KiwoomConnection in MOCK mode")
            self._ocx = _MockOcx()
        else:
            # Windows 전용: PyQt5 QAxWidget으로 실제 OCX 로드
            self._ocx = self._create_real_ocx()

        # OnEventConnect 콜백 연결
        self._bind_events()

    # -- Public API --

    def login(self) -> bool:
        """Initiate login via ``CommConnect`` and block until completion.

        Returns
        -------
        bool
            *True* if the login succeeded, *False* on timeout or error.
        """
        with self._login_lock:
            logger.info("Requesting Kiwoom login …")
            self._login_event.clear()
            self._login_error_code = None

            # CommConnect 호출 (OCX에 로그인 요청)
            ret = self._ocx.dynamicCall("CommConnect()")
            if ret != 0:
                logger.warning(
                    "CommConnect returned %d (%s)", ret, _error_description(ret)
                )
                return False

            # OnEventConnect 콜백 대기 (타임아웃 포함)
            arrived = self._login_event.wait(timeout=self._LOGIN_TIMEOUT)
            if not arrived:
                logger.warning("Login timed out after %ds", self._LOGIN_TIMEOUT)
                return False

            # 에러코드 확인
            if self._login_error_code != 0:
                logger.warning(
                    "Login failed: code=%s (%s)",
                    self._login_error_code,
                    _error_description(self._login_error_code or -1),
                )
                return False

            self._connected = True
            logger.info("Kiwoom login successful")
            return True

    def logout(self) -> None:
        """Tear down the current session."""
        if self._connected:
            logger.info("Logging out of Kiwoom session")
            self._connected = False
        else:
            logger.info("logout() called but no active session")

    def is_connected(self) -> bool:
        """Return whether the session is currently active."""
        return self._connected

    def is_mock_trading(self) -> bool:
        """Return *True* if connected to the mock-trading server.

        키움 모의투자 서버 여부를 반환한다.
        ``GetServerGubun`` 이 ``"1"`` 이면 모의투자 서버.
        """
        return self.get_login_info("GetServerGubun") == "1"

    def get_login_info(self, tag: str) -> str:
        """Retrieve login metadata from the Kiwoom server.

        Parameters
        ----------
        tag : str
            One of ``ACCNO``, ``ACCOUNT_CNT``, ``USER_ID``, ``USER_NAME``,
            ``GetServerGubun``, ``KEY_BSECGB``, ``FIREW_SECGB``, etc.
        """
        result: str = self._ocx.dynamicCall(
            "GetLoginInfo(QString)", tag
        )
        logger.debug("GetLoginInfo('%s') → '%s'", tag, result)
        return result.strip() if result else ""

    def get_account_list(self) -> List[str]:
        """Return the list of account numbers for the logged-in user.

        키움 계좌번호는 세미콜론으로 구분된 문자열로 반환된다.
        """
        raw = self.get_login_info("ACCNO")
        # 세미콜론 구분 → 빈 문자열 제거
        accounts = [acct.strip() for acct in raw.split(";") if acct.strip()]
        logger.info("Account list: %s", accounts)
        return accounts

    @property
    def ocx(self) -> Any:
        """Direct access to the underlying OCX control.

        On non-Windows platforms this returns the ``_MockOcx`` instance.
        Prefer the high-level methods whenever possible.
        """
        return self._ocx

    # -- Event callbacks (이벤트 콜백) --

    def _on_event_connect(self, err_code: int) -> None:
        """Handle the ``OnEventConnect`` signal from the OCX control.

        Parameters
        ----------
        err_code : int
            ``0`` on success; negative value on failure.
        """
        was_connected = self._connected
        self._login_error_code = err_code
        if err_code == 0:
            self._connected = True
            logger.info("OnEventConnect: login succeeded (code=0)")
        else:
            self._connected = False
            logger.warning(
                "OnEventConnect: login failed — code=%d (%s)",
                err_code,
                _error_description(err_code),
            )
            if was_connected and self._on_disconnect is not None:
                try:
                    self._on_disconnect(err_code)
                except Exception:
                    logger.exception("on_disconnect callback failed")
            if was_connected:
                self._schedule_reconnect(err_code)
        # 대기 중인 login() 스레드에 완료 시그널 전송
        self._login_event.set()

    def _schedule_reconnect(self, err_code: int) -> None:
        with self._reconnect_lock:
            if self._reconnecting:
                return
            self._reconnecting = True

        def _reconnect() -> None:
            try:
                for attempt in range(1, self._reconnect_attempts + 1):
                    logger.warning("Reconnect attempt %d/%d", attempt, self._reconnect_attempts)
                    if self.login():
                        logger.info("Reconnect succeeded")
                        return
                    if attempt < self._reconnect_attempts:
                        time.sleep(self._reconnect_interval)
                if self._on_reconnect_failure is not None:
                    try:
                        self._on_reconnect_failure(err_code)
                    except Exception:
                        logger.exception("on_reconnect_failure callback failed")
            finally:
                with self._reconnect_lock:
                    self._reconnecting = False

        threading.Thread(target=_reconnect, daemon=True).start()

    # -- Private helpers (내부 유틸) --

    def _create_real_ocx(self) -> Any:
        """Instantiate the real Kiwoom QAxWidget (Windows only).

        PyQt5의 QAxWidget을 사용하여 키움 OCX 컨트롤을 로드한다.
        """
        try:
            from PyQt5.QAxContainer import QAxWidget  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "PyQt5.QAxContainer is required on Windows. "
                "Install it via: pip install PyQt5"
            ) from exc

        ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        logger.info("Real OCX control loaded: KHOPENAPI.KHOpenAPICtrl.1")
        return ocx

    def _bind_events(self) -> None:
        """Wire OCX signals to Python callbacks.

        실제 OCX에서는 OnEventConnect 시그널을 연결하고,
        Mock에서는 _MockOcx.connect()를 통해 콜백을 등록한다.
        """
        if self._mock:
            # Mock: 콜백을 직접 등록
            self._ocx._callbacks["OnEventConnect"] = self._on_event_connect
            logger.debug("Bound OnEventConnect via mock callback registry")
        else:
            # Real OCX: PyQt signal/slot 연결
            self._ocx.OnEventConnect.connect(self._on_event_connect)
            logger.debug("Bound OnEventConnect via PyQt signal/slot")
