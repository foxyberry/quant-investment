#!/usr/bin/env python3
"""
Investor Trading Analysis Script
투자자별 매매 동향 조회 (네이버 금융)

Usage:
    # 삼성전자 최근 20일 매매 동향
    python scripts/investor_trading.py 005930

    # 여러 페이지 조회 (더 많은 데이터)
    python scripts/investor_trading.py 005930 --pages 3

    # 요약만 보기
    python scripts/investor_trading.py 005930 --summary

    # 외국인/기관 순매수 상위 전체 (추천)
    python scripts/investor_trading.py --top 10

    # 외국인만 순매수 상위
    python scripts/investor_trading.py --top-foreign 10

    # 기관만 순매수 상위
    python scripts/investor_trading.py --top-institution 10

    # KOSDAQ 순매수 상위
    python scripts/investor_trading.py --top 10 --market KOSDAQ
"""

import argparse
import requests
import pandas as pd
from io import StringIO
from pykrx import stock
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')


def get_stock_name(ticker: str) -> str:
    """종목명 조회"""
    try:
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return ticker


def get_top_market_cap_tickers(market: str = "KOSPI", top_n: int = 50) -> list:
    """시가총액 상위 종목 코드 가져오기 (로컬 파일 우선)"""
    from pathlib import Path

    # 로컬 파일에서 시가총액 순 종목 리스트 로드
    data_dir = Path(__file__).parent.parent / "data" / "korean"

    if market.upper() == "KOSPI":
        master_file = data_dir / "kospi_master.csv"
    else:
        master_file = data_dir / "kosdaq_master.csv"

    if master_file.exists():
        try:
            df = pd.read_csv(master_file)
            if 'code' in df.columns:
                return df['code'].astype(str).str.zfill(6).head(top_n).tolist()
        except Exception:
            pass

    # 로컬 파일이 없으면 네이버에서 가져오기
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    sosok = "0" if market.upper() == "KOSPI" else "1"
    tickers = []

    try:
        for page in range(1, 3):
            url = f'https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}'
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'euc-kr'

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            for a in soup.select('a[href*="/item/main.naver?code="]'):
                href = a.get('href', '')
                if 'code=' in href:
                    code = href.split('code=')[1][:6]
                    if code.isdigit() and code not in tickers:
                        tickers.append(code)
    except Exception as e:
        print(f"  네트워크 오류: {e}")

    return tickers[:top_n]


def get_investor_trading_naver(ticker: str, pages: int = 1) -> pd.DataFrame:
    """네이버 금융에서 투자자별 매매 동향 가져오기"""
    code = ticker.replace('.KS', '').replace('.KQ', '').zfill(6)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

    all_data = []

    for page in range(1, pages + 1):
        url = f'https://finance.naver.com/item/frgn.naver?code={code}&page={page}'
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr'

        tables = pd.read_html(StringIO(response.text))

        if len(tables) > 3:
            df = tables[3]

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] if col[0] == col[1] else f"{col[0]}_{col[1]}"
                              for col in df.columns]

            df = df.dropna(how='all')
            df = df.dropna(subset=['날짜'] if '날짜' in df.columns else [df.columns[0]])

            all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)
    date_col = '날짜' if '날짜' in result.columns else result.columns[0]
    result = result.drop_duplicates(subset=[date_col])

    return result


def get_recent_net_purchase(ticker: str, days: int = 5) -> dict:
    """최근 N일 순매수량 및 거래량 조회"""
    try:
        df = get_investor_trading_naver(ticker, pages=1)
        if df.empty:
            return None

        # 컬럼 찾기
        inst_col = None
        frgn_col = None
        vol_col = None
        for col in df.columns:
            if '기관' in str(col) and '순매매' in str(col):
                inst_col = col
            elif '외국인' in str(col) and '순매매' in str(col):
                frgn_col = col
            elif '거래량' in str(col):
                vol_col = col

        if not inst_col or not frgn_col:
            return None

        # 최근 N일 합계/평균
        recent = df.head(days)
        avg_volume = recent[vol_col].mean() if vol_col else 0

        return {
            'ticker': ticker,
            'name': get_stock_name(ticker),
            'institution': recent[inst_col].sum() if inst_col else 0,
            'foreign': recent[frgn_col].sum() if frgn_col else 0,
            'avg_volume': avg_volume,  # 평균 거래량
        }
    except Exception:
        return None


