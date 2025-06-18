from typing import List
import logging

class ExternalScreener:
    """
    외부 스크리너 활용 - 이미 필터링된 결과 사용
    - Finviz, Yahoo Screener 등 활용
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_finviz_screener_results(self, custom_filters: List[str] = None) -> List[str]:
        """
        Finviz 스크리너 결과 활용
        - 이미 필터링된 종목들만 가져옴
        """
        try:
            from finvizfinance.screener.overview import Overview

            foverview = Overview()

            default_filters = [
                'sh_avgvol_o200',    # 평균 거래량 20만 이상
                'sh_price_o5',       # 가격 $5 이상
                'cap_midover',       # 중형주 이상
            ]

            filters = custom_filters if custom_filters else default_filters
            foverview.set_filter(filters_dict=dict(zip(filters, [None]*len(filters))))

            df = foverview.screener_view()
            symbols = df['Ticker'].tolist()

            self.logger.info(f"Finviz에서 {len(symbols)}개 종목 발견")
            return symbols

        except ImportError:
            self.logger.warning("finvizfinance 라이브러리 없음. pip install finvizfinance")
            return []
        except Exception as e:
            self.logger.error(f"Finviz 스크리너 실행 실패: {e}")
            return []

    def get_yahoo_screener_results(self) -> List[str]:
        """Yahoo Finance 스크리너 결과 활용 (예시용)"""
        try:
            symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN']  # 예시 데이터
            self.logger.info(f"Yahoo 스크리너에서 {len(symbols)}개 종목 발견")
            return symbols
        except Exception as e:
            self.logger.error(f"Yahoo 스크리너 실행 실패: {e}")
            return []
