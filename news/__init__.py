"""
News Feed Module
뉴스 피드 모듈

Supports multiple news providers:
- Finnhub (60 calls/min free)
- Marketaux (100 calls/day free)

Usage:
    from news import NewsAggregator, get_news, get_sentiment

    # Using aggregator (recommended)
    aggregator = NewsAggregator()
    news = aggregator.get_news("AAPL")
    sentiment = aggregator.get_sentiment("AAPL")
    print(aggregator.summary("AAPL"))

    # Using convenience functions
    news = get_news("AAPL", limit=10)
    sentiment = get_sentiment("AAPL")

    # Using individual providers
    from news import FinnhubProvider, MarketauxProvider

    finnhub = FinnhubProvider(api_key="your_key")
    news = finnhub.get_news("AAPL")

Environment Variables:
    FINNHUB_API_KEY: Finnhub API key
    MARKETAUX_API_KEY: Marketaux API key
"""

from .provider import (
    NewsItem, NewsSentiment, Sentiment,
    NewsProvider, BaseNewsProvider
)
from .finnhub import FinnhubProvider
from .marketaux import MarketauxProvider
from .aggregator import (
    NewsAggregator,
    get_news, get_sentiment
)

__all__ = [
    # Data classes
    'NewsItem', 'NewsSentiment', 'Sentiment',

    # Interfaces
    'NewsProvider', 'BaseNewsProvider',

    # Providers
    'FinnhubProvider', 'MarketauxProvider',

    # Aggregator
    'NewsAggregator',

    # Convenience functions
    'get_news', 'get_sentiment',
]
