"""Kiwoom OpenAPI+ constants.

Defines all constants required for Kiwoom OpenAPI+ integration:
FID codes, error codes, order types, price types (hoga), market types,
real-time data types, chejan categories, and server types.
"""

from enum import Enum, IntEnum


# ---------------------------------------------------------------------------
# Error codes (에러코드)
# ---------------------------------------------------------------------------


class ErrorCode(IntEnum):
    """Kiwoom OpenAPI+ error codes returned by CommRqData / SendOrder."""

    OP_ERR_NONE = 0               # 정상처리
    OP_ERR_FAIL = -10             # 실패
    OP_ERR_LOGIN = -100           # 사용자 정보 교환 실패
    OP_ERR_CONNECT = -101         # 서버 접속 실패
    OP_ERR_VERSION = -102         # 버전 처리 실패
    OP_ERR_FIREWALL = -103        # 개인방화벽 실패
    OP_ERR_MEMORY = -104          # 메모리 보호 실패
    OP_ERR_INPUT = -105           # 함수 입력값 오류
    OP_ERR_SOCKET_CLOSED = -106   # 통신 연결 종료
    OP_ERR_SISE_OVERFLOW = -200   # 시세 과부하
    OP_ERR_RQ_STRUCT_FAIL = -201  # 전문 작성 초기화 실패
    OP_ERR_RQ_STRING_FAIL = -202  # 전문 작성 입력값 오류
    OP_ERR_NO_DATA = -203         # 데이터 없음
    OP_ERR_OVER_MAX_DATA = -204   # 종목코드 과다 요청
    OP_ERR_DATA_RCV_FAIL = -205   # 데이터 수신 실패
    OP_ERR_OVER_MAX_FID = -206    # FID 과다 요청
    OP_ERR_REAL_CANCEL = -207     # 실시간 해제 오류
    OP_ERR_ORD_WRONG_INPUT = -300   # 주문 입력값 오류
    OP_ERR_ORD_WRONG_ACCTNO = -301  # 계좌 비밀번호 불일치
    OP_ERR_OTHER_ACC_USE = -302     # 타인계좌 사용 오류
    OP_ERR_MIS_2BILL_EXC = -303     # 주문가격 20억원 초과
    OP_ERR_MIS_5BILL_EXC = -304     # 주문가격 50억원 초과
    OP_ERR_MIS_1PER_EXC = -305      # 주문수량 총발행주수 1% 초과
    OP_ERR_MIS_3PER_EXC = -306      # 주문수량 총발행주수 3% 초과
    OP_ERR_SEND_FAIL = -307         # 주문전송 실패
    OP_ERR_ORD_OVERFLOW = -308      # 주문전송 과부하
    OP_ERR_MIS_300CNT_EXC = -309    # 주문수량 300계약 초과
    OP_ERR_MIS_500CNT_EXC = -310    # 주문수량 500계약 초과
    OP_ERR_ORD_WRONG_ACCTINFO = -340  # 계좌 정보 없음
    OP_ERR_ORD_SYMCODE_EMPTY = -500   # 종목코드 없음


# ---------------------------------------------------------------------------
# Order type (주문유형)
# ---------------------------------------------------------------------------


class OrderType(IntEnum):
    """Kiwoom SendOrder nOrderType parameter."""

    NEW_BUY = 1       # 신규매수
    NEW_SELL = 2      # 신규매도
    CANCEL_BUY = 3    # 매수취소
    CANCEL_SELL = 4   # 매도취소
    MODIFY_BUY = 5    # 매수정정
    MODIFY_SELL = 6   # 매도정정


# ---------------------------------------------------------------------------
# Price type / Hoga type (호가유형)
# ---------------------------------------------------------------------------


class HogaType(str, Enum):
    """Kiwoom SendOrder sHogaGb parameter (price type)."""

    LIMIT = "00"              # 지정가
    MARKET = "03"             # 시장가
    CONDITIONAL_LIMIT = "05"  # 조건부지정가
    BEST_LIMIT = "06"         # 최유리지정가
    FIRST_LIMIT = "07"        # 최우선지정가
    PRE_MARKET = "61"         # 장전시간외
    POST_MARKET = "62"        # 장후시간외
    OFF_HOURS_SINGLE = "81"   # 시간외단일가


