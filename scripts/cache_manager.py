#!/usr/bin/env python3
"""
OHLCV Data Cache Manager
데이터 캐시 관리 스크립트

Usage:
    # 캐시 상태 확인
    python scripts/cache_manager.py status

    # KOSPI 전체 종목 프리페치
    python scripts/cache_manager.py prefetch --universe KOSPI

    # 특정 종목 갱신
    python scripts/cache_manager.py refresh --ticker 005930.KS

    # 캐시 삭제
    python scripts/cache_manager.py clear
    python scripts/cache_manager.py clear --ticker 005930.KS
"""

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
from utils.data_cache import OHLCVCache, get_cache
from screener.kospi_fetcher import KospiListFetcher


def cmd_status(args):
    """캐시 상태 확인"""
    cache = get_cache()
    cache.print_status()


def cmd_prefetch(args):
    """데이터 프리페치"""
    cache = get_cache()
    fetcher = KospiListFetcher()

    # 유니버스 종목 가져오기
    universe = args.universe.upper()
    if universe == "KOSPI":
        symbols = fetcher.get_kospi_symbols()
    elif universe == "KOSDAQ":
        symbols = fetcher.get_kosdaq_symbols()
    elif universe == "ALL":
        symbols = fetcher.get_kospi_symbols() + fetcher.get_kosdaq_symbols()
    else:
        print(f"Unknown universe: {universe}")
        return

    tickers = [s['symbol'] for s in symbols]

    print(f"\n{'='*60}")
    print(f"  OHLCV Data Prefetch")
    print(f"{'='*60}")
    print(f"  유니버스: {universe}")
    print(f"  종목 수: {len(tickers)}")
    print(f"  캐시 기간: {args.days}일")
    print(f"{'='*60}\n")

    results = cache.prefetch(tickers, days=args.days, show_progress=True)

    success = sum(1 for v in results.values() if v)
    fail = len(results) - success

    print(f"\n{'='*60}")
    print(f"  완료: 성공 {success}, 실패 {fail}")
    print(f"{'='*60}\n")


def cmd_refresh(args):
    """캐시 갱신"""
    cache = get_cache()

    if args.ticker:
        # 단일 종목 갱신
        print(f"\n  {args.ticker} 캐시 갱신 중...")
        success = cache.refresh(args.ticker)
        if success:
            print(f"  완료!")
        else:
            print(f"  실패!")
    else:
        # 전체 갱신
        fetcher = KospiListFetcher()
        universe = args.universe.upper()

        if universe == "KOSPI":
            symbols = fetcher.get_kospi_symbols()
        elif universe == "KOSDAQ":
            symbols = fetcher.get_kosdaq_symbols()
        else:
            symbols = fetcher.get_kospi_symbols() + fetcher.get_kosdaq_symbols()

        tickers = [s['symbol'] for s in symbols]

        print(f"\n{'='*60}")
        print(f"  캐시 전체 갱신")
        print(f"{'='*60}")
        print(f"  종목 수: {len(tickers)}")
        print(f"{'='*60}\n")

        results = cache.refresh_all(tickers, show_progress=True)

        success = sum(1 for v in results.values() if v)
        fail = len(results) - success

        print(f"\n  완료: 성공 {success}, 실패 {fail}\n")


def cmd_clear(args):
    """캐시 삭제"""
    cache = get_cache()

    if args.ticker:
        # 단일 종목 삭제
        count = cache.clear(args.ticker)
        print(f"\n  {args.ticker} 캐시 삭제: {count}개 파일\n")
    else:
        # 전체 삭제 (확인 필요)
        if not args.force:
            status = cache.status()
            print(f"\n  전체 캐시를 삭제합니다.")
            print(f"  파일 수: {status['total_files']}")
            print(f"  크기: {status['total_size_mb']} MB")

            confirm = input("\n  계속하시겠습니까? (y/N): ")
            if confirm.lower() != 'y':
                print("  취소됨")
                return

        count = cache.clear()
        print(f"\n  캐시 삭제 완료: {count}개 파일\n")


def cmd_get(args):
    """단일 종목 데이터 가져오기 (테스트용)"""
    cache = get_cache()

    print(f"\n  {args.ticker} 데이터 가져오는 중...")
    data = cache.get(args.ticker, days=args.days, force_refresh=args.refresh)

    if data is not None:
        print(f"\n  데이터: {len(data)}행")
        print(f"  기간: {data.index[0]} ~ {data.index[-1]}")
        print(f"\n{data.tail(10)}\n")
    else:
        print(f"\n  데이터 가져오기 실패\n")


def main():
    parser = argparse.ArgumentParser(
        description="OHLCV Data Cache Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='명령')

    # status 명령
    parser_status = subparsers.add_parser('status', help='캐시 상태 확인')
    parser_status.set_defaults(func=cmd_status)

    # prefetch 명령
    parser_prefetch = subparsers.add_parser('prefetch', help='데이터 프리페치')
    parser_prefetch.add_argument(
        '--universe', type=str, default='KOSPI',
        help='유니버스 (KOSPI/KOSDAQ/ALL)'
    )
    parser_prefetch.add_argument(
        '--days', type=int, default=365,
        help='캐시 기간 (일, 기본 365)'
    )
    parser_prefetch.set_defaults(func=cmd_prefetch)

    # refresh 명령
    parser_refresh = subparsers.add_parser('refresh', help='캐시 갱신')
    parser_refresh.add_argument(
        '--ticker', type=str,
        help='특정 종목 (예: 005930.KS)'
    )
    parser_refresh.add_argument(
        '--universe', type=str, default='KOSPI',
        help='전체 갱신 시 유니버스'
    )
    parser_refresh.set_defaults(func=cmd_refresh)

    # clear 명령
    parser_clear = subparsers.add_parser('clear', help='캐시 삭제')
    parser_clear.add_argument(
        '--ticker', type=str,
        help='특정 종목만 삭제'
    )
    parser_clear.add_argument(
        '--force', '-f', action='store_true',
        help='확인 없이 삭제'
    )
    parser_clear.set_defaults(func=cmd_clear)

    # get 명령 (테스트용)
    parser_get = subparsers.add_parser('get', help='단일 종목 데이터 가져오기')
    parser_get.add_argument('ticker', type=str, help='종목 코드')
    parser_get.add_argument(
        '--days', type=int, default=100,
        help='데이터 기간 (일)'
    )
    parser_get.add_argument(
        '--refresh', action='store_true',
        help='캐시 무시하고 새로 가져오기'
    )
    parser_get.set_defaults(func=cmd_get)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
