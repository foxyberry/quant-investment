"""
News Provider Interface
뉴스 제공자 인터페이스

Usage:
    from news.provider import NewsProvider, NewsItem, NewsSentiment
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Sentiment(Enum):
    """감성 분류"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class NewsItem:
    """뉴스 아이템"""
    title: str
    summary: Optional[str]
    url: str
    source: str
    published_at: datetime
    ticker: Optional[str] = None

    # Sentiment
    sentiment: Optional[Sentiment] = None
    sentiment_score: Optional[float] = None  # -1.0 to 1.0

    # Provider info
    provider: Optional[str] = None  # "finnhub", "marketaux"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "ticker": self.ticker,
            "sentiment": self.sentiment.value if self.sentiment else None,
            "sentiment_score": self.sentiment_score,
            "provider": self.provider,
        }

    @property
    def is_positive(self) -> bool:
        return self.sentiment == Sentiment.POSITIVE or (
            self.sentiment_score is not None and self.sentiment_score > 0.2
        )

    @property
    def is_negative(self) -> bool:
        return self.sentiment == Sentiment.NEGATIVE or (
            self.sentiment_score is not None and self.sentiment_score < -0.2
        )


@dataclass
class NewsSentiment:
    """종목별 뉴스 감성 요약"""
    ticker: str
    total_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_sentiment_score: float
    latest_news: List[NewsItem] = field(default_factory=list)

    @property
    def sentiment_ratio(self) -> float:
        """긍정/부정 비율 (-1 to 1)"""
        if self.total_count == 0:
            return 0
        return (self.positive_count - self.negative_count) / self.total_count

    @property
    def overall_sentiment(self) -> Sentiment:
        """전체 감성"""
        if self.avg_sentiment_score > 0.1:
            return Sentiment.POSITIVE
        elif self.avg_sentiment_score < -0.1:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "total_count": self.total_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "avg_sentiment_score": self.avg_sentiment_score,
            "sentiment_ratio": self.sentiment_ratio,
            "overall_sentiment": self.overall_sentiment.value,
            "latest_news": [n.to_dict() for n in self.latest_news[:5]],
        }


class NewsProvider(Protocol):
    """뉴스 제공자 프로토콜"""

    @property
    def name(self) -> str:
        """제공자 이름"""
        ...

    def get_news(
        self,
        ticker: str,
        limit: int = 10,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NewsItem]:
        """종목 뉴스 조회"""
        ...

    def get_sentiment(self, ticker: str) -> Optional[NewsSentiment]:
        """종목 감성 분석"""
        ...


class BaseNewsProvider(ABC):
    """뉴스 제공자 기본 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_news(
        self,
        ticker: str,
        limit: int = 10,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NewsItem]:
        pass

    def get_sentiment(self, ticker: str) -> Optional[NewsSentiment]:
        """뉴스 기반 감성 분석"""
        news_items = self.get_news(ticker, limit=50)

        if not news_items:
            return None

        positive = 0
        negative = 0
        neutral = 0
        scores = []

        for item in news_items:
            if item.sentiment == Sentiment.POSITIVE:
                positive += 1
            elif item.sentiment == Sentiment.NEGATIVE:
                negative += 1
            else:
                neutral += 1

            if item.sentiment_score is not None:
                scores.append(item.sentiment_score)

        avg_score = sum(scores) / len(scores) if scores else 0

        return NewsSentiment(
            ticker=ticker,
            total_count=len(news_items),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            avg_sentiment_score=avg_score,
            latest_news=news_items[:5],
        )

    def is_configured(self) -> bool:
        """API 키 설정 여부"""
        return self.api_key is not None and len(self.api_key) > 0
