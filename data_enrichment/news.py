"""
News Enrichment Module

Provides news enrichment for stocks by integrating with the existing
news module (finnhub, marketaux, aggregator).

Usage:
    from data_enrichment.news import NewsEnricher

    enricher = NewsEnricher(max_articles=10, days=7)
    result = enricher.enrich("AAPL", name="Apple Inc.")

    # Result format:
    # {
    #     'articles': [...],
    #     'article_count': 10,
    #     'sentiment_summary': 'positive',
    # }
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
        """
        Initialize the NewsEnricher.

        Args:
            max_articles: Maximum number of articles to fetch (default: 10)
            days: Number of days to look back for news (default: 7)
            finnhub_key: Optional Finnhub API key (uses env var if not provided)
            marketaux_key: Optional Marketaux API key (uses env var if not provided)
        """
        self.max_articles = max_articles
        self.days = days
        self.logger = logging.getLogger(__name__)

        # Initialize the news aggregator with optional API keys
        self._aggregator = NewsAggregator(
            finnhub_key=finnhub_key,
            marketaux_key=marketaux_key,
        )

    def enrich(self, ticker: str, name: str = None) -> Dict[str, Any]:
        """
        Fetch recent news for the stock.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
            name: Optional company name (currently unused, reserved for future)

        Returns:
            Dictionary containing:
                - articles: List of article dictionaries
                - article_count: Number of articles fetched
                - sentiment_summary: Overall sentiment ('positive', 'negative', 'neutral')
        """
        result = {
            'articles': [],
            'article_count': 0,
            'sentiment_summary': 'neutral',
        }

        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=self.days)

            # Fetch news from aggregator
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

            # Transform news items to article format
            articles = []
            sentiment_scores = []
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}

            for item in news_items:
                article = self._transform_news_item(item)
                articles.append(article)

                # Collect sentiment data for summary
                if item.sentiment_score is not None:
                    sentiment_scores.append(item.sentiment_score)

                if item.sentiment:
                    sentiment_counts[item.sentiment.value] += 1
                else:
                    sentiment_counts['neutral'] += 1

            # Calculate overall sentiment
            sentiment_summary = self._calculate_sentiment_summary(
                sentiment_scores, sentiment_counts
            )

            result['articles'] = articles
            result['article_count'] = len(articles)
            result['sentiment_summary'] = sentiment_summary

            self.logger.debug(
                f"Fetched {len(articles)} articles for {ticker}, "
                f"sentiment: {sentiment_summary}"
            )

        except Exception as e:
            self.logger.error(f"Error enriching news for {ticker}: {e}")

        return result

    def _transform_news_item(self, item) -> Dict[str, Any]:
        """
        Transform a NewsItem to the enrichment article format.

        Args:
            item: NewsItem from the news module

        Returns:
            Dictionary with article data
        """
        return {
            'title': item.title,
            'source': item.source,
            'date': item.published_at.strftime("%Y-%m-%d %H:%M:%S"),
            'summary': item.summary or '',
            'sentiment': item.sentiment.value if item.sentiment else 'neutral',
            'url': item.url,
        }

    def _calculate_sentiment_summary(
        self,
        scores: List[float],
        counts: Dict[str, int]
    ) -> str:
        """
        Calculate overall sentiment summary.

        Uses a combination of average sentiment score and sentiment counts
        to determine the overall sentiment.

        Args:
            scores: List of sentiment scores (-1.0 to 1.0)
            counts: Dictionary of sentiment counts

        Returns:
            Overall sentiment string ('positive', 'negative', 'neutral')
        """
        # If we have scores, use the average
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score > 0.1:
                return 'positive'
            elif avg_score < -0.1:
                return 'negative'
            return 'neutral'

        # Fall back to count-based analysis
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
        """
        Get list of configured news providers.

        Returns:
            List of provider names
        """
        return self._aggregator.get_providers()

    def is_configured(self) -> bool:
        """
        Check if at least one news provider is configured.

        Returns:
            True if at least one provider is available
        """
        return len(self._aggregator.get_providers()) > 0