def collect_investor_data(market: str, days: int) -> pd.DataFrame:
    """투자자별 데이터 수집"""
    print(f"\n  {market} 시총 상위 50개 종목에서 조회 중...")

    tickers = get_top_market_cap_tickers(market, top_n=50)
    if not tickers:
        print("  종목 목록을 가져올 수 없습니다.")
        return pd.DataFrame()

    print(f"  {len(tickers)}개 종목 데이터 수집 중...")

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_recent_net_purchase, t, days): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    if not results:
        print("  데이터를 수집할 수 없습니다.")
        return pd.DataFrame()

    return pd.DataFrame(results)


def format_volume(n: float) -> str:
    """거래량 포맷팅"""
    if pd.isna(n) or n == 0:
        return "-"
    if abs(n) >= 100_000_000:
        return f"{n/100_000_000:,.1f}억"
    elif abs(n) >= 10_000:
        return f"{n/10_000:,.0f}만"
    else:
        return f"{n:,.0f}"


def show_all_rankings(top_n: int, market: str, days: int):
    """외국인/기관 순매수/순매도 전체 출력"""
    df = collect_investor_data(market, days)
    if df.empty:
        return

    print(f"\n{'='*75}")
    print(f"  {market} 투자자별 순매수/순매도 상위 {top_n}종목 (최근 {days}일)")
    print(f"{'='*75}")

    # 외국인 순매수 상위
    print(f"\n  [외국인 순매수 TOP {top_n}]")
    print(f"  {'순위':>4} {'종목명':<12} {'외국인':>11} {'기관':>11} {'거래량':>10}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*11} {'-'*10}")
    for i, (_, row) in enumerate(df.nlargest(top_n, 'foreign').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['foreign']):>11} {format_number(row['institution']):>11} {vol:>10}")

    # 외국인 순매도 상위
    print(f"\n  [외국인 순매도 TOP {top_n}]")
    print(f"  {'순위':>4} {'종목명':<12} {'외국인':>11} {'기관':>11} {'거래량':>10}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*11} {'-'*10}")
    for i, (_, row) in enumerate(df.nsmallest(top_n, 'foreign').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['foreign']):>11} {format_number(row['institution']):>11} {vol:>10}")

    # 기관 순매수 상위
    print(f"\n  [기관 순매수 TOP {top_n}]")
    print(f"  {'순위':>4} {'종목명':<12} {'기관':>11} {'외국인':>11} {'거래량':>10}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*11} {'-'*10}")
    for i, (_, row) in enumerate(df.nlargest(top_n, 'institution').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['institution']):>11} {format_number(row['foreign']):>11} {vol:>10}")

    # 기관 순매도 상위
    print(f"\n  [기관 순매도 TOP {top_n}]")
    print(f"  {'순위':>4} {'종목명':<12} {'기관':>11} {'외국인':>11} {'거래량':>10}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*11} {'-'*10}")
    for i, (_, row) in enumerate(df.nsmallest(top_n, 'institution').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['institution']):>11} {format_number(row['foreign']):>11} {vol:>10}")

    # 쌍끌이 (외국인+기관 동시 매수/매도)
    df['combined'] = df['foreign'] + df['institution']

    print(f"\n  [쌍끌이 매수 TOP {top_n}] (외국인+기관 동반 매수)")
    print(f"  {'순위':>4} {'종목명':<12} {'합계':>11} {'외국인':>9} {'기관':>9} {'거래량':>9}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*9} {'-'*9} {'-'*9}")
    for i, (_, row) in enumerate(df.nlargest(top_n, 'combined').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['combined']):>11} {format_number(row['foreign']):>9} {format_number(row['institution']):>9} {vol:>9}")

    print(f"\n  [쌍끌이 매도 TOP {top_n}] (외국인+기관 동반 매도)")
    print(f"  {'순위':>4} {'종목명':<12} {'합계':>11} {'외국인':>9} {'기관':>9} {'거래량':>9}")
    print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*9} {'-'*9} {'-'*9}")
    for i, (_, row) in enumerate(df.nsmallest(top_n, 'combined').iterrows(), 1):
        name = row['name'][:10] if len(row['name']) > 10 else row['name']
        vol = format_volume(row.get('avg_volume', 0))
        print(f"  {i:>4} {name:<12} {format_number(row['combined']):>11} {format_number(row['foreign']):>9} {format_number(row['institution']):>9} {vol:>9}")

    # 거래량 상위 (관심도)
    if 'avg_volume' in df.columns:
        print(f"\n  [거래량 TOP {top_n}] (관심도 높은 종목)")
        print(f"  {'순위':>4} {'종목명':<12} {'거래량':>11} {'외국인':>11} {'기관':>11}")
        print(f"  {'-'*4} {'-'*12} {'-'*11} {'-'*11} {'-'*11}")
        for i, (_, row) in enumerate(df.nlargest(top_n, 'avg_volume').iterrows(), 1):
            name = row['name'][:10] if len(row['name']) > 10 else row['name']
            vol = format_volume(row['avg_volume'])
            print(f"  {i:>4} {name:<12} {vol:>11} {format_number(row['foreign']):>11} {format_number(row['institution']):>11}")