# ---------------------------------------------------------------------------
# Market type (시장구분)
# ---------------------------------------------------------------------------


class MarketType(str, Enum):
    """Market identifiers used in Kiwoom API calls."""

    KOSPI = "STK"   # 코스피
    KOSDAQ = "KSQ"  # 코스닥


# ---------------------------------------------------------------------------
# Real-time data type (실시간 데이터 타입)
# ---------------------------------------------------------------------------


class RealType(str, Enum):
    """Real-time data type names for SetRealReg."""

    STOCK_QUOTE = "주식시세"        # 주식시세
    STOCK_EXECUTION = "주식체결"    # 주식체결
    STOCK_ORDERBOOK = "주식호가잔량"  # 주식호가잔량
    ORDER_EXECUTION = "주문체결"    # 주문체결
    BALANCE = "잔고"               # 잔고


# ---------------------------------------------------------------------------
# FID constants (FID 상수)
# ---------------------------------------------------------------------------


class FID:
    """Field ID constants for Kiwoom real-time / TR data.

    This is a namespace class and should not be instantiated.
    FIDs are grouped by their primary usage context.
    """

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("FID is a namespace class and cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError("FID is a namespace class and cannot be instantiated")

    # -- 주식시세 (Stock quote) --
    CURRENT_PRICE = 10   # 현재가
    CHANGE = 11          # 전일대비
    CHANGE_RATE = 12     # 등락율
    VOLUME = 13          # 누적거래량
    AMOUNT = 14          # 누적거래대금
    OPEN = 16            # 시가
    HIGH = 17            # 고가
    LOW = 18             # 저가
    CHANGE_SIGN = 25     # 전일대비기호
    BEST_ASK = 27        # 매도호가 (최우선)
    BEST_BID = 28        # 매수호가 (최우선)
    MARKET_CAP = 311     # 시가총액

    # -- 주식체결 (Stock execution) --
    TICK_VOLUME = 15     # 거래량 (단위체결)
    FILL_TIME = 20       # 체결시간
    FILL_STRENGTH = 228  # 체결강도
    SESSION_TYPE = 290   # 장구분

    # -- 주문체결 (Order execution) --
    CODE = 9001          # 종목코드
    NAME = 302           # 종목명
    ORDER_QTY = 900      # 주문수량
    ORDER_PRICE = 901    # 주문가격
    UNFILLED_QTY = 902   # 미체결수량
    BUY_SELL = 907       # 매도수구분
    ORDER_TIME = 908     # 주문/체결시간
    FILL_PRICE = 910     # 체결가
    FILL_QTY = 911       # 체결량
    ORDER_CATEGORY = 912  # 주문구분
    ORDER_STATUS = 913   # 주문상태
    ACCOUNT = 9201       # 계좌번호
    ORDER_NO = 9203      # 주문번호

    # -- 잔고 (Balance / Holdings) --
    HOLDING_QTY = 930    # 보유수량
    AVG_BUY_PRICE = 931  # 매입단가
    TOTAL_COST = 932     # 총매입가
    ORDERABLE_QTY = 933  # 주문가능수량
    DAY_BUY_SELL = 946   # 당일매매수량
    DAY_PNL = 950        # 당일손익
    DEPOSIT = 951        # 예수금
    PNL_RATE = 8019      # 손익율


# ---------------------------------------------------------------------------
# Chejan category (체잔 구분)
# ---------------------------------------------------------------------------


class ChejanGubun(str, Enum):
    """Category identifier for OnReceiveChejanData callback."""

    ORDER = "0"    # 주문체결통보
    BALANCE = "1"  # 잔고통보


# ---------------------------------------------------------------------------
# Server type (서버 구분)
# ---------------------------------------------------------------------------


class ServerType(str, Enum):
    """Kiwoom login server type (mock vs. live trading)."""

    MOCK = "1"  # 모의투자
    LIVE = "0"  # 실거래
