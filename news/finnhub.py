"""
Finnhub News Provider
Finnhub API 뉴스 제공자

Usage:
    from news.finnhub import FinnhubProvider

    provider = FinnhubProvider(api_key="your_api_key")
    news = provider.get_news("AAPL")

API Docs: https://finnhub.io/docs/api/company-news
Free tier: 60 calls/minute
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .provider import BaseNewsProvider, NewsItem, Sentiment, NewsSentiment


class FinnhubProvider(BaseNewsProvider):
    """Finnhub 뉴스 제공자"""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Finnhub API 키 (없으면 환경변수 FINNHUB_API_KEY 사용)
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required for FinnhubProvider")

        api_key = api_key or os.environ.get("FINNHUB_API_KEY")
        super().__init__(api_key)
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "finnhub"

    def get_news(
        self,
        ticker: str,
        limit: int = 10,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NewsItem]:
        """
        종목 뉴스 조회

        Args:
            ticker: 종목 코드 (예: AAPL, MSFT)
            limit: 최대 뉴스 수
            from_date: 시작 날짜
            to_date: 종료 날짜

        Returns:
            뉴스 아이템 목록
        """
        if not self.is_configured():
            self.logger.warning("Finnhub API key not configured")
            return []

        # Default date range: last 7 days
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=7)

        try:
            response = requests.get(
                f"{self.BASE_URL}/company-news",
                params={
                    "symbol": ticker.upper().replace(".KS", "").replace(".KQ", ""),
                    "from": from_date.strftime("%Y-%m-%d"),
                    "to": to_date.strftime("%Y-%m-%d"),
                    "token": self.api_key,
                },
                timeout=10
            )

            if response.status_code != 200:
                self.logger.error(f"Finnhub API error: {response.status_code}")
                return []

            data = response.json()

            if not isinstance(data, list):
                return []

            news_items = []
            for item in data[:limit]:
                news_item = self._parse_news_item(item, ticker)
                if news_item:
                    news_items.append(news_item)

            return news_items

        except Exception as e:
            self.logger.error(f"Finnhub fetch error: {e}")
            return []

    def _parse_news_item(self, data: Dict[str, Any], ticker: str) -> Optional[NewsItem]:
        """뉴스 아이템 파싱"""
        try:
            # Parse datetime from Unix timestamp
            published_at = datetime.fromtimestamp(data.get("datetime", 0))

            # Finnhub doesn't provide sentiment directly
            # We'll use a simple keyword-based approach
            headline = data.get("headline", "")
            summary = data.get("summary", "")
            sentiment, score = self._analyze_sentiment(headline + " " + summary)

            return NewsItem(
                title=headline,
                summary=summary[:500] if summary else None,
                url=data.get("url", ""),
                source=data.get("source", "Unknown"),
                published_at=published_at,
                ticker=ticker,
                sentiment=sentiment,
                sentiment_score=score,
                provider=self.name,
                raw_data=data,
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse news item: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> tuple[Optional[Sentiment], Optional[float]]:
        """
        간단한 키워드 기반 감성 분석

        Note: 실제 프로덕션에서는 NLP 라이브러리나 API 사용 권장
        """
        if not text:
            return None, None

        text_lower = text.lower()

        # Positive keywords
        positive_words = [
            "surge", "jump", "gain", "rise", "up", "high", "record", "beat",
            "exceed", "strong", "growth", "profit", "success", "bullish",
            "upgrade", "buy", "outperform", "positive", "boost", "rally"
        ]

        # Negative keywords
        negative_words = [
            "fall", "drop", "decline", "down", "low", "miss", "loss", "weak",
            "bearish", "downgrade", "sell", "underperform", "negative", "cut",
            "crash", "plunge", "concern", "risk", "warning", "fail"
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return Sentiment.NEUTRAL, 0.0

        score = (positive_count - negative_count) / max(total, 1)
        score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]

        if score > 0.2:
            return Sentiment.POSITIVE, score
        elif score < -0.2:
            return Sentiment.NEGATIVE, score
        else:
            return Sentiment.NEUTRAL, score

    def get_market_news(self, category: str = "general", limit: int = 10) -> List[NewsItem]:
        """
        시장 전체 뉴스 조회

        Args:
            category: 카테고리 (general, forex, crypto, merger)
            limit: 최대 뉴스 수
        """
        if not self.is_configured():
            return []

        try:
            response = requests.get(
                f"{self.BASE_URL}/news",
                params={
                    "category": category,
                    "token": self.api_key,
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()
            news_items = []

            for item in data[:limit]:
                news_item = self._parse_news_item(item, "MARKET")
                if news_item:
                    news_items.append(news_item)

            return news_items

        except Exception as e:
            self.logger.error(f"Finnhub market news error: {e}")
            return []