def show_top_investors(investor_type: str, top_n: int, market: str, days: int):
    """순매수 상위 종목 출력 (단일 투자자)"""
    df = collect_investor_data(market, days)
    if df.empty:
        return

    sort_col = 'foreign' if investor_type == 'foreign' else 'institution'
    investor_name = '외국인' if investor_type == 'foreign' else '기관'

    # 순매수 상위
    df_buy = df.nlargest(top_n, sort_col)

    print(f"\n{'='*70}")
    print(f"  {market} {investor_name} 순매수 상위 {top_n}종목 (최근 {days}일)")
    print(f"{'='*70}")
    print(f"\n  {'순위':>4} {'종목명':<16} {'기관':>14} {'외국인':>14}")
    print(f"  {'-'*4} {'-'*16} {'-'*14} {'-'*14}")

    for i, (_, row) in enumerate(df_buy.iterrows(), 1):
        name = row['name'][:14] if len(row['name']) > 14 else row['name']
        inst = format_number(row['institution'])
        frgn = format_number(row['foreign'])
        print(f"  {i:>4} {name:<16} {inst:>14} {frgn:>14}")

    # 순매도 상위
    df_sell = df.nsmallest(top_n, sort_col)

    print(f"\n{'='*70}")
    print(f"  {market} {investor_name} 순매도 상위 {top_n}종목 (최근 {days}일)")
    print(f"{'='*70}")
    print(f"\n  {'순위':>4} {'종목명':<16} {'기관':>14} {'외국인':>14}")
    print(f"  {'-'*4} {'-'*16} {'-'*14} {'-'*14}")

    for i, (_, row) in enumerate(df_sell.iterrows(), 1):
        name = row['name'][:14] if len(row['name']) > 14 else row['name']
        inst = format_number(row['institution'])
        frgn = format_number(row['foreign'])
        print(f"  {i:>4} {name:<16} {inst:>14} {frgn:>14}")


def format_number(n: float, unit: str = "주") -> str:
    """숫자 포맷팅"""
    if pd.isna(n):
        return "-"

    if unit == "주":
        if abs(n) >= 100_000_000:
            return f"{n/100_000_000:+,.1f}억주"
        elif abs(n) >= 10_000:
            return f"{n/10_000:+,.0f}만주"
        else:
            return f"{n:+,.0f}주"
    else:
        if abs(n) >= 100_000_000:
            return f"{n/100_000_000:+,.1f}억"
        elif abs(n) >= 10_000:
            return f"{n/10_000:+,.0f}만"
        else:
            return f"{n:+,.0f}"


def print_trading_data(df: pd.DataFrame, ticker: str, stock_name: str):
    """일별 매매 동향 출력"""
    print(f"\n{'='*75}")
    print(f"  {stock_name} ({ticker}) 투자자별 매매 동향")
    print(f"{'='*75}")

    if df.empty:
        print("  데이터가 없습니다.")
        return

    date_col = '날짜' if '날짜' in df.columns else df.columns[0]
    price_col = '종가' if '종가' in df.columns else None

    inst_col = None
    frgn_col = None

    for col in df.columns:
        if '기관' in str(col) and '순매매' in str(col):
            inst_col = col
        elif '외국인' in str(col) and '순매매' in str(col):
            frgn_col = col

    print(f"\n  {'날짜':<12} {'종가':>10} {'기관':>14} {'외국인':>14}")
    print(f"  {'-'*12} {'-'*10} {'-'*14} {'-'*14}")

    for _, row in df.head(20).iterrows():
        date_str = str(row[date_col]).replace('.', '-')[:10] if pd.notna(row[date_col]) else '-'

        price_str = '-'
        if price_col and pd.notna(row[price_col]):
            price_str = f"{int(row[price_col]):,}"

        inst_str = format_number(row[inst_col]) if inst_col and pd.notna(row[inst_col]) else '-'
        frgn_str = format_number(row[frgn_col]) if frgn_col and pd.notna(row[frgn_col]) else '-'

        print(f"  {date_str:<12} {price_str:>10} {inst_str:>14} {frgn_str:>14}")


