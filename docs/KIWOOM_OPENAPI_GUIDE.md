# Kiwoom OpenAPI+ Integration Guide

> Real-time account connection, order placement, and position monitoring
> Reference: Kiwoom OpenAPI+ Developer Guide v1.1

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Environment Setup](#2-environment-setup)
3. [Connection & Login](#3-connection--login)
4. [TR Data Request Flow](#4-tr-data-request-flow)
5. [Order Placement (SendOrder)](#5-order-placement-sendorder)
6. [Order Confirmation (OnReceiveChejanData)](#6-order-confirmation-onreceivechejandata)
7. [Real-time Data Subscription](#7-real-time-data-subscription)
8. [Real-time FID Reference](#8-real-time-fid-reference)
9. [Condition Search (Real-time Screening)](#9-condition-search-real-time-screening)
10. [Error Codes](#10-error-codes)
11. [Credit Order Guide](#11-credit-order-guide)
12. [Integration Design for quant-investment](#12-integration-design-for-quant-investment)

---

## 1. Architecture Overview

Kiwoom OpenAPI+ is an **ActiveX (OCX) control-based** trading API for the Korean stock market (KOSPI/KOSDAQ).

```
┌─────────────────────────────────────────────────────┐
│                  Your Application                    │
│                                                      │
│   SetInputValue()  ──►  CommRqData()                │
│   SendOrder()      ──►  Kiwoom Server               │
│   SetRealReg()     ──►  Real-time Feed              │
│                                                      │
│   ◄── OnReceiveTrData      (TR response)            │
│   ◄── OnReceiveChejanData  (order/balance update)   │
│   ◄── OnReceiveRealData    (real-time quotes)       │
│   ◄── OnReceiveMsg         (server messages)        │
│   ◄── OnEventConnect       (login result)           │
└─────────────────────────────────────────────────────┘
          │                        ▲
          ▼                        │
┌─────────────────────────────────────────────────────┐
│              KHOpenAPI.ocx (ActiveX Control)          │
│              Registered in Windows Registry           │
└─────────────────────────────────────────────────────┘
          │                        ▲
          ▼                        │
┌─────────────────────────────────────────────────────┐
│              Kiwoom Securities Server                 │
└─────────────────────────────────────────────────────┘
```

### Key Constraints

- **Windows only** — OCX requires Windows COM infrastructure
- **Single login** — One login per PC (disconnects previous session)
- **Rate limits** — TR requests: max 1 per second (5 per second causes temp ban)
- **Screen numbers** — Up to 200 screens, each managing its own data/real-time subscriptions
- **Real-time limits** — Max 100 stocks + 100 FIDs per `SetRealReg` call

---

## 2. Environment Setup

### Required Files

| File | Location | Purpose |
|------|----------|---------|
| `KHOpenAPI.ocx` | Windows Registry | Main API control |
| `data/*.enc` | Kiwoom install dir | TR definition files |
| `data/fidinfo.dat` | Kiwoom install dir | Real-time FID definitions |
| `koacommon.dll` | Kiwoom install dir | Common library |

### Python Integration (via `pykiwoom` or custom wrapper)

```python
import pythoncom
import win32com.client

# Create OCX instance
kiwoom = win32com.client.Dispatch("KHOpenAPI.KHOpenAPICtrl.1")

# Or use QAxWidget in PyQt5
from PyQt5.QAxContainer import QAxWidget
ocx = QAxWidget("KHOpenAPI.KHOpenAPICtrl.1")
```

### Mock Trading vs Live Trading

- Mock trading available via login dialog checkbox
- `GetLoginInfo("GetServerGubun")` returns:
  - `"1"` → Mock trading server
  - Other → Live trading server

---

## 3. Connection & Login

### Login Flow

```python
# 1. Request login (opens Kiwoom login dialog)
ocx.dynamicCall("CommConnect()")

# 2. Handle login result
def on_event_connect(err_code):
    if err_code == 0:
        print("Login successful")
    else:
        print(f"Login failed: error code {err_code}")

# 3. Get account info after login
account_count = ocx.dynamicCall("GetLoginInfo(QString)", "ACCOUNT_CNT")
accounts = ocx.dynamicCall("GetLoginInfo(QString)", "ACCNO")  # semicolon-separated
user_id = ocx.dynamicCall("GetLoginInfo(QString)", "USER_ID")
server_type = ocx.dynamicCall("GetLoginInfo(QString)", "GetServerGubun")
```

### GetLoginInfo Keys

| Key | Return Value |
|-----|-------------|
| `ACCOUNT_CNT` | Number of accounts |
| `ACCNO` | Account numbers (`;` separated) |
| `USER_ID` | User ID |
| `USER_NAME` | User name |
| `GetServerGubun` | `"1"` = mock, else live |

---

## 4. TR Data Request Flow

### Standard Pattern: Request → Event → Extract

```python
# Step 1: Set input values
ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", "005930")

# Step 2: Send request
# CommRqData(sRQName, sTrCode, nPrevNext, sScreenNo)
ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                "주식기본정보", "OPT10001", 0, "0101")

# Step 3: Handle response in OnReceiveTrData event
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

### Pagination (연속조회)

- `prev_next` parameter: `"2"` means more data available
- Pass `prev_next=2` in next `CommRqData` call to fetch remaining data

### Bulk Data (GetCommDataEx)

For chart/historical data, use `GetCommDataEx` to receive all rows at once as a 2D array:

```python
data = ocx.dynamicCall(
    "GetCommDataEx(QString, QString)", tr_code, "주식분봉차트조회"
)
# Returns: [[row0_col0, row0_col1, ...], [row1_col0, ...], ...]
```

---

## 5. Order Placement (SendOrder)

### Function Signature

```
LONG SendOrder(
    BSTR sRQName,      // Request name (user-defined)
    BSTR sScreenNo,     // Screen number (4-digit, e.g., "0101")
    BSTR sAccNo,        // Account number
    LONG nOrderType,    // Order type (see below)
    BSTR sCode,         // Stock code (6-digit)
    LONG nQty,          // Quantity
    LONG nPrice,        // Price (0 for market order)
    BSTR sHogaGb,       // Price type (see below)
    BSTR sOrgOrderNo    // Original order no (for cancel/modify, else "")
)
```

### Order Types (nOrderType)

| Code | Type | Description |
|------|------|-------------|
| 1 | **신규매수** | New buy order |
| 2 | **신규매도** | New sell order |
| 3 | **매수취소** | Cancel buy order |
| 4 | **매도취소** | Cancel sell order |
| 5 | **매수정정** | Modify buy order |
| 6 | **매도정정** | Modify sell order |

### Price Types (sHogaGb)

| Code | Type | Description |
|------|------|-------------|
| `00` | **지정가** | Limit order |
| `03` | **시장가** | Market order |
| `05` | 조건부지정가 | Conditional limit |
| `06` | 최유리지정가 | Best limit |
| `07` | 최우선지정가 | Priority limit |
| `10` | 지정가IOC | Limit IOC |
| `13` | 시장가IOC | Market IOC |
| `16` | 최유리IOC | Best limit IOC |
| `20` | 지정가FOK | Limit FOK |
| `23` | 시장가FOK | Market FOK |
| `26` | 최유리FOK | Best limit FOK |
| `61` | 장전시간외종가 | Pre-market closing price |
| `62` | 시간외단일가 | After-hours single price |
| `81` | 장후시간외종가 | Post-market closing price |

### Order Examples

```python
# Example 1: Market buy 10 shares of Samsung (005930)
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수",    # sRQName
    "0101",           # sScreenNo
    "8123456789",     # sAccNo
    1,                # nOrderType: 신규매수
    "005930",         # sCode: 삼성전자
    10,               # nQty
    0,                # nPrice: 0 for market order
    "03",             # sHogaGb: 시장가
    ""                # sOrgOrderNo: empty for new order
)

# Example 2: Limit buy at 70,000 KRW
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자지정가매수", "0101", "8123456789",
    1, "005930", 10, 70000, "00", ""
)

# Example 3: Cancel a buy order
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수취소", "0101", "8123456789",
    3,                # nOrderType: 매수취소
    "005930", 10, 0, "00",
    "12345"           # sOrgOrderNo: original order number
)

# Example 4: Modify order (change price)
ocx.dynamicCall(
    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
    "삼성전자매수정정", "0101", "8123456789",
    5,                # nOrderType: 매수정정
    "005930", 10, 71000, "00",
    "12345"           # sOrgOrderNo
)
```

### Return Value

- `0`: Order sent successfully (does NOT mean filled)
- Non-zero: Error (see [Error Codes](#10-error-codes))

---

## 6. Order Confirmation (OnReceiveChejanData)

This is the **critical event** for tracking order status and position changes.

### Event Signature

```python
def on_receive_chejan_data(sGubun, nItemCnt, sFidList):
    """
    sGubun: "0" = 주문체결통보 (order/fill notification)
             "1" = 잔고통보 (balance/position update)
             "3" = 특이신호
    nItemCnt: number of data items
    sFidList: semicolon-separated FID list
    """
    pass
```

### Reading Chejan Data

```python
def on_receive_chejan_data(sGubun, nItemCnt, sFidList):
    if sGubun == "0":  # Order/fill notification
        order_no = ocx.dynamicCall("GetChejanData(int)", 9203)    # 주문번호
        stock_code = ocx.dynamicCall("GetChejanData(int)", 9001)  # 종목코드
        order_status = ocx.dynamicCall("GetChejanData(int)", 913) # 주문상태
        order_qty = ocx.dynamicCall("GetChejanData(int)", 900)    # 주문수량
        order_price = ocx.dynamicCall("GetChejanData(int)", 901)  # 주문가격
        unfilled_qty = ocx.dynamicCall("GetChejanData(int)", 902) # 미체결수량
        fill_price = ocx.dynamicCall("GetChejanData(int)", 910)   # 체결가
        fill_qty = ocx.dynamicCall("GetChejanData(int)", 911)     # 체결량
        fill_time = ocx.dynamicCall("GetChejanData(int)", 908)    # 주문/체결시간
        buy_sell = ocx.dynamicCall("GetChejanData(int)", 907)     # 1:매도, 2:매수

    elif sGubun == "1":  # Balance update
        stock_code = ocx.dynamicCall("GetChejanData(int)", 9001)
        stock_name = ocx.dynamicCall("GetChejanData(int)", 302)
        holding_qty = ocx.dynamicCall("GetChejanData(int)", 930)  # 보유수량
        avg_price = ocx.dynamicCall("GetChejanData(int)", 931)    # 매입단가
        total_cost = ocx.dynamicCall("GetChejanData(int)", 932)   # 총매입가
        current_price = ocx.dynamicCall("GetChejanData(int)", 10) # 현재가
        pnl = ocx.dynamicCall("GetChejanData(int)", 950)          # 당일 총 매도 손익
        pnl_rate = ocx.dynamicCall("GetChejanData(int)", 8019)    # 손익율
```

### Order/Fill FIDs (sGubun = "0")

| FID | Description |
|-----|-------------|
| 9201 | 계좌번호 (Account number) |
| 9203 | 주문번호 (Order number) |
| 9001 | 종목코드 (Stock code) |
| 302 | 종목명 (Stock name) |
| 913 | 주문상태 (접수/확인/체결) |
| 900 | 주문수량 (Order quantity) |
| 901 | 주문가격 (Order price) |
| 902 | 미체결수량 (Unfilled quantity) |
| 903 | 체결누계금액 (Cumulative fill amount) |
| 904 | 원주문번호 (Original order no) |
| 905 | 주문구분 (+현금내수, -현금매도...) |
| 906 | 매매구분 (보통, 시장가...) |
| 907 | 매도수구분 (1:매도, 2:매수) |
| 908 | 주문/체결시간 (HHMMSSMS) |
| 909 | 체결번호 (Fill number) |
| 910 | 체결가 (Fill price) |
| 911 | 체결량 (Fill quantity) |
| 912 | 주문업무분류 (JJ:주식, FJ:선물옵션...) |
| 914 | 단위체결가 (Unit fill price) |
| 915 | 단위체결량 (Unit fill quantity) |
| 938 | 당일매매수수료 (Day trading fee) |
| 939 | 당일매매세금 (Day trading tax) |

### Balance FIDs (sGubun = "1")

| FID | Description |
|-----|-------------|
| 9201 | 계좌번호 (Account number) |
| 9001 | 종목코드 (Stock code) |
| 302 | 종목명 (Stock name) |
| 10 | 현재가 (Current price) |
| 930 | 보유수량 (Holding quantity) |
| 931 | 매입단가 (Average buy price) |
| 932 | 총매입가 (Total cost) |
| 933 | 주문가능수량 (Orderable quantity) |
| 945 | 당일순매수량 (Day net buy qty) |
| 946 | 매도/매수구분 (Sell/Buy flag) |
| 950 | 당일 총 매도 손익 (Day total P&L) |
| 951 | 예수금 (Deposit) |
| 27 | (최우선)매도호가 (Best ask) |
| 28 | (최우선)매수호가 (Best bid) |
| 307 | 기준가 (Base price) |
| 8019 | 손익율 (P&L rate) |

---

## 7. Real-time Data Subscription

### Registration

```python
# SetRealReg(sScreenNo, sCodeList, sFidList, sOptType)
ocx.dynamicCall(
    "SetRealReg(QString, QString, QString, QString)",
    "0001",                        # Screen number
    "005930;000660",               # Stock codes (semicolon-separated)
    "10;12;15;13",                 # FID list: 현재가, 등락율, 체결량, 누적거래량
    "0"                            # OptType: "0" = replace, "1" = append
)
```

### OptType Behavior

| Value | Behavior |
|-------|----------|
| `"0"` | **Replace** — Only the last registered stocks get real-time data on this screen. Previous registrations are removed. |
| `"1"` | **Append** — Add new stocks to existing real-time registrations on this screen. |

**Important**: First registration on a screen must use `"0"`. Subsequent additions use `"1"`.

### Receiving Real-time Data

```python
def on_receive_real_data(sJongmokCode, sRealType, sRealData):
    """
    sJongmokCode: stock code
    sRealType: real-time type name (e.g., "주식체결", "주식호가잔량")
    sRealData: raw data string
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
        )  # FID 15 = 거래량, 체결량
```

### Unregistration

```python
# Remove specific stock from screen
ocx.dynamicCall("SetRealRemove(QString, QString)", "0001", "005930")

# Remove all stocks from screen
ocx.dynamicCall("SetRealRemove(QString, QString)", "0001", "ALL")

# Remove all screens
ocx.dynamicCall("SetRealRemove(QString, QString)", "ALL", "ALL")
```

### Limits

- Max **100 stocks** per `SetRealReg` call
- Max **100 FIDs** per `SetRealReg` call
- Max **200 screen numbers** total

---

## 8. Real-time FID Reference

### 8.1 Stock Quote (주식시세)

| FID | Description |
|-----|-------------|
| 10 | Current price (현재가, 체결가) |
| 11 | Change vs previous close (전일 대비) |
| 12 | Change rate % (등락율) |
| 27 | Best ask price (최우선 매도호가) |
| 28 | Best bid price (최우선 매수호가) |
| 13 | Cumulative volume (누적거래량) |
| 14 | Cumulative amount (누적거래대금) |
| 16 | Open (시가) |
| 17 | High (고가) |
| 18 | Low (저가) |
| 25 | Change sign vs prev close (전일대비기호) |
| 311 | Market cap in 억 (시가총액) |

### 8.2 Stock Execution (주식체결)

| FID | Description |
|-----|-------------|
| 20 | Fill time HHMMSS (체결시간) |
| 10 | Current/fill price (현재가, 체결가) |
| 11 | Change vs prev close (전일 대비) |
| 12 | Change rate % (등락율) |
| 15 | Volume per tick (거래량, 체결량) |
| 13 | Cumulative volume (누적거래량) |
| 228 | Fill strength (체결강도) |
| 290 | Session type (장구분) |

### 8.19 Order/Fill (주문체결) — via OnReceiveChejanData

| FID | Description |
|-----|-------------|
| 9201 | Account number |
| 9203 | Order number |
| 9001 | Stock code |
| 302 | Stock name |
| 912 | Order category (JJ:주식, FJ:선물옵션, JG:주식잔고, FG:선물옵션잔고) |
| 913 | Order status (접수/확인/체결) |
| 900 | Order quantity |
| 901 | Order price |
| 902 | Unfilled quantity |
| 907 | Buy/Sell (1:매도, 2:매수) |
| 908 | Order/fill time |
| 910 | Fill price |
| 911 | Fill quantity |

### 8.20 Balance (잔고) — via OnReceiveChejanData

| FID | Description |
|-----|-------------|
| 9201 | Account number |
| 9001 | Stock code |
| 302 | Stock name |
| 10 | Current price |
| 930 | Holding quantity |
| 931 | Average buy price |
| 932 | Total cost |
| 933 | Orderable quantity |
| 946 | Buy/Sell flag |
| 950 | Day P&L |
| 951 | Deposit (예수금) |
| 8019 | P&L rate |

---

## 9. Condition Search (Real-time Screening)

Kiwoom supports server-side condition-based screening with real-time updates.

### Flow

```
1. GetConditionLoad()           → Load conditions from server
2. OnReceiveConditionVer        → Confirm load success
3. GetConditionNameList()       → Get list of conditions
4. SendCondition(nSearch=1)     → Start real-time condition monitoring
5. OnReceiveTrCondition         → Receive matching stock list
6. OnReceiveRealCondition       → Real-time entry("I")/exit("D") signals
7. SendConditionStop()          → Stop monitoring
```

### Example

```python
# Load conditions
ocx.dynamicCall("GetConditionLoad()")

# After OnReceiveConditionVer confirms success:
condition_list = ocx.dynamicCall("GetConditionNameList()")
# Returns: "인덱스1^조건명1;인덱스2^조건명2;..."

# Start real-time monitoring (nSearch=1)
ocx.dynamicCall(
    "SendCondition(QString, QString, int, int)",
    "0101",           # Screen number
    "급등주조건",      # Condition name
    0,                # Condition index
    1                 # nSearch: 0=one-time, 1=real-time, 2=continuous
)

# OnReceiveRealCondition fires when stocks enter/exit the condition
def on_receive_real_condition(strCode, strType, strConditionName, strConditionIndex):
    if strType == "I":  # Entry
        print(f"{strCode} entered condition {strConditionName}")
    elif strType == "D":  # Exit
        print(f"{strCode} exited condition {strConditionName}")
```

### Limits

- Max **10 real-time condition screens** at a time
- Conditions must be created in Kiwoom HTS (영웅문) [0150] screen
- Must call `SendConditionStop()` before switching conditions

---

## 10. Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | OP_ERR_NONE | Success |
| -10 | OP_ERR_FAIL | General failure |
| -100 | OP_ERR_LOGIN | Login credential error |
| -101 | OP_ERR_CONNECT | Server connection failed |
| -102 | OP_ERR_VERSION | Version mismatch |
| -103 | OP_ERR_FIREWALL | Firewall blocked |
| -104 | OP_ERR_MEMORY | Memory protection error |
| -105 | OP_ERR_INPUT | Invalid input parameter |
| -106 | OP_ERR_SOCKET_CLOSED | Connection closed |
| -200 | OP_ERR_SISE_OVERFLOW | Quote request overflow |
| -201 | OP_ERR_RQ_STRUCT_FAIL | Request structure init failed |
| -202 | OP_ERR_RQ_STRING_FAIL | Request string input error |
| -203 | OP_ERR_NO_DATA | No data available |
| -204 | OP_ERR_OVER_MAX_DATA | Too many stock codes |
| -205 | OP_ERR_DATA_RCV_FAIL | Data receive failed |
| -206 | OP_ERR_OVER_MAX_FID | Too many FIDs |
| -207 | OP_ERR_REAL_CANCEL | Real-time unregister error |
| -300 | OP_ERR_ORD_WRONG_INPUT | Invalid order input |
| -301 | OP_ERR_ORD_WRONG_ACCTNO | Wrong account password |
| -302 | OP_ERR_OTHER_ACC_USE | Unauthorized account use |
| -303 | OP_ERR_MIS_2BILL_EXC | Order amount > 2 billion KRW |
| -304 | OP_ERR_MIS_5BILL_EXC | Order amount > 5 billion KRW |
| -305 | OP_ERR_MIS_1PER_EXC | Quantity > 1% of total shares |
| -306 | OP_ERR_MIS_3PER_EXC | Quantity > 3% of total shares |
| -307 | OP_ERR_SEND_FAIL | Order send failed |
| -308 | OP_ERR_ORD_OVERFLOW | Order send overload |
| -309 | OP_ERR_MIS_300CNT_EXC | Quantity > 300 contracts |
| -310 | OP_ERR_MIS_500CNT_EXC | Quantity > 500 contracts |
| -340 | OP_ERR_ORD_WRONG_ACCTINFO | No account info |
| -500 | OP_ERR_ORD_SYMCODE_EMPTY | Stock code empty |

---

## 11. Credit Order Guide

Credit orders use `SendOrderCredit()` instead of `SendOrder()`.

### Credit Order Types

| Type | Code | Loan Date | Notes |
|------|------|-----------|-------|
| Credit buy (신용매수) | `03` | Empty string | |
| Credit sell - repay (융자상환) | `33` | Loan date per stock | |
| Credit sell - consolidate (융자합) | `99` | `99991231` | Max 5 stocks |

### Important Notes

- Credit orders: **live trading only** (not available in mock trading)
- Target: Only "자기융자" and "대주" types
- Loan date is critical — determines repayment schedule
- Use `OPW00005` TR to query credit balance and loan dates

---

## 12. Integration Design for quant-investment

### Proposed Architecture

```
quant-investment/
├── kiwoom/                    # New module
│   ├── __init__.py
│   ├── connection.py          # Login, session management
│   ├── order.py               # SendOrder wrapper, order state machine
│   ├── realtime.py            # Real-time subscription manager
│   ├── chejan_handler.py      # OnReceiveChejanData processor
│   ├── tr_request.py          # TR data request helpers
│   ├── condition_search.py    # Condition-based real-time screening
│   ├── constants.py           # FIDs, error codes, order types
│   └── screen_manager.py      # Screen number allocation
```

### Integration with Existing Modules

| Existing Module | Integration Point |
|----------------|-------------------|
| `portfolio/holdings.py` | Sync positions via `OnReceiveChejanData(sGubun="1")` |
| `portfolio/executor.py` | Replace paper trade with `SendOrder()` |
| `portfolio/trigger.py` | Use real-time price feed instead of polling |
| `portfolio/monitor.py` | Subscribe to `SetRealReg` for position monitoring |
| `discovery/` | Use condition search for real-time screening |

### Order State Machine

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

### Safety Considerations

1. **Always start with mock trading** (`GetServerGubun() == "1"`)
2. **Implement kill switch** — Emergency cancel all pending orders
3. **Rate limit** — Queue orders, max 1 per second
4. **Position limits** — Check against `portfolio/risk.py` rules before sending
5. **Audit logging** — Log every SendOrder call and ChejanData event
6. **Duplicate order prevention** — Track order numbers, prevent re-submission
7. **Connection monitoring** — Handle disconnection via `OnEventConnect` with negative error codes

### Recommended Development Order

1. **Phase 1**: Connection + Login + Account info query
2. **Phase 2**: TR data requests (stock info, account balance)
3. **Phase 3**: Real-time data subscription (price feed)
4. **Phase 4**: Order placement (mock trading only)
5. **Phase 5**: Order confirmation handling (ChejanData)
6. **Phase 6**: Integration with existing portfolio module
7. **Phase 7**: Condition search integration with discovery module
8. **Phase 8**: Live trading (after thorough testing)
