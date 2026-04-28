"""
News Enrichment Module
Canonical location. Moved from data_enrichment/news.py.

Provides news enrichment for stocks by integrating with the existing
news module (finnhub, marketaux, aggregator).

Usage:
    from data_sources.news.aggregator import NewsEnricher

    enricher = NewsEnricher(max_articles=10, days=7)
    result = enricher.enrich("AAPL", name="Apple Inc.")
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from news.aggregator import NewsAggregator
from news.provider import Sentiment


class NewsEnricher:
    """
    News enricher for stocks.

    Integrates with the existing news module to fetch and enrich
    stock data with recent news articles and sentiment analysis.
    """

    def __init__(
        self,
        max_articles: int = 10,
        days: int = 7,
        finnhub_key: Optional[str] = None,
        marketaux_key: Optional[str] = None,
    ):
        self.max_articles = max_articles
        self.days = days
        self.logger = logging.getLogger(__name__)
        self._aggregator = NewsAggregator(
            finnhub_key=finnhub_key,
            marketaux_key=marketaux_key,
        )

    def enrich(self, ticker: str, name: str = None) -> Dict[str, Any]:
        result = {
            'articles': [],
            'article_count': 0,
            'sentiment_summary': 'neutral',
        }
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=self.days)
            news_items = self._aggregator.get_news(
                ticker=ticker,
                limit=self.max_articles,
                from_date=from_date,
                to_date=to_date,
                deduplicate=True,
            )
            if not news_items:
                self.logger.debug(f"No news found for {ticker}")
                return result

            articles = []
            sentiment_scores = []
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}

            for item in news_items:
                article = self._transform_news_item(item)
                articles.append(article)
                if item.sentiment_score is not None:
                    sentiment_scores.append(item.sentiment_score)
                if item.sentiment:
                    sentiment_counts[item.sentiment.value] += 1
                else:
                    sentiment_counts['neutral'] += 1

            sentiment_summary = self._calculate_sentiment_summary(sentiment_scores, sentiment_counts)
            result['articles'] = articles
            result['article_count'] = len(articles)
            result['sentiment_summary'] = sentiment_summary
            self.logger.debug(f"Fetched {len(articles)} articles for {ticker}, sentiment: {sentiment_summary}")
        except Exception as e:
            self.logger.error(f"Error enriching news for {ticker}: {e}")
        return result

    def _transform_news_item(self, item) -> Dict[str, Any]:
        return {
            'title': item.title,
            'source': item.source,
            'date': item.published_at.strftime("%Y-%m-%d %H:%M:%S"),
            'summary': item.summary or '',
            'sentiment': item.sentiment.value if item.sentiment else 'neutral',
            'url': item.url,
        }

    def _calculate_sentiment_summary(self, scores: List[float], counts: Dict[str, int]) -> str:
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score > 0.1:
                return 'positive'
            elif avg_score < -0.1:
                return 'negative'
            return 'neutral'
        total = sum(counts.values())
        if total == 0:
            return 'neutral'
        positive_ratio = counts['positive'] / total
        negative_ratio = counts['negative'] / total
        if positive_ratio > negative_ratio and positive_ratio > 0.4:
            return 'positive'
        elif negative_ratio > positive_ratio and negative_ratio > 0.4:
            return 'negative'
        return 'neutral'

    def get_providers(self) -> List[str]:
        return self._aggregator.get_providers()

    def is_configured(self) -> bool:
        return len(self._aggregator.get_providers()) > 0
