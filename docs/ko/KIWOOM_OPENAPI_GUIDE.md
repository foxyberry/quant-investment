# 키움 OpenAPI+ 연동 가이드

> 실시간 계좌 연동, 주문 넣기, 잔고 모니터링
> 참고: 키움 OpenAPI+ 개발가이드 v1.1

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [개발 환경 설정](#2-개발-환경-설정)
3. [접속 및 로그인](#3-접속-및-로그인)
4. [TR 데이터 요청 흐름](#4-tr-데이터-요청-흐름)
5. [주문 넣기 (SendOrder)](#5-주문-넣기-sendorder)
6. [주문 체결 확인 (OnReceiveChejanData)](#6-주문-체결-확인-onreceivechejandata)
7. [실시간 데이터 구독](#7-실시간-데이터-구독)
8. [실시간 FID 레퍼런스](#8-실시간-fid-레퍼런스)
9. [조건검색 (실시간 스크리닝)](#9-조건검색-실시간-스크리닝)
10. [에러 코드표](#10-에러-코드표)
11. [신용주문 가이드](#11-신용주문-가이드)
12. [quant-investment 연동 설계](#12-quant-investment-연동-설계)

---

## 1. 아키텍처 개요

키움 OpenAPI+는 **ActiveX(OCX) 컨트롤 기반** 한국 주식시장(KOSPI/KOSDAQ) 트레이딩 API입니다.

```
┌─────────────────────────────────────────────────────┐
│                    내 애플리케이션                      │
│                                                      │
│   SetInputValue()  ──►  CommRqData()  (TR 요청)     │
│   SendOrder()      ──►  키움 서버     (주문)         │
│   SetRealReg()     ──►  실시간 피드   (시세)         │
│                                                      │
│   ◄── OnReceiveTrData      (TR 응답)                │
│   ◄── OnReceiveChejanData  (주문체결/잔고 통보)       │
│   ◄── OnReceiveRealData    (실시간 시세)             │
│   ◄── OnReceiveMsg         (서버 메시지)             │
│   ◄── OnEventConnect       (로그인 결과)             │
└─────────────────────────────────────────────────────┘
          │                        ▲
          ▼                        │
┌─────────────────────────────────────────────────────┐
│              KHOpenAPI.ocx (ActiveX 컨트롤)           │
│              Windows 레지스트리에 등록                  │
└─────────────────────────────────────────────────────┘
          │                        ▲
          ▼                        │
┌─────────────────────────────────────────────────────┐
│                   키움증권 서버                        │
└─────────────────────────────────────────────────────┘
```

### 주요 제약사항

- **Windows 전용** — OCX는 Windows COM 인프라 필요
- **단일 로그인** — PC당 하나만 로그인 가능 (기존 세션 자동 끊김)
- **요청 제한** — TR 요청: 초당 최대 1회 (초당 5회 시 임시 차단)
- **화면번호** — 최대 200개, 각 화면이 독립적으로 데이터/실시간 구독 관리
- **실시간 제한** — `SetRealReg` 한 번에 종목 100개 + FID 100개까지

---

## 2. 개발 환경 설정

### 필수 파일

| 파일 | 위치 | 용도 |
|------|------|------|
| `KHOpenAPI.ocx` | Windows 레지스트리 | 메인 API 컨트롤 |
| `data/*.enc` | 키움 설치 폴더 | TR 정의 파일 |
| `data/fidinfo.dat` | 키움 설치 폴더 | 실시간 FID 정의 |
| `koacommon.dll` | 키움 설치 폴더 | 공통 라이브러리 |

### Python 연동 (win32com 또는 PyQt5)

```python
import pythoncom
import win32com.client

# OCX 인스턴스 생성
kiwoom = win32com.client.Dispatch("KHOpenAPI.KHOpenAPICtrl.1")

# 또는 PyQt5의 QAxWidget 사용
from PyQt5.QAxContainer import QAxWidget
ocx = QAxWidget("KHOpenAPI.KHOpenAPICtrl.1")
```

### 모의투자 vs 실거래

- 로그인 다이얼로그에서 모의투자 체크박스 선택
- `GetLoginInfo("GetServerGubun")` 반환값:
  - `"1"` → 모의투자 서버
  - 그 외 → 실거래 서버

---

## 3. 접속 및 로그인

### 로그인 흐름

```python
# 1. 로그인 요청 (키움 로그인 창이 뜸)
ocx.dynamicCall("CommConnect()")

# 2. 로그인 결과 처리
def on_event_connect(err_code):
    if err_code == 0:
        print("로그인 성공")
    else:
        print(f"로그인 실패: 에러코드 {err_code}")

# 3. 로그인 후 계좌 정보 조회
account_count = ocx.dynamicCall("GetLoginInfo(QString)", "ACCOUNT_CNT")
accounts = ocx.dynamicCall("GetLoginInfo(QString)", "ACCNO")  # 세미콜론 구분
user_id = ocx.dynamicCall("GetLoginInfo(QString)", "USER_ID")
server_type = ocx.dynamicCall("GetLoginInfo(QString)", "GetServerGubun")
```

### GetLoginInfo 키 목록

| 키 | 반환값 |
|---|--------|
| `ACCOUNT_CNT` | 보유 계좌 수 |
| `ACCNO` | 계좌번호 목록 (`;` 구분) |
| `USER_ID` | 사용자 ID |
| `USER_NAME` | 사용자명 |
| `GetServerGubun` | `"1"` = 모의투자, 그 외 실거래 |

---

## 4. TR 데이터 요청 흐름

### 기본 패턴: 요청 → 이벤트 → 추출

```python
# 1단계: 입력값 설정
ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", "005930")

# 2단계: 요청 전송
# CommRqData(사용자구분명, TR코드, 연속조회여부, 화면번호)
ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                "주식기본정보", "OPT10001", 0, "0101")

# 3단계: OnReceiveTrData 이벤트에서 응답 처리
def on_receive_tr_data(screen_no, rq_name, tr_code, record_name, prev_next):
    if rq_name == "주식기본정보":
        name = ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code, record_name, 0, "종목명"
        ).strip()
        price = ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            tr_code, record_name, 0, "현재가"
        ).strip()
```

### 연속조회 (페이지네이션)

- `prev_next` 파라미터: `"2"` = 추가 데이터 있음
- 다음 `CommRqData` 호출 시 `prev_next=2`로 전달하면 나머지 데이터 수신

### 대량 데이터 (GetCommDataEx)

차트/과거 데이터는 `GetCommDataEx`를 사용하면 2차원 배열로 한 번에 수신:

```python
data = ocx.dynamicCall(
    "GetCommDataEx(QString, QString)", tr_code, "주식분봉차트조회"
)
# 반환: [[행0_열0, 행0_열1, ...], [행1_열0, ...], ...]
```

---

## 5. 주문 넣기 (SendOrder)

### 함수 시그니처

```
LONG SendOrder(
    BSTR sRQName,      // 사용자 구분명 (임의 지정)
    BSTR sScreenNo,     // 화면번호 (4자리, 예: "0101")
    BSTR sAccNo,        // 계좌번호
    LONG nOrderType,    // 주문유형 (아래 표 참고)
    BSTR sCode,         // 종목코드 (6자리)
    LONG nQty,          // 수량
    LONG nPrice,        // 가격 (시장가 주문 시 0)
    BSTR sHogaGb,       // 거래구분 (아래 표 참고)
    BSTR sOrgOrderNo    // 원주문번호 (취소/정정 시 사용, 신규는 "")
)
```

### 주문유형 (nOrderType)

| 코드 | 유형 | 설명 |
|------|------|------|
| 1 | **신규매수** | 새로운 매수 주문 |
| 2 | **신규매도** | 새로운 매도 주문 |
| 3 | **매수취소** | 기존 매수 주문 취소 |
| 4 | **매도취소** | 기존 매도 주문 취소 |
| 5 | **매수정정** | 기존 매수 주문 가격/수량 변경 |
| 6 | **매도정정** | 기존 매도 주문 가격/수량 변경 |

### 거래구분 (sHogaGb)

| 코드 | 유형 | 설명 |
|------|------|------|
| `00` | **지정가** | 지정한 가격으로 주문 |
| `03` | **시장가** | 현재 시장가격으로 즉시 체결 |
| `05` | 조건부지정가 | 장 마감 시 시장가 전환 |
| `06` | 최유리지정가 | 상대방 최우선호가로 지정 |
| `07` | 최우선지정가 | 자기 최우선호가로 지정 |
| `10` | 지정가IOC | 즉시 체결 후 잔량 취소 (지정가) |
| `13` | 시장가IOC | 즉시 체결 후 잔량 취소 (시장가) |
| `16` | 최유리IOC | 즉시 체결 후 잔량 취소 (최유리) |
| `20` | 지정가FOK | 전량 체결 또는 전량 취소 (지정가) |
| `23` | 시장가FOK | 전량 체결 또는 전량 취소 (시장가) |
| `26` | 최유리FOK | 전량 체결 또는 전량 취소 (최유리) |
| `61` | 장전시간외종가 | 장 시작 전 전일 종가로 주문 |
| `62` | 시간외단일가 | 시간외 단일가 매매 |
| `81` | 장후시간외종가 | 장 마감 후 당일 종가로 주문 |

### 주문 예시

```python
# 예시 1: 삼성전자(005930) 시장가 10주 매수
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수",    # sRQName
    "0101",           # sScreenNo
    "8123456789",     # sAccNo
    1,                # nOrderType: 신규매수
    "005930",         # sCode: 삼성전자
    10,               # nQty: 10주
    0,                # nPrice: 시장가이므로 0
    "03",             # sHogaGb: 시장가
    ""                # sOrgOrderNo: 신규이므로 빈 문자열
)

# 예시 2: 지정가 70,000원에 매수
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자지정가매수", "0101", "8123456789",
    1, "005930", 10, 70000, "00", ""
)

# 예시 3: 매수 주문 취소
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수취소", "0101", "8123456789",
    3,                # nOrderType: 매수취소
    "005930", 10, 0, "00",
    "12345"           # sOrgOrderNo: 원래 주문번호
)

# 예시 4: 주문 정정 (가격 변경)
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수정정", "0101", "8123456789",
    5,                # nOrderType: 매수정정
    "005930", 10, 71000, "00",
    "12345"           # sOrgOrderNo: 원래 주문번호
)
```

### 반환값

- `0`: 주문 전송 성공 (**체결 성공이 아님!** 체결 여부는 OnReceiveChejanData에서 확인)
- 0이 아닌 값: 에러 ([에러 코드표](#10-에러-코드표) 참고)

---

## 6. 주문 체결 확인 (OnReceiveChejanData)

주문 상태 추적과 잔고 변동을 확인하는 **가장 중요한 이벤트**입니다.

### 이벤트 시그니처

```python
def on_receive_chejan_data(sGubun, nItemCnt, sFidList):
    """
    sGubun: "0" = 주문체결통보 (주문 접수/확인/체결)
             "1" = 잔고통보 (보유수량/예수금 변동)
             "3" = 특이신호
    nItemCnt: 데이터 항목 수
    sFidList: 세미콜론 구분 FID 리스트
    """
    pass
```

### 체결 데이터 읽기

```python
def on_receive_chejan_data(sGubun, nItemCnt, sFidList):
    if sGubun == "0":  # 주문체결통보
        order_no = ocx.dynamicCall("GetChejanData(int)", 9203)    # 주문번호
        stock_code = ocx.dynamicCall("GetChejanData(int)", 9001)  # 종목코드
        order_status = ocx.dynamicCall("GetChejanData(int)", 913) # 주문상태
        order_qty = ocx.dynamicCall("GetChejanData(int)", 900)    # 주문수량
        order_price = ocx.dynamicCall("GetChejanData(int)", 901)  # 주문가격
        unfilled_qty = ocx.dynamicCall("GetChejanData(int)", 902) # 미체결수량
        fill_price = ocx.dynamicCall("GetChejanData(int)", 910)   # 체결가
        fill_qty = ocx.dynamicCall("GetChejanData(int)", 911)     # 체결량
        fill_time = ocx.dynamicCall("GetChejanData(int)", 908)    # 체결시간
        buy_sell = ocx.dynamicCall("GetChejanData(int)", 907)     # 1:매도, 2:매수

    elif sGubun == "1":  # 잔고통보
        stock_code = ocx.dynamicCall("GetChejanData(int)", 9001)  # 종목코드
        stock_name = ocx.dynamicCall("GetChejanData(int)", 302)   # 종목명
        holding_qty = ocx.dynamicCall("GetChejanData(int)", 930)  # 보유수량
        avg_price = ocx.dynamicCall("GetChejanData(int)", 931)    # 매입단가
        total_cost = ocx.dynamicCall("GetChejanData(int)", 932)   # 총매입가
        current_price = ocx.dynamicCall("GetChejanData(int)", 10) # 현재가
        pnl = ocx.dynamicCall("GetChejanData(int)", 950)          # 당일 매도 손익
        pnl_rate = ocx.dynamicCall("GetChejanData(int)", 8019)    # 손익율
```

### 주문체결 FID 목록 (sGubun = "0")

| FID | 설명 |
|-----|------|
| 9201 | 계좌번호 |
| 9203 | 주문번호 |
| 9001 | 종목코드 |
| 302 | 종목명 |
| 913 | 주문상태 (접수/확인/체결) |
| 900 | 주문수량 |
| 901 | 주문가격 |
| 902 | 미체결수량 |
| 903 | 체결누계금액 |
| 904 | 원주문번호 |
| 905 | 주문구분 (+현금내수, -현금매도...) |
| 906 | 매매구분 (보통, 시장가...) |
| 907 | 매도수구분 (1:매도, 2:매수) |
| 908 | 주문/체결시간 (HHMMSSMS) |
| 909 | 체결번호 |
| 910 | 체결가 |
| 911 | 체결량 |
| 912 | 주문업무분류 (JJ:주식주문, FJ:선물옵션, JG:주식잔고, FG:선물옵션잔고) |
| 938 | 당일매매 수수료 |
| 939 | 당일매매 세금 |

### 잔고 FID 목록 (sGubun = "1")

| FID | 설명 |
|-----|------|
| 9201 | 계좌번호 |
| 9001 | 종목코드 |
| 302 | 종목명 |
| 10 | 현재가 |
| 930 | 보유수량 |
| 931 | 매입단가 |
| 932 | 총매입가 |
| 933 | 주문가능수량 |
| 946 | 매도/매수구분 |
| 950 | 당일 총 매도 손익 |
| 951 | 예수금 |
| 8019 | 손익율 |

---

## 7. 실시간 데이터 구독

### 등록

```python
# SetRealReg(화면번호, 종목코드리스트, FID리스트, 등록타입)
ocx.dynamicCall(
    "SetRealReg(QString, QString, QString, QString)",
    "0001",                        # 화면번호
    "005930;000660",               # 종목코드 (세미콜론 구분)
    "10;12;15;13",                 # FID: 현재가, 등락율, 체결량, 누적거래량
    "0"                            # 타입: "0"=교체, "1"=추가
)
```

### 등록 타입 동작

| 값 | 동작 |
|---|------|
| `"0"` | **교체** — 해당 화면에 마지막 등록한 종목만 실시간 수신. 기존 등록 해제됨 |
| `"1"` | **추가** — 기존 등록 종목에 새 종목 추가 |

**중요**: 화면 최초 등록은 반드시 `"0"`, 이후 추가는 `"1"` 사용

### 실시간 데이터 수신

```python
def on_receive_real_data(sJongmokCode, sRealType, sRealData):
    """
    sJongmokCode: 종목코드
    sRealType: 실시간 타입명 (예: "주식체결", "주식호가잔량")
    sRealData: 원시 데이터 문자열
    """
    if sRealType == "주식체결":
        current_price = ocx.dynamicCall(
            "GetCommRealData(QString, int)", sJongmokCode, 10
        )  # FID 10 = 현재가
        change_rate = ocx.dynamicCall(
            "GetCommRealData(QString, int)", sJongmokCode, 12
        )  # FID 12 = 등락율
        volume = ocx.dynamicCall(
            "GetCommRealData(QString, int)", sJongmokCode, 15
        )  # FID 15 = 거래량
```

### 해제

```python
# 특정 종목 실시간 해제
ocx.dynamicCall("SetRealRemove(QString, QString)", "0001", "005930")

# 화면 전체 실시간 해제
ocx.dynamicCall("SetRealRemove(QString, QString)", "0001", "ALL")

# 전체 실시간 해제
ocx.dynamicCall("SetRealRemove(QString, QString)", "ALL", "ALL")
```

### 제한사항

- `SetRealReg` 한 번에 종목 **최대 100개**
- `SetRealReg` 한 번에 FID **최대 100개**
- 전체 화면번호 **최대 200개**

---

## 8. 실시간 FID 레퍼런스

### 주식시세 (시세 변동 시)

| FID | 설명 |
|-----|------|
| 10 | 현재가, 체결가, 실시간종가 |
| 11 | 전일 대비 |
| 12 | 등락율 |
| 27 | (최우선)매도호가 |
| 28 | (최우선)매수호가 |
| 13 | 누적거래량 |
| 14 | 누적거래대금 |
| 16 | 시가 |
| 17 | 고가 |
| 18 | 저가 |
| 311 | 시가총액(억) |

### 주식체결 (체결 발생 시)

| FID | 설명 |
|-----|------|
| 20 | 체결시간 (HHMMSS) |
| 10 | 현재가, 체결가 |
| 12 | 등락율 |
| 15 | 거래량, 체결량 |
| 13 | 누적거래량 |
| 228 | 체결강도 |
| 290 | 장구분 |

### 주문체결 (FID 8.19, OnReceiveChejanData에서 수신)

| FID | 설명 |
|-----|------|
| 9201 | 계좌번호 |
| 9203 | 주문번호 |
| 9001 | 종목코드, 업종코드 |
| 913 | 주문상태 (접수, 확인, 체결) |
| 900 | 주문수량 |
| 901 | 주문가격 |
| 902 | 미체결수량 |
| 907 | 매도수구분 (1:매도, 2:매수) |
| 910 | 체결가 |
| 911 | 체결량 |

### 잔고 (FID 8.20, OnReceiveChejanData에서 수신)

| FID | 설명 |
|-----|------|
| 9201 | 계좌번호 |
| 9001 | 종목코드 |
| 302 | 종목명 |
| 930 | 보유수량 |
| 931 | 매입단가 |
| 932 | 총매입가 |
| 933 | 주문가능수량 |
| 950 | 당일 총 매도 손익 |
| 951 | 예수금 |
| 8019 | 손익율 |

---

## 9. 조건검색 (실시간 스크리닝)

키움 서버에 저장된 사용자 조건식으로 실시간 종목 편입/이탈 감지가 가능합니다.

### 전체 흐름

```
1. GetConditionLoad()           → 서버에서 조건식 로드
2. OnReceiveConditionVer        → 로드 성공 확인
3. GetConditionNameList()       → 조건명 리스트 조회
4. SendCondition(nSearch=1)     → 실시간 조건 모니터링 시작
5. OnReceiveTrCondition         → 조건 부합 종목 리스트 수신
6. OnReceiveRealCondition       → 실시간 편입("I")/이탈("D") 알림
7. SendConditionStop()          → 모니터링 중지
```

### 예시

```python
# 조건식 로드
ocx.dynamicCall("GetConditionLoad()")

# OnReceiveConditionVer로 성공 확인 후:
condition_list = ocx.dynamicCall("GetConditionNameList()")
# 반환: "인덱스1^조건명1;인덱스2^조건명2;..."

# 실시간 모니터링 시작 (nSearch=1)
ocx.dynamicCall(
    "SendCondition(QString, QString, int, int)",
    "0101",           # 화면번호
    "급등주조건",      # 조건명
    0,                # 조건명 인덱스
    1                 # nSearch: 0=일반조회, 1=실시간조회, 2=연속조회
)

# OnReceiveRealCondition: 실시간으로 종목 편입/이탈 알림
def on_receive_real_condition(strCode, strType, strConditionName, strConditionIndex):
    if strType == "I":  # 편입
        print(f"{strCode} 조건 {strConditionName}에 편입")
    elif strType == "D":  # 이탈
        print(f"{strCode} 조건 {strConditionName}에서 이탈")
```

### 제한사항

- 실시간 조건검색 화면 **최대 10개** 동시 가능
- 조건식은 **키움 HTS(영웅문) [0150] 화면**에서 생성해야 함
- 조건 변경 시 반드시 `SendConditionStop()` 먼저 호출

---

## 10. 에러 코드표

| 코드 | 상수명 | 설명 |
|------|--------|------|
| 0 | OP_ERR_NONE | 정상처리 |
| -10 | OP_ERR_FAIL | 실패 |
| -100 | OP_ERR_LOGIN | 사용자정보교환실패 |
| -101 | OP_ERR_CONNECT | 서버접속실패 |
| -102 | OP_ERR_VERSION | 버전처리실패 |
| -103 | OP_ERR_FIREWALL | 개인방화벽실패 |
| -104 | OP_ERR_MEMORY | 메모리보호실패 |
| -105 | OP_ERR_INPUT | 함수입력값오류 |
| -106 | OP_ERR_SOCKET_CLOSED | 통신연결종료 |
| -200 | OP_ERR_SISE_OVERFLOW | 시세조회과부하 |
| -201 | OP_ERR_RQ_STRUCT_FAIL | 전문작성초기화실패 |
| -202 | OP_ERR_RQ_STRING_FAIL | 전문작성입력값오류 |
| -203 | OP_ERR_NO_DATA | 데이터없음 |
| -204 | OP_ERR_OVER_MAX_DATA | 조회가능한종목수초과 |
| -205 | OP_ERR_DATA_RCV_FAIL | 데이터수신실패 |
| -206 | OP_ERR_OVER_MAX_FID | 조회가능한FID수초과 |
| -207 | OP_ERR_REAL_CANCEL | 실시간해제오류 |
| -300 | OP_ERR_ORD_WRONG_INPUT | 입력값오류 |
| -301 | OP_ERR_ORD_WRONG_ACCTNO | 계좌비밀번호없음 |
| -302 | OP_ERR_OTHER_ACC_USE | 타인계좌사용오류 |
| -303 | OP_ERR_MIS_2BILL_EXC | 주문가격이20억원을초과 |
| -304 | OP_ERR_MIS_5BILL_EXC | 주문가격이50억원을초과 |
| -305 | OP_ERR_MIS_1PER_EXC | 주문수량이총발행주수의1%초과 |
| -306 | OP_ERR_MIS_3PER_EXC | 주문수량은총발행주수의3%초과 |
| -307 | OP_ERR_SEND_FAIL | 주문전송실패 |
| -308 | OP_ERR_ORD_OVERFLOW | 주문전송과부하 |
| -309 | OP_ERR_MIS_300CNT_EXC | 주문수량300계약초과 |
| -310 | OP_ERR_MIS_500CNT_EXC | 주문수량500계약초과 |
| -340 | OP_ERR_ORD_WRONG_ACCTINFO | 계좌정보없음 |
| -500 | OP_ERR_ORD_SYMCODE_EMPTY | 종목코드없음 |

---

## 11. 신용주문 가이드

신용주문은 `SendOrder()` 대신 `SendOrderCredit()`을 사용합니다.

### 신용주문 유형

| 유형 | 구분코드 | 대출일 | 비고 |
|------|----------|--------|------|
| 신용매수 | `03` | 공백입력 | |
| 융자상환 (신용매도) | `33` | 종목별 대출일 | |
| 융자합 (신용매도) | `99` | `99991231` | 5종목 이하잔고만 가능 |

### 주의사항

- 신용주문은 **실거래만 가능** (모의투자 불가)
- 대상: "자기융자"와 "대주" 유형만
- 대출일 설정이 매우 중요 — 상환일 기준으로 지정
- 신용잔고 조회: `OPW00005` TR 사용

---

## 12. quant-investment 연동 설계

### 제안 모듈 구조

```
quant-investment/
├── kiwoom/                    # 신규 모듈
│   ├── __init__.py
│   ├── connection.py          # 로그인, 세션 관리
│   ├── order.py               # SendOrder 래퍼, 주문 상태 머신
│   ├── realtime.py            # 실시간 구독 관리
│   ├── chejan_handler.py      # OnReceiveChejanData 처리
│   ├── tr_request.py          # TR 데이터 요청 헬퍼
│   ├── condition_search.py    # 조건검색 실시간 스크리닝
│   ├── constants.py           # FID, 에러코드, 주문유형 상수
│   └── screen_manager.py      # 화면번호 할당 관리
```

### 기존 모듈 연동 포인트

| 기존 모듈 | 연동 방법 |
|----------|----------|
| `portfolio/holdings.py` | `OnReceiveChejanData(sGubun="1")`로 실시간 잔고 동기화 |
| `portfolio/executor.py` | 페이퍼 트레이딩을 `SendOrder()` 실제 주문으로 교체 |
| `portfolio/trigger.py` | 폴링 대신 실시간 가격 피드(`SetRealReg`) 사용 |
| `portfolio/monitor.py` | 실시간 구독으로 포지션 모니터링 |
| `discovery/` | 조건검색으로 실시간 종목 발굴 |

### 주문 상태 머신

```
          SendOrder()
              │
              ▼
         ┌─────────┐
         │  접수    │  ← OnReceiveChejanData(913="접수")
         │ (Placed) │
         └────┬────┘
              │
              ▼
         ┌─────────┐
         │  확인    │  ← OnReceiveChejanData(913="확인")
         │(Confirmed)│
         └────┬────┘
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
┌────────┐ ┌──────┐ ┌────────┐
│ 체결   │ │부분체결│ │ 취소   │
│(Filled)│ │(Partial)│ │(Cancelled)│
└────────┘ └──────┘ └────────┘
```

### 안전 장치

1. **모의투자로 시작** — `GetServerGubun() == "1"` 확인
2. **킬 스위치** — 모든 미체결 주문 긴급 취소 기능
3. **요청 제한** — 주문 큐, 초당 최대 1건
4. **포지션 한도** — `portfolio/risk.py` 규칙으로 주문 전 사전 검증
5. **감사 로깅** — 모든 SendOrder 호출과 ChejanData 이벤트 기록
6. **중복 주문 방지** — 주문번호 추적, 재전송 방지
7. **연결 모니터링** — `OnEventConnect` 음수 에러코드로 단절 감지/재접속

### 구현 권장 순서

1. **Phase 1**: 접속 + 로그인 + 계좌 정보 조회
2. **Phase 2**: TR 데이터 요청 (종목 정보, 계좌 잔고)
3. **Phase 3**: 실시간 데이터 구독 (가격 피드)
4. **Phase 4**: 주문 넣기 (모의투자에서만)
5. **Phase 5**: 주문 체결 처리 (ChejanData)
6. **Phase 6**: 기존 포트폴리오 모듈 연동
7. **Phase 7**: 조건검색 + 종목발굴 모듈 연동
8. **Phase 8**: 실거래 전환 (충분한 테스트 후)