def print_summary(df: pd.DataFrame, ticker: str, stock_name: str):
    """기간 합계 요약 출력"""
    print(f"\n{'='*75}")
    print(f"  {stock_name} ({ticker}) 투자자별 매매 요약 ({len(df)}일)")
    print(f"{'='*75}\n")

    if df.empty:
        print("  데이터가 없습니다.")
        return

    inst_col = None
    frgn_col = None

    for col in df.columns:
        if '기관' in str(col) and '순매매' in str(col):
            inst_col = col
        elif '외국인' in str(col) and '순매매' in str(col):
            frgn_col = col

    print(f"  {'투자자':<10} {'순매수량':>16} {'판정':>12}")
    print(f"  {'-'*10} {'-'*16} {'-'*12}")

    if inst_col:
        inst_total = df[inst_col].sum()
        judgment = "매수 우위" if inst_total > 0 else "매도 우위" if inst_total < 0 else "중립"
        print(f"  {'기관':<10} {format_number(inst_total):>16} {judgment:>12}")

    if frgn_col:
        frgn_total = df[frgn_col].sum()
        judgment = "매수 우위" if frgn_total > 0 else "매도 우위" if frgn_total < 0 else "중립"
        print(f"  {'외국인':<10} {format_number(frgn_total):>16} {judgment:>12}")

    frgn_hold_col = None
    frgn_ratio_col = None
    for col in df.columns:
        if '외국인' in str(col) and '보유주수' in str(col):
            frgn_hold_col = col
        elif '외국인' in str(col) and '보유율' in str(col):
            frgn_ratio_col = col

    if frgn_hold_col and frgn_ratio_col:
        latest = df.iloc[0]
        hold = latest[frgn_hold_col]
        ratio = latest[frgn_ratio_col]
        print(f"\n  [외국인 보유 현황]")
        if pd.notna(hold):
            print(f"  - 보유주수: {hold/100_000_000:,.2f}억주")
        if pd.notna(ratio):
            print(f"  - 보유율: {ratio}")

    if frgn_col:
        print(f"\n  [추세 분석]")
        recent_5 = df.head(5)[frgn_col].sum()
        prev_5 = df.head(10).tail(5)[frgn_col].sum() if len(df) >= 10 else 0

        if recent_5 > 0 and recent_5 > prev_5:
            trend = "최근 5일 외국인 순매수 + 증가세 ↑"
        elif recent_5 > 0:
            trend = "최근 5일 외국인 순매수 (감소세)"
        elif recent_5 < 0 and recent_5 < prev_5:
            trend = "최근 5일 외국인 순매도 + 심화 ↓"
        elif recent_5 < 0:
            trend = "최근 5일 외국인 순매도 (완화세)"
        else:
            trend = "최근 5일 외국인 중립"
        print(f"  - {trend}")


def main():
    parser = argparse.ArgumentParser(description="투자자별 매매 동향 조회 (네이버 금융)")
    parser.add_argument("ticker", nargs="?", help="종목 코드 (예: 005930)")
    parser.add_argument("--pages", type=int, default=1, help="조회 페이지 수 (1페이지=약20일)")
    parser.add_argument("--summary", action="store_true", help="요약만 출력")
    parser.add_argument("--top", type=int, metavar="N", help="외국인/기관 순매수 상위 전체 N종목")
    parser.add_argument("--top-foreign", type=int, metavar="N", help="외국인 순매수 상위 N종목")
    parser.add_argument("--top-institution", type=int, metavar="N", help="기관 순매수 상위 N종목")
    parser.add_argument("--market", default="KOSPI", help="시장 (KOSPI/KOSDAQ)")
    parser.add_argument("--days", type=int, default=5, help="순매수 집계 기간 (일)")

    args = parser.parse_args()

    # 순매수 상위 조회
    if args.top:
        show_all_rankings(args.top, args.market, args.days)
        return

    if args.top_foreign:
        show_top_investors('foreign', args.top_foreign, args.market, args.days)
        return

    if args.top_institution:
        show_top_investors('institution', args.top_institution, args.market, args.days)
        return

    # 개별 종목 조회
    if not args.ticker:
        parser.print_help()
        return

    ticker = args.ticker.replace(".KS", "").replace(".KQ", "").zfill(6)
    stock_name = get_stock_name(ticker)

    print(f"\n  조회 중... {stock_name} ({ticker})")

    df = get_investor_trading_naver(ticker, pages=args.pages)

    if df.empty:
        print(f"\n  데이터를 찾을 수 없습니다.")
        return

    if args.summary:
        print_summary(df, ticker, stock_name)
    else:
        print_trading_data(df, ticker, stock_name)
        print_summary(df, ticker, stock_name)


if __name__ == "__main__":
    main()
