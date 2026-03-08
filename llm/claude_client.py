"""
Claude API Client for Stock Analysis

This module provides a ClaudeAnalyzer class that uses the Anthropic API
to analyze stocks and provide investment recommendations.
"""

import os
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Stock analysis result from Claude"""
    ticker: str
    valuation_score: float  # 1-10
    risk_score: float  # 1-10
    entry_recommendation: str  # 'BUY', 'WAIT', 'AVOID'
    reasoning: str
    key_risks: List[str]
    catalysts: List[str]
    raw_response: Optional[str] = None


class ClaudeAnalyzerError(Exception):
    """Base exception for ClaudeAnalyzer errors"""
    pass


class APIKeyMissingError(ClaudeAnalyzerError):
    """Raised when API key is not provided"""
    pass


class APICallError(ClaudeAnalyzerError):
    """Raised when API call fails"""
    pass


class ResponseParseError(ClaudeAnalyzerError):
    """Raised when response parsing fails"""
    pass


class ClaudeAnalyzer:
    """
    Claude-based stock analyzer using Anthropic API.

    Provides methods to analyze individual stocks or batches of stocks
    using Claude's reasoning capabilities.

    Example:
        analyzer = ClaudeAnalyzer()
        result = analyzer.analyze_stock(
            ticker="AAPL",
            name="Apple Inc.",
            current_price=175.50,
            ma_240=165.30,
            technical={"rsi": 55, "macd_histogram": 0.5},
            fundamental={"pe_ratio": 28, "market_cap": "2.8T"}
        )
        print(result.entry_recommendation)
    """

    # System prompt for stock analysis
    SYSTEM_PROMPT = """You are an expert quantitative analyst and investment advisor.
Your role is to analyze stocks based on technical and fundamental data provided,
and give structured investment recommendations.

Always respond in valid JSON format with the following structure:
{
    "valuation_score": <float 1-10>,
    "risk_score": <float 1-10>,
    "entry_recommendation": "<BUY|WAIT|AVOID>",
    "reasoning": "<detailed analysis reasoning>",
    "key_risks": ["<risk1>", "<risk2>", ...],
    "catalysts": ["<catalyst1>", "<catalyst2>", ...]
}

Scoring Guidelines:
- valuation_score: 1 = extremely overvalued, 10 = extremely undervalued
- risk_score: 1 = very low risk, 10 = very high risk
- entry_recommendation:
  - BUY: Strong opportunity, favorable risk/reward
  - WAIT: Potential but timing not ideal, wait for better entry
  - AVOID: Too risky or overvalued

