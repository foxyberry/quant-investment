"""
Fundamental Data Enrichment Module
Canonical location. Moved from data_enrichment/fundamental.py.

기본적 분석 데이터 수집 모듈

This module fetches financial/fundamental data for stocks using:
- yfinance for US stocks
- pykrx/Naver for Korean stocks (ending with .KS or .KQ)

Usage:
    from data_sources.fundamental.fundamental import FundamentalEnricher

    enricher = FundamentalEnricher()
    data = enricher.enrich("AAPL")           # US stock
    data = enricher.enrich("005930.KS")      # Korean stock (Samsung)
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

import yfinance as yf

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    NAVER_SCRAPING_AVAILABLE = True
except ImportError:
    NAVER_SCRAPING_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FundamentalData:
    """Fundamental data structure for a stock"""

    # Valuation
    pe_ratio: Optional[float] = None           # P/E ratio (TTM)
    forward_pe: Optional[float] = None         # Forward P/E
    pb_ratio: Optional[float] = None           # P/B ratio
    ps_ratio: Optional[float] = None           # P/S ratio
    peg_ratio: Optional[float] = None          # PEG ratio

    # Profitability
    eps: Optional[float] = None                # Earnings Per Share
    revenue: Optional[float] = None            # Total Revenue
    revenue_growth: Optional[float] = None     # YoY revenue growth %
    profit_margin: Optional[float] = None      # Profit margin %
    roe: Optional[float] = None                # Return on Equity %
    roa: Optional[float] = None                # Return on Assets %

    # Financial Health
    debt_to_equity: Optional[float] = None     # Debt to Equity ratio
    current_ratio: Optional[float] = None      # Current ratio
    quick_ratio: Optional[float] = None        # Quick ratio

    # Dividend
    dividend_yield: Optional[float] = None     # Dividend yield %
    payout_ratio: Optional[float] = None       # Dividend payout ratio %

    # Size
    market_cap: Optional[float] = None         # Market capitalization
    enterprise_value: Optional[float] = None   # Enterprise value

    # Info
    sector: Optional[str] = None               # Sector classification
    industry: Optional[str] = None             # Industry classification
    description: Optional[str] = None          # Company description

    # Metadata
    ticker: Optional[str] = None               # Stock ticker
    name: Optional[str] = None                 # Company name
    currency: Optional[str] = None             # Currency of financial data
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat()
        return result


class FundamentalEnricher:
    """
    Fetches fundamental/financial data for stocks.

    Supports:
    - US stocks: Uses yfinance
    - Korean stocks (.KS, .KQ): Uses pykrx + Naver scraping, with yfinance fallback
    """

    # Naver Finance URLs
    NAVER_FINANCE_URL = "https://finance.naver.com/item/main.naver?code={code}"
    NAVER_SISE_URL = "https://finance.naver.com/item/coinfo.naver?code={code}"

    def __init__(self, use_naver_fallback: bool = True):
        self.use_naver_fallback = use_naver_fallback and NAVER_SCRAPING_AVAILABLE

    def enrich(self, ticker: str) -> Dict[str, Any]:
        if self._is_korean_stock(ticker):
            data = self._enrich_korean_stock(ticker)
        else:
            data = self._enrich_us_stock(ticker)
        return data.to_dict()

    def enrich_as_dataclass(self, ticker: str) -> FundamentalData:
        if self._is_korean_stock(ticker):
            return self._enrich_korean_stock(ticker)
        else:
            return self._enrich_us_stock(ticker)

    def _is_korean_stock(self, ticker: str) -> bool:
        return ticker.endswith('.KS') or ticker.endswith('.KQ')

    def _extract_code(self, ticker: str) -> str:
        return ticker.split('.')[0]

    def _safe_get(self, data: Dict, key: str, default: Any = None) -> Any:
        import math
        value = data.get(key, default)
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return value

    def _enrich_us_stock(self, ticker: str) -> FundamentalData:
        logger.info(f"Fetching US stock fundamental data: {ticker}")
        data = FundamentalData(ticker=ticker)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info:
                logger.warning(f"No info available for {ticker}")
                return data
            data.pe_ratio = self._safe_get(info, 'trailingPE')
            data.forward_pe = self._safe_get(info, 'forwardPE')
            data.pb_ratio = self._safe_get(info, 'priceToBook')
            data.ps_ratio = self._safe_get(info, 'priceToSalesTrailing12Months')
            data.peg_ratio = self._safe_get(info, 'pegRatio')
            data.eps = self._safe_get(info, 'trailingEps')
            data.revenue = self._safe_get(info, 'totalRevenue')
            data.revenue_growth = self._safe_get(info, 'revenueGrowth')
            if data.revenue_growth is not None:
                data.revenue_growth = data.revenue_growth * 100
            data.profit_margin = self._safe_get(info, 'profitMargins')
            if data.profit_margin is not None:
                data.profit_margin = data.profit_margin * 100
            data.roe = self._safe_get(info, 'returnOnEquity')
            if data.roe is not None:
                data.roe = data.roe * 100
            data.roa = self._safe_get(info, 'returnOnAssets')
            if data.roa is not None:
                data.roa = data.roa * 100
            data.debt_to_equity = self._safe_get(info, 'debtToEquity')
            data.current_ratio = self._safe_get(info, 'currentRatio')
            data.quick_ratio = self._safe_get(info, 'quickRatio')
            data.dividend_yield = self._safe_get(info, 'dividendYield')
            if data.dividend_yield is not None:
                data.dividend_yield = data.dividend_yield * 100
            data.payout_ratio = self._safe_get(info, 'payoutRatio')
            if data.payout_ratio is not None:
                data.payout_ratio = data.payout_ratio * 100
            data.market_cap = self._safe_get(info, 'marketCap')
            data.enterprise_value = self._safe_get(info, 'enterpriseValue')
            data.sector = self._safe_get(info, 'sector')
            data.industry = self._safe_get(info, 'industry')
            data.description = self._safe_get(info, 'longBusinessSummary')
            data.name = self._safe_get(info, 'shortName') or self._safe_get(info, 'longName')
            data.currency = self._safe_get(info, 'currency', 'USD')
            logger.info(f"Successfully fetched fundamental data for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {ticker}: {e}")
        return data

    def _enrich_korean_stock(self, ticker: str) -> FundamentalData:
        logger.info(f"Fetching Korean stock fundamental data: {ticker}")
        code = self._extract_code(ticker)
        pykrx_data = FundamentalData(ticker=ticker)
        naver_data = FundamentalData(ticker=ticker)

        def _fetch_pykrx():
            if PYKRX_AVAILABLE:
                self._enrich_from_pykrx(pykrx_data, code)

        def _fetch_naver():
            if self.use_naver_fallback:
                self._enrich_from_naver(naver_data, code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            pykrx_future = executor.submit(_fetch_pykrx)
            naver_future = executor.submit(_fetch_naver)
            pykrx_future.result()
            naver_future.result()

        data = FundamentalData(ticker=ticker)
        for f in FundamentalData.__dataclass_fields__:
            if f in ("ticker", "last_updated"):
                continue
            pykrx_val = getattr(pykrx_data, f)
            naver_val = getattr(naver_data, f)
            merged = pykrx_val if pykrx_val is not None else naver_val
            if merged is not None:
                setattr(data, f, merged)

        self._enrich_korean_from_yfinance(data, ticker)
        return data

    def _enrich_from_pykrx(self, data: FundamentalData, code: str) -> None:
        try:
            from datetime import date, timedelta
            today = date.today()
            end_date = today
            start_date = end_date - timedelta(days=14)
            fundamental = pykrx_stock.get_market_fundamental_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                code
            )
            if not fundamental.empty:
                latest = fundamental.iloc[-1]
                if 'PER' in latest.index and latest['PER'] > 0:
                    data.pe_ratio = float(latest['PER'])
                if 'PBR' in latest.index and latest['PBR'] > 0:
                    data.pb_ratio = float(latest['PBR'])
                if 'EPS' in latest.index:
                    data.eps = float(latest['EPS'])
                if 'DIV' in latest.index and latest['DIV'] > 0:
                    data.dividend_yield = float(latest['DIV'])
            cap_data = pykrx_stock.get_market_cap_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                code
            )
            if not cap_data.empty:
                latest_cap = cap_data.iloc[-1]
                if '시가총액' in latest_cap.index:
                    data.market_cap = float(latest_cap['시가총액'])
            try:
                data.name = pykrx_stock.get_market_ticker_name(code)
            except Exception:
                pass
            logger.debug(f"pykrx data fetched for {code}")
        except Exception as e:
            logger.warning("pykrx fetch failed for %s: %s", code, str(e))

    def _enrich_from_naver(self, data: FundamentalData, code: str) -> None:
        try:
            url = self.NAVER_FINANCE_URL.format(code=code)
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            self._parse_naver_per_table(data, soup)
            self._parse_naver_metrics(data, soup)
            self._parse_naver_sector(data, soup)
            self._parse_naver_description(data, code)
            logger.debug(f"Naver data fetched for {code}")
        except Exception as e:
            logger.warning(f"Naver Finance scraping failed for {code}: {e}")

    def _parse_naver_per_table(self, data: FundamentalData, soup) -> None:
        try:
            per_table = soup.select_one('#tab_con1 table.per_table')
            if not per_table:
                return
            rows = per_table.select('tr')
            for row in rows:
                label_text = row.get_text(strip=True)
                ems = row.select('em')
                if not ems:
                    continue
                if '배당수익률' in label_text:
                    div_text = ems[0].get_text(strip=True).replace('%', '').replace(',', '')
                    try:
                        div_val = float(div_text) if div_text and div_text != '-' else None
                        if div_val is not None and data.dividend_yield is None:
                            data.dividend_yield = div_val
                    except ValueError:
                        pass
                    continue
                if len(ems) < 2:
                    continue
                val1_text = ems[0].get_text(strip=True).replace(',', '')
                val2_text = ems[1].get_text(strip=True).replace(',', '')
                try:
                    val1 = float(val1_text) if val1_text and val1_text != '-' else None
                    val2 = float(val2_text) if val2_text and val2_text != '-' else None
                except ValueError:
                    val1, val2 = None, None
                if '추정PER' in label_text:
                    if val1 is not None and data.forward_pe is None:
                        data.forward_pe = val1
                elif 'PER' in label_text and 'EPS' in label_text:
                    if val1 is not None and data.pe_ratio is None:
                        data.pe_ratio = val1
                    if val2 is not None and data.eps is None:
                        data.eps = val2
                elif 'PBR' in label_text and 'BPS' in label_text:
                    if val1 is not None and data.pb_ratio is None:
                        data.pb_ratio = val1
        except Exception as e:
            logger.debug(f"Error parsing Naver per_table: {e}")

    def _parse_naver_metrics(self, data: FundamentalData, soup) -> None:
        try:
            tables = soup.select('table.tb_type1')
            for table in tables:
                rows = table.select('tr')
                for row in rows:
                    header = row.select_one('th')
                    value_td = row.select_one('td')
                    if not header or not value_td:
                        continue
                    header_text = header.get_text(strip=True)
                    value_text = value_td.get_text(strip=True).replace(',', '').replace('%', '')
                    try:
                        value = float(value_text) if value_text and value_text != 'N/A' else None
                    except ValueError:
                        value = None
                    if value is None:
                        continue
                    if 'ROE' in header_text and data.roe is None:
                        data.roe = value
                    elif 'ROA' in header_text and data.roa is None:
                        data.roa = value
                    elif '부채비율' in header_text and data.debt_to_equity is None:
                        data.debt_to_equity = value
                    elif '유동비율' in header_text and data.current_ratio is None:
                        data.current_ratio = value
                    elif '영업이익률' in header_text and data.profit_margin is None:
                        data.profit_margin = value
                    elif 'PSR' in header_text and data.ps_ratio is None:
                        data.ps_ratio = value
        except Exception as e:
            logger.debug(f"Error parsing Naver metrics: {e}")

    def _parse_naver_sector(self, data: FundamentalData, soup) -> None:
        try:
            info_section = soup.select_one('div.wrap_company')
            if info_section:
                sector_link = info_section.select_one('a[href*="sise_group"]')
                if sector_link and data.sector is None:
                    data.sector = sector_link.get_text(strip=True)
                industry_span = info_section.select_one('span.sub_tit')
                if industry_span and data.industry is None:
                    data.industry = industry_span.get_text(strip=True)
        except Exception as e:
            logger.debug(f"Error parsing Naver sector: {e}")

    def _parse_naver_description(self, data: FundamentalData, code: str) -> None:
        try:
            if data.description is not None:
                return
            url = f"https://finance.naver.com/item/coinfo.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            summary_div = soup.select_one('div.summary_info')
            if summary_div:
                data.description = summary_div.get_text(strip=True)[:500]
        except Exception as e:
            logger.debug(f"Error fetching Naver description: {e}")

    def _enrich_korean_from_yfinance(self, data: FundamentalData, ticker: str) -> None:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info:
                return
            if data.pe_ratio is None:
                data.pe_ratio = self._safe_get(info, 'trailingPE')
            if data.forward_pe is None:
                data.forward_pe = self._safe_get(info, 'forwardPE')
            if data.pb_ratio is None:
                data.pb_ratio = self._safe_get(info, 'priceToBook')
            if data.ps_ratio is None:
                data.ps_ratio = self._safe_get(info, 'priceToSalesTrailing12Months')
            if data.peg_ratio is None:
                data.peg_ratio = self._safe_get(info, 'pegRatio')
            if data.eps is None:
                data.eps = self._safe_get(info, 'trailingEps')
            if data.revenue is None:
                data.revenue = self._safe_get(info, 'totalRevenue')
            if data.revenue_growth is None:
                growth = self._safe_get(info, 'revenueGrowth')
                if growth is not None:
                    data.revenue_growth = growth * 100
            if data.profit_margin is None:
                margin = self._safe_get(info, 'profitMargins')
                if margin is not None:
                    data.profit_margin = margin * 100
            if data.roe is None:
                roe = self._safe_get(info, 'returnOnEquity')
                if roe is not None:
                    data.roe = roe * 100
            if data.roa is None:
                roa = self._safe_get(info, 'returnOnAssets')
                if roa is not None:
                    data.roa = roa * 100
            if data.debt_to_equity is None:
                data.debt_to_equity = self._safe_get(info, 'debtToEquity')
            if data.current_ratio is None:
                data.current_ratio = self._safe_get(info, 'currentRatio')
            if data.quick_ratio is None:
                data.quick_ratio = self._safe_get(info, 'quickRatio')
            if data.dividend_yield is None:
                div_yield = self._safe_get(info, 'dividendYield')
                if div_yield is not None:
                    converted = div_yield * 100
                    data.dividend_yield = div_yield if converted > 50 else converted
            if data.payout_ratio is None:
                payout = self._safe_get(info, 'payoutRatio')
                if payout is not None:
                    data.payout_ratio = payout * 100
            if data.market_cap is None:
                data.market_cap = self._safe_get(info, 'marketCap')
            if data.enterprise_value is None:
                data.enterprise_value = self._safe_get(info, 'enterpriseValue')
            if data.sector is None:
                data.sector = self._safe_get(info, 'sector')
            if data.industry is None:
                data.industry = self._safe_get(info, 'industry')
            if data.description is None:
                data.description = self._safe_get(info, 'longBusinessSummary')
            if data.name is None:
                data.name = self._safe_get(info, 'shortName') or self._safe_get(info, 'longName')
            data.currency = self._safe_get(info, 'currency', 'KRW')
            logger.debug(f"yfinance fallback data fetched for {ticker}")
        except Exception as e:
            logger.warning(f"yfinance fallback failed for {ticker}: {e}")


def enrich_fundamental(ticker: str) -> Dict[str, Any]:
    """Convenience function to fetch fundamental data for a stock."""
    enricher = FundamentalEnricher()
    return enricher.enrich(ticker)
