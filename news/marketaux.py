"""
Marketaux News Provider
Marketaux API 뉴스 제공자

Usage:
    from news.marketaux import MarketauxProvider

    provider = MarketauxProvider(api_key="your_api_key")
    news = provider.get_news("AAPL")

API Docs: https://www.marketaux.com/documentation
Free tier: 100 requests/day
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


class MarketauxProvider(BaseNewsProvider):
    """Marketaux 뉴스 제공자"""

    BASE_URL = "https://api.marketaux.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Marketaux API 키 (없으면 환경변수 MARKETAUX_API_KEY 사용)
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required for MarketauxProvider")

        api_key = api_key or os.environ.get("MARKETAUX_API_KEY")
        super().__init__(api_key)
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "marketaux"

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
            self.logger.warning("Marketaux API key not configured")
            return []

        # Clean ticker symbol
        clean_ticker = ticker.upper().replace(".KS", "").replace(".KQ", "")

        params = {
            "api_token": self.api_key,
            "symbols": clean_ticker,
            "limit": min(limit, 50),  # Marketaux max is 50
            "language": "en",
        }

        if from_date:
            params["published_after"] = from_date.strftime("%Y-%m-%dT%H:%M")
        if to_date:
            params["published_before"] = to_date.strftime("%Y-%m-%dT%H:%M")

        try:
            response = requests.get(
                f"{self.BASE_URL}/news/all",
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                self.logger.error(f"Marketaux API error: {response.status_code}")
                return []

            data = response.json()

            if "data" not in data:
                return []

            news_items = []
            for item in data["data"][:limit]:
                news_item = self._parse_news_item(item, ticker)
                if news_item:
                    news_items.append(news_item)

            return news_items

        except Exception as e:
            self.logger.error(f"Marketaux fetch error: {e}")
            return []

    def _parse_news_item(self, data: Dict[str, Any], ticker: str) -> Optional[NewsItem]:
        """뉴스 아이템 파싱"""
        try:
            # Parse datetime
            published_str = data.get("published_at", "")
            if published_str:
                # Handle ISO format with timezone
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            else:
                published_at = datetime.now()

            # Marketaux provides sentiment
            sentiment_data = data.get("entities", [])
            sentiment, score = self._extract_sentiment(sentiment_data, ticker)

            return NewsItem(
                title=data.get("title", ""),
                summary=data.get("description", "")[:500] if data.get("description") else None,
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

    def _extract_sentiment(
        self,
        entities: List[Dict],
        ticker: str
    ) -> tuple[Optional[Sentiment], Optional[float]]:
        """
        Marketaux 엔티티에서 감성 추출

        Marketaux는 각 엔티티(종목)별로 sentiment_score를 제공
        """
        if not entities:
            return None, None

        clean_ticker = ticker.upper().replace(".KS", "").replace(".KQ", "")

        for entity in entities:
            if entity.get("symbol", "").upper() == clean_ticker:
                score = entity.get("sentiment_score")
                if score is not None:
                    # Marketaux score is already -1 to 1
                    if score > 0.2:
                        return Sentiment.POSITIVE, score
                    elif score < -0.2:
                        return Sentiment.NEGATIVE, score
                    else:
                        return Sentiment.NEUTRAL, score

        # Fallback: use highlights_sentiment if available
        for entity in entities:
            highlights = entity.get("highlights", [])
            if highlights:
                scores = [h.get("sentiment") for h in highlights if h.get("sentiment")]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    if avg_score > 0.2:
                        return Sentiment.POSITIVE, avg_score
                    elif avg_score < -0.2:
                        return Sentiment.NEGATIVE, avg_score
                    return Sentiment.NEUTRAL, avg_score

        return None, None

    def get_market_news(
        self,
        countries: str = "us",
        limit: int = 10
    ) -> List[NewsItem]:
        """
        시장 전체 뉴스 조회

        Args:
            countries: 국가 코드 (us, kr, jp 등)
            limit: 최대 뉴스 수
        """
        if not self.is_configured():
            return []

        try:
            response = requests.get(
                f"{self.BASE_URL}/news/all",
                params={
                    "api_token": self.api_key,
                    "countries": countries,
                    "limit": min(limit, 50),
                    "language": "en",
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()

            if "data" not in data:
                return []

            news_items = []
            for item in data["data"][:limit]:
                news_item = self._parse_news_item(item, "MARKET")
                if news_item:
                    news_items.append(news_item)

            return news_items

        except Exception as e:
            self.logger.error(f"Marketaux market news error: {e}")
            return []

    def search_news(
        self,
        keywords: str,
        limit: int = 10
    ) -> List[NewsItem]:
        """
        키워드 기반 뉴스 검색

        Args:
            keywords: 검색 키워드
            limit: 최대 뉴스 수
        """
        if not self.is_configured():
            return []

        try:
            response = requests.get(
                f"{self.BASE_URL}/news/all",
                params={
                    "api_token": self.api_key,
                    "search": keywords,
                    "limit": min(limit, 50),
                    "language": "en",
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()

            if "data" not in data:
                return []

            news_items = []
            for item in data["data"][:limit]:
                news_item = self._parse_news_item(item, "SEARCH")
                if news_item:
                    news_items.append(news_item)

            return news_items

        except Exception as e:
            self.logger.error(f"Marketaux search error: {e}")
            return []