Be concise but thorough in your reasoning. Focus on actionable insights."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = 1500,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Claude analyzer.

        Automatically detects provider based on available API keys.
        Priority: ANTHROPIC_API_KEY > OPENAI_API_KEY.

        Args:
            api_key: API key (defaults to env var based on provider detection)
            model: Model to use (defaults based on provider)
            max_tokens: Max tokens for response
            max_retries: Maximum number of retry attempts for transient failures
            retry_delay: Base delay between retries in seconds (exponential backoff)
        """
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if api_key:
            # Explicit key provided — assume anthropic unless only openai key matches
            self.api_key = api_key
            self._provider = "anthropic"
        elif anthropic_key:
            self.api_key = anthropic_key
            self._provider = "anthropic"
        elif openai_key:
            self.api_key = openai_key
            self._provider = "openai"
        else:
            raise APIKeyMissingError(
                "No AI API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
            )

        default_models = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
        }
        self.model = model or default_models[self._provider]
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None

    @property
    def client(self):
        """Lazy initialization of API client based on provider"""
        if self._client is None:
            if self._provider == "openai":
                try:
                    import openai
                    self._client = openai.OpenAI(api_key=self.api_key)
                    logger.debug(f"Initialized OpenAI client with model: {self.model}")
                except ImportError:
                    raise ImportError(
                        "openai package not installed. Run: pip install openai"
                    )
            else:
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=self.api_key)
                    logger.debug(f"Initialized Anthropic client with model: {self.model}")
                except ImportError:
                    raise ImportError(
                        "anthropic package not installed. Run: pip install anthropic"
                    )
        return self._client

    # Language instructions appended to system prompt per locale
    LOCALE_INSTRUCTIONS = {
        "ko": "\n\nIMPORTANT: Write ALL text values (reasoning, key_risks, catalysts) in Korean. JSON keys must remain in English.",
        "zh": "\n\nIMPORTANT: Write ALL text values (reasoning, key_risks, catalysts) in Chinese. JSON keys must remain in English.",
    }

    def analyze_stock(
        self,
        ticker: str,
        name: str,
        current_price: float,
        ma_240: float,
        technical: dict,
        fundamental: dict,
        news: dict = None,
        locale: str = None
    ) -> AnalysisResult:
        """
        Analyze a single stock using AI.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            name: Company name (e.g., "Apple Inc.")
            current_price: Current stock price
            ma_240: 240-day moving average
            technical: Technical indicators dict (e.g., {"rsi": 55, "macd": 0.5})
            fundamental: Fundamental data dict (e.g., {"pe_ratio": 28})
            news: News data dict (optional, e.g., {"sentiment": "positive", "headlines": [...]})
            locale: Response language locale (e.g., "ko", "zh"). None or "en" = English.

        Returns:
            AnalysisResult with valuation, risk, and recommendation

        Raises:
            APICallError: If API call fails after retries
            ResponseParseError: If response cannot be parsed
        """
        prompt = self._build_analysis_prompt(
            ticker=ticker,
            name=name,
            current_price=current_price,
            ma_240=ma_240,
            technical=technical,
            fundamental=fundamental,
            news=news
        )

        logger.info(f"Analyzing stock: {ticker}")
        logger.debug(f"Analysis prompt for {ticker}: {prompt[:200]}...")

        system = self.SYSTEM_PROMPT
        if locale and locale in self.LOCALE_INSTRUCTIONS:
            system += self.LOCALE_INSTRUCTIONS[locale]

        response = self._call_claude(prompt, system=system)

        return self._parse_analysis_response(ticker, response)

    def analyze_batch(
        self,
        stocks: List[dict]
    ) -> List[AnalysisResult]:
        """
        Analyze multiple stocks sequentially.

        Args:
            stocks: List of stock profiles with all required data.
                    Each dict should have keys: ticker, name, current_price,
                    ma_240, technical, fundamental, and optionally news.

        Returns:
            List of AnalysisResult for each stock

        Example:
            stocks = [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "current_price": 175.50,
                    "ma_240": 165.30,
                    "technical": {"rsi": 55},
                    "fundamental": {"pe_ratio": 28}
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corp.",
                    "current_price": 380.00,
                    "ma_240": 360.00,
                    "technical": {"rsi": 60},
                    "fundamental": {"pe_ratio": 35}
                }
            ]
            results = analyzer.analyze_batch(stocks)
        """
        results = []
        total = len(stocks)

        logger.info(f"Starting batch analysis of {total} stocks")

        for idx, stock in enumerate(stocks, 1):
            ticker = stock.get("ticker", "UNKNOWN")
            try:
                logger.info(f"Processing {idx}/{total}: {ticker}")
                result = self.analyze_stock(
                    ticker=stock["ticker"],
                    name=stock["name"],
                    current_price=stock["current_price"],
                    ma_240=stock["ma_240"],
                    technical=stock["technical"],
                    fundamental=stock["fundamental"],
                    news=stock.get("news")
                )
                results.append(result)
            except (APICallError, ResponseParseError) as e:
                logger.error(f"Failed to analyze {ticker}: {e}")
                # Create a failed result
                results.append(AnalysisResult(
                    ticker=ticker,
                    valuation_score=0.0,
                    risk_score=10.0,
                    entry_recommendation="AVOID",
                    reasoning=f"Analysis failed: {str(e)}",
                    key_risks=["Analysis error"],
                    catalysts=[],
                    raw_response=None
                ))
            except KeyError as e:
                logger.error(f"Missing required field for {ticker}: {e}")
                results.append(AnalysisResult(
                    ticker=ticker,
                    valuation_score=0.0,
                    risk_score=10.0,
                    entry_recommendation="AVOID",
                    reasoning=f"Missing required data field: {str(e)}",
                    key_risks=["Incomplete data"],
                    catalysts=[],
                    raw_response=None
                ))

        logger.info(f"Batch analysis complete. Processed {len(results)} stocks.")
        return results

    def _build_analysis_prompt(
        self,
        ticker: str,
        name: str,
        current_price: float,
        ma_240: float,
        technical: dict,
        fundamental: dict,
        news: dict = None
    ) -> str:
        """Build the analysis prompt from stock data"""
        price_vs_ma = ((current_price - ma_240) / ma_240 * 100) if ma_240 else 0

        prompt_parts = [
            f"Analyze the following stock for investment potential:",
            f"",
            f"## Stock Information",
            f"- Ticker: {ticker}",
            f"- Company: {name}",
            f"- Current Price: ${current_price:.2f}",
            f"- 240-day MA: ${ma_240:.2f}",
            f"- Price vs 240-MA: {price_vs_ma:+.2f}%",
            f"",
            f"## Technical Indicators",
        ]

        for key, value in technical.items():
            if isinstance(value, float):
                prompt_parts.append(f"- {key}: {value:.2f}")
            else:
                prompt_parts.append(f"- {key}: {value}")

        prompt_parts.extend([
            f"",
            f"## Fundamental Data",
        ])

        for key, value in fundamental.items():
            if isinstance(value, float):
                prompt_parts.append(f"- {key}: {value:.2f}")
            else:
                prompt_parts.append(f"- {key}: {value}")

        if news:
            prompt_parts.extend([
                f"",
                f"## Recent News & Sentiment",
            ])
            for key, value in news.items():
                if isinstance(value, list):
                    prompt_parts.append(f"- {key}:")
                    for item in value[:5]:  # Limit to 5 items
                        prompt_parts.append(f"  - {item}")
                else:
                    prompt_parts.append(f"- {key}: {value}")

        prompt_parts.extend([
            f"",
            f"Provide your analysis in JSON format as specified."
        ])

        return "\n".join(prompt_parts)

    def _call_claude(self, prompt: str, system: str = None) -> str:
        """
        Make API call with retry logic. Dispatches to the correct provider.

        Args:
            prompt: User prompt to send
            system: System prompt (optional)

        Returns:
            Response text from the AI model

        Raises:
            APICallError: If all retries fail
        """
        if self._provider == "openai":
            return self._call_openai(prompt, system)
        return self._call_anthropic(prompt, system)

    def _call_anthropic(self, prompt: str, system: str = None) -> str:
        """Make API call to Anthropic Claude with retry logic."""
        import anthropic

        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Anthropic API call attempt {attempt + 1}/{self.max_retries}")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system or "",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                response_text = message.content[0].text
                logger.debug(f"API response received: {len(response_text)} chars")

                return response_text

            except anthropic.RateLimitError as e:
                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit. Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except anthropic.APIConnectionError as e:
                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Connection error. Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except anthropic.APIStatusError as e:
                # Non-retryable errors (4xx except rate limit)
                if e.status_code < 500 and e.status_code != 429:
                    logger.error(f"API error (non-retryable): {e}")
                    raise APICallError(f"API error: {e}")

                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Server error ({e.status_code}). Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Unexpected error during API call: {e}")
                raise APICallError(f"Unexpected error: {e}")

        # All retries exhausted
        logger.error(f"All {self.max_retries} retries failed. Last error: {last_error}")
        raise APICallError(f"API call failed after {self.max_retries} retries: {last_error}")

    def _call_openai(self, prompt: str, system: str = None) -> str:
        """Make API call to OpenAI with retry logic."""
        import openai

        last_error = None
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"OpenAI API call attempt {attempt + 1}/{self.max_retries}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,
                )

                response_text = response.choices[0].message.content
                if not response_text:
                    raise APICallError("OpenAI returned empty response content")
                logger.debug(f"API response received: {len(response_text)} chars")

                return response_text

            except openai.RateLimitError as e:
                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit. Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except openai.APIConnectionError as e:
                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Connection error. Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except openai.APIStatusError as e:
                if e.status_code < 500 and e.status_code != 429:
                    logger.error(f"API error (non-retryable): {e}")
                    raise APICallError(f"API error: {e}")

                last_error = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Server error ({e.status_code}). Retrying in {delay:.1f}s...")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Unexpected error during API call: {e}")
                raise APICallError(f"Unexpected error: {e}")

        logger.error(f"All {self.max_retries} retries failed. Last error: {last_error}")
        raise APICallError(f"API call failed after {self.max_retries} retries: {last_error}")

    def _parse_analysis_response(self, ticker: str, response: str) -> AnalysisResult:
        """
        Parse Claude's JSON response into AnalysisResult.

        Args:
            ticker: Stock ticker for the result
            response: Raw response text from Claude

        Returns:
            AnalysisResult object

        Raises:
            ResponseParseError: If JSON parsing fails or required fields missing
        """
        logger.debug(f"Parsing response for {ticker}")

        # Try to extract JSON from response (Claude sometimes adds markdown formatting)
        json_str = response.strip()

        # Handle markdown code blocks
        if "```json" in json_str:
            start = json_str.find("```json") + 7
            end = json_str.find("```", start)
            json_str = json_str[start:end].strip()
        elif "```" in json_str:
            start = json_str.find("```") + 3
            end = json_str.find("```", start)
            json_str = json_str[start:end].strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {ticker}: {e}")
            logger.debug(f"Raw response: {response}")
            raise ResponseParseError(f"Failed to parse JSON response: {e}")

        # Validate and extract required fields
        required_fields = [
            "valuation_score", "risk_score", "entry_recommendation",
            "reasoning", "key_risks", "catalysts"
        ]

        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.error(f"Missing fields in response for {ticker}: {missing}")
            raise ResponseParseError(f"Missing required fields: {missing}")

        # Validate score ranges
        valuation_score = float(data["valuation_score"])
        risk_score = float(data["risk_score"])

        if not (1 <= valuation_score <= 10):
            logger.warning(f"Valuation score {valuation_score} out of range for {ticker}, clamping")
            valuation_score = max(1, min(10, valuation_score))

        if not (1 <= risk_score <= 10):
            logger.warning(f"Risk score {risk_score} out of range for {ticker}, clamping")
            risk_score = max(1, min(10, risk_score))

        # Validate recommendation
        recommendation = data["entry_recommendation"].upper()
        if recommendation not in ("BUY", "WAIT", "AVOID"):
            logger.warning(f"Invalid recommendation '{recommendation}' for {ticker}, defaulting to WAIT")
            recommendation = "WAIT"

        return AnalysisResult(
            ticker=ticker,
            valuation_score=valuation_score,
            risk_score=risk_score,
            entry_recommendation=recommendation,
            reasoning=str(data["reasoning"]),
            key_risks=list(data["key_risks"]),
            catalysts=list(data["catalysts"]),
            raw_response=response
        )
