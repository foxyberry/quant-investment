"""
Report Generator Module
Markdown report generation for stock analysis results

Usage:
    from pipeline import ReportGenerator
    from llm import FullAnalysisResult

    # Initialize
    generator = ReportGenerator()

    # Generate daily report
    report = generator.generate_daily_report(
        results=analysis_results,
        positions=position_recommendations,
        market="SP500"
    )

    # Save report
    filepath = generator.save_report(report)

    # Quick console summary
    generator.print_summary(results)
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PositionRecommendation:
    """Position sizing recommendation for a stock"""
    ticker: str
    shares: int
    amount: float
    position_pct: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "amount": self.amount,
            "position_pct": self.position_pct,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "risk_reward_ratio": self.risk_reward_ratio,
        }


class ReportGenerator:
    """
    Generate readable analysis reports in markdown format.

    Features:
    - Daily analysis reports with executive summary
    - Top recommendations table
    - Detailed analysis sections
    - Risk warnings
    - Position sizing tables
    """

    def __init__(self, output_dir: str = "reports/analysis"):
        """
        Initialize report generator.

        Args:
            output_dir: Directory to save reports (relative to project root)
        """
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist"""
        if not os.path.isabs(self.output_dir):
            # Make it relative to the current working directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.output_dir = os.path.join(base_dir, self.output_dir)

        os.makedirs(self.output_dir, exist_ok=True)

    def generate_daily_report(
        self,
        results: list,
        positions: list = None,
        market: str = "ALL",
    ) -> str:
        """
        Generate a daily analysis report.

        Args:
            results: List of FullAnalysisResult objects
            positions: Optional list of PositionRecommendation objects
            market: Market identifier (KOSPI, SP500, or ALL)

        Returns:
            Markdown formatted report string
        """
        if not results:
            return self._generate_empty_report(market)

        sections = []

        # 1. Header
        sections.append(self._generate_header(market))

        # 2. Executive Summary
        sections.append(self._generate_executive_summary(results))

        # 3. Top Recommendations Table
        buy_results = [r for r in results if r.entry_recommendation == "BUY"]
        if buy_results:
            sections.append(self._generate_recommendations_table(buy_results))

        # 4. Detailed Analysis
        if buy_results:
            sections.append(self._generate_detailed_analysis(buy_results))

        # 5. Risk Warnings
        sections.append(self._generate_risk_warnings(results))

        # 6. Position Sizing (if provided)
        if positions:
            sections.append(self._generate_position_table(positions))

        # 7. Wait List Summary
        wait_results = [r for r in results if r.entry_recommendation == "WAIT"]
        if wait_results:
            sections.append(self._generate_wait_list(wait_results))

        # 8. Avoid List Summary
        avoid_results = [r for r in results if r.entry_recommendation == "AVOID"]
        if avoid_results:
            sections.append(self._generate_avoid_list(avoid_results))

        # Footer
        sections.append(self._generate_footer())

        return "\n\n".join(sections)

    def _generate_empty_report(self, market: str) -> str:
        """Generate report when no results are available"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        market_name = self._get_market_name(market)

        return f"""# Daily Stock Analysis Report
**Date**: {date_str} | **Market**: {market_name}

## Executive Summary

No stocks were analyzed today.

---
*Report generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    def _generate_header(self, market: str) -> str:
        """Generate report header"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        market_name = self._get_market_name(market)

        return f"""# Daily Stock Analysis Report
**Date**: {date_str} | **Market**: {market_name}"""

    def _get_market_name(self, market: str) -> str:
        """Convert market code to display name"""
        market_names = {
            "KOSPI": "KOSPI (Korea)",
            "KOSDAQ": "KOSDAQ (Korea)",
            "SP500": "S&P 500",
            "ALL": "All Markets",
        }
        return market_names.get(market.upper(), market)

    def _generate_executive_summary(self, results: list) -> str:
        """Generate executive summary section"""
        total = len(results)
        buy_count = sum(1 for r in results if r.entry_recommendation == "BUY")
        wait_count = sum(1 for r in results if r.entry_recommendation == "WAIT")
        avoid_count = sum(1 for r in results if r.entry_recommendation == "AVOID")

        # Calculate average scores
        avg_valuation = sum(r.valuation_score for r in results) / total if total else 0
        avg_risk = sum(r.risk_score for r in results) / total if total else 0

        return f"""## Executive Summary

- **Stocks Analyzed**: {total}
- **Buy Recommendations**: {buy_count}
- **Wait**: {wait_count}
- **Avoid**: {avoid_count}

Average Scores:
- Valuation: {avg_valuation:.1f}/10
- Risk: {avg_risk:.1f}/10"""

    def _generate_recommendations_table(self, buy_results: list) -> str:
        """Generate top recommendations table"""
        # Sort by valuation score descending, then by risk ascending
        sorted_results = sorted(
            buy_results,
            key=lambda x: (-x.valuation_score, x.risk_score)
        )

        lines = ["## Top Recommendations", ""]
        lines.append("| Rank | Ticker | Name | Price | Valuation | Risk | Action |")
        lines.append("|------|--------|------|-------|-----------|------|--------|")

        for i, r in enumerate(sorted_results[:10], 1):
            price_str = self._format_price(r.current_price, r.ticker)
            name_short = r.name[:20] + "..." if len(r.name) > 20 else r.name
            lines.append(
                f"| {i} | {r.ticker} | {name_short} | {price_str} | "
                f"{r.valuation_score:.0f}/10 | {r.risk_score:.0f}/10 | {r.entry_recommendation} |"
            )

        return "\n".join(lines)

    def _generate_detailed_analysis(self, buy_results: list) -> str:
        """Generate detailed analysis for each recommended stock"""
        # Sort by valuation score descending
        sorted_results = sorted(
            buy_results,
            key=lambda x: (-x.valuation_score, x.risk_score)
        )

        lines = ["## Detailed Analysis"]

        for i, r in enumerate(sorted_results[:10], 1):
            lines.append("")
            lines.append(f"### {i}. {r.ticker} - {r.name}")
            lines.append("")

            # Price info
            price_str = self._format_price(r.current_price, r.ticker)
            ma_str = self._format_price(r.ma_240, r.ticker)
            distance_sign = "+" if r.distance_pct >= 0 else ""
            lines.append(f"- **Price**: {price_str} (240d MA: {ma_str}, {distance_sign}{r.distance_pct:.1f}%)")
            lines.append(f"- **Recommendation**: {r.entry_recommendation}")
            lines.append(f"- **Valuation Score**: {r.valuation_score:.0f}/10")
            lines.append(f"- **Risk Score**: {r.risk_score:.0f}/10")

            # Technical and fundamental views if available
            if hasattr(r, 'technical_view') and r.technical_view:
                lines.append(f"- **Technical View**: {r.technical_view}")
            if hasattr(r, 'fundamental_view') and r.fundamental_view:
                lines.append(f"- **Fundamental View**: {r.fundamental_view}")

            # Reasoning
            if r.reasoning:
                lines.append("")
                lines.append("**Reasoning**:")
                lines.append(f"> {r.reasoning}")

            # Key Risks
            if r.key_risks:
                lines.append("")
                lines.append("**Key Risks**:")
                for risk in r.key_risks[:5]:
                    lines.append(f"- {risk}")

            # Catalysts
            if r.catalysts:
                lines.append("")
                lines.append("**Catalysts**:")
                for catalyst in r.catalysts[:5]:
                    lines.append(f"- {catalyst}")

            # Target prices if available
            if hasattr(r, 'target_price') and r.target_price:
                target_str = self._format_price(r.target_price, r.ticker)
                lines.append("")
                lines.append(f"**Target Price**: {target_str}")

            if hasattr(r, 'stop_loss_price') and r.stop_loss_price:
                stop_str = self._format_price(r.stop_loss_price, r.ticker)
                lines.append(f"**Stop Loss**: {stop_str}")

        return "\n".join(lines)

    def _generate_risk_warnings(self, results: list) -> str:
        """Generate risk warnings section"""
        lines = ["## Risk Warnings"]

        # High risk stocks (risk score >= 7)
        high_risk = [r for r in results if r.risk_score >= 7]
        if high_risk:
            lines.append("")
            lines.append("### High Risk Stocks (Risk >= 7)")
            lines.append("")
            for r in sorted(high_risk, key=lambda x: -x.risk_score)[:5]:
                lines.append(f"- **{r.ticker}** ({r.name}): Risk {r.risk_score:.0f}/10")
                if r.key_risks:
                    lines.append(f"  - Primary risk: {r.key_risks[0]}")

        # Stocks with valuation/risk mismatch (high valuation but also high risk)
        mismatch = [r for r in results if r.valuation_score >= 7 and r.risk_score >= 6]
        if mismatch:
            lines.append("")
            lines.append("### High Valuation with Elevated Risk")
            lines.append("")
            for r in mismatch[:5]:
                lines.append(
                    f"- **{r.ticker}**: Valuation {r.valuation_score:.0f}/10, "
                    f"Risk {r.risk_score:.0f}/10"
                )

        # General market warnings
        avg_risk = sum(r.risk_score for r in results) / len(results) if results else 0
        if avg_risk >= 6:
            lines.append("")
            lines.append("### Market Warning")
            lines.append("")
            lines.append(
                f"Average risk score is elevated at {avg_risk:.1f}/10. "
                "Consider reducing position sizes."
            )

        if len(lines) == 1:
            lines.append("")
            lines.append("No significant risk warnings at this time.")

        return "\n".join(lines)

    def _generate_position_table(self, positions: list) -> str:
        """Generate position sizing table"""
        lines = ["## Position Sizing"]
        lines.append("")
        lines.append("| Ticker | Shares | Amount | Position % | Stop Loss |")
        lines.append("|--------|--------|--------|------------|-----------|")

        for p in positions:
            amount_str = f"${p.amount:,.0f}"
            position_str = f"{p.position_pct:.1f}%"
            stop_str = f"${p.stop_loss:,.2f}" if p.stop_loss else "-"

            lines.append(
                f"| {p.ticker} | {p.shares} | {amount_str} | "
                f"{position_str} | {stop_str} |"
            )

        # Total
        total_amount = sum(p.amount for p in positions)
        total_pct = sum(p.position_pct for p in positions)
        lines.append(f"| **Total** | - | **${total_amount:,.0f}** | **{total_pct:.1f}%** | - |")

        return "\n".join(lines)

    def _generate_wait_list(self, wait_results: list) -> str:
        """Generate wait list summary"""
        lines = ["## Wait List"]
        lines.append("")
        lines.append("Stocks that may become opportunities with improved conditions:")
        lines.append("")
        lines.append("| Ticker | Name | Price | Valuation | Risk | Reason |")
        lines.append("|--------|------|-------|-----------|------|--------|")

        sorted_results = sorted(
            wait_results,
            key=lambda x: (-x.valuation_score, x.risk_score)
        )

        for r in sorted_results[:10]:
            price_str = self._format_price(r.current_price, r.ticker)
            name_short = r.name[:15] + "..." if len(r.name) > 15 else r.name
            reason_short = r.reasoning[:30] + "..." if r.reasoning and len(r.reasoning) > 30 else (r.reasoning or "-")
            lines.append(
                f"| {r.ticker} | {name_short} | {price_str} | "
                f"{r.valuation_score:.0f}/10 | {r.risk_score:.0f}/10 | {reason_short} |"
            )

        return "\n".join(lines)

    def _generate_avoid_list(self, avoid_results: list) -> str:
        """Generate avoid list summary"""
        lines = ["## Avoid List"]
        lines.append("")
        lines.append("Stocks to avoid based on current analysis:")
        lines.append("")

        sorted_results = sorted(
            avoid_results,
            key=lambda x: (x.valuation_score, -x.risk_score)
        )

        for r in sorted_results[:10]:
            price_str = self._format_price(r.current_price, r.ticker)
            lines.append(f"- **{r.ticker}** ({r.name}) - {price_str}")
            lines.append(f"  - Valuation: {r.valuation_score:.0f}/10, Risk: {r.risk_score:.0f}/10")
            if r.key_risks:
                lines.append(f"  - Primary concern: {r.key_risks[0]}")

        return "\n".join(lines)

    def _generate_footer(self) -> str:
        """Generate report footer"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""---

*Report generated at {timestamp}*

**Disclaimer**: This report is for informational purposes only and does not constitute investment advice. Always conduct your own research before making investment decisions."""

    def _format_price(self, price: float, ticker: str = "") -> str:
        """Format price with appropriate currency symbol"""
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            # Korean won - no decimal places
            return f"{price:,.0f} KRW"
        else:
            # USD - 2 decimal places
            return f"${price:,.2f}"

    def save_report(self, content: str, filename: str = None) -> str:
        """
        Save report to file.

        Args:
            content: Report content (markdown string)
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Full filepath of saved report
        """
        if filename is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H%M")
            filename = f"analysis_{date_str}_{time_str}.md"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Report saved to {filepath}")
        return filepath

    def print_summary(self, results: list) -> None:
        """
        Print quick summary to console.

        Args:
            results: List of FullAnalysisResult objects
        """
        if not results:
            print("No results to summarize.")
            return

        total = len(results)
        buy_count = sum(1 for r in results if r.entry_recommendation == "BUY")
        wait_count = sum(1 for r in results if r.entry_recommendation == "WAIT")
        avoid_count = sum(1 for r in results if r.entry_recommendation == "AVOID")

        print("\n" + "=" * 60)
        print("  ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"  Total Analyzed: {total}")
        print(f"  BUY:   {buy_count:3d} ({buy_count/total*100:.1f}%)")
        print(f"  WAIT:  {wait_count:3d} ({wait_count/total*100:.1f}%)")
        print(f"  AVOID: {avoid_count:3d} ({avoid_count/total*100:.1f}%)")
        print("=" * 60)

        # Top BUY recommendations
        buy_results = [r for r in results if r.entry_recommendation == "BUY"]
        if buy_results:
            sorted_buys = sorted(
                buy_results,
                key=lambda x: (-x.valuation_score, x.risk_score)
            )
            print("\n  TOP BUY RECOMMENDATIONS:")
            print("-" * 60)
            print(f"  {'Ticker':<8} {'Name':<20} {'Valuation':>10} {'Risk':>8}")
            print("-" * 60)
            for r in sorted_buys[:5]:
                name_short = r.name[:18] + ".." if len(r.name) > 18 else r.name
                print(f"  {r.ticker:<8} {name_short:<20} {r.valuation_score:>8.0f}/10 {r.risk_score:>6.0f}/10")
            print("-" * 60)
        print()


def calculate_position_sizes(
    results: list,
    portfolio_value: float,
    max_position_pct: float = 5.0,
    min_position_pct: float = 2.0,
    max_total_pct: float = 30.0,
) -> List[PositionRecommendation]:
    """
    Calculate position sizes for recommended stocks.

    Args:
        results: List of FullAnalysisResult with BUY recommendations
        portfolio_value: Total portfolio value
        max_position_pct: Maximum position size as percentage
        min_position_pct: Minimum position size as percentage
        max_total_pct: Maximum total allocation percentage

    Returns:
        List of PositionRecommendation objects
    """
    buy_results = [r for r in results if r.entry_recommendation == "BUY"]
    if not buy_results:
        return []

    # Sort by valuation score (highest first) then risk (lowest first)
    sorted_results = sorted(
        buy_results,
        key=lambda x: (-x.valuation_score, x.risk_score)
    )

    positions = []
    total_allocated = 0.0

    for r in sorted_results:
        if total_allocated >= max_total_pct:
            break

        # Calculate position size based on score
        # Higher valuation and lower risk = larger position
        score_factor = (r.valuation_score / 10) * (1 - r.risk_score / 20)
        position_pct = min_position_pct + (max_position_pct - min_position_pct) * score_factor

        # Ensure we don't exceed limits
        position_pct = min(position_pct, max_position_pct)
        position_pct = min(position_pct, max_total_pct - total_allocated)

        if position_pct < min_position_pct:
            continue

        amount = portfolio_value * (position_pct / 100)
        shares = int(amount / r.current_price)

        if shares <= 0:
            continue

        # Recalculate actual amount and percentage
        actual_amount = shares * r.current_price
        actual_pct = (actual_amount / portfolio_value) * 100

        # Calculate stop loss (default: 5% below current price)
        stop_loss = r.stop_loss_price if hasattr(r, 'stop_loss_price') and r.stop_loss_price else r.current_price * 0.95

        positions.append(PositionRecommendation(
            ticker=r.ticker,
            shares=shares,
            amount=actual_amount,
            position_pct=actual_pct,
            stop_loss=stop_loss,
            target_price=r.target_price if hasattr(r, 'target_price') else None,
        ))

        total_allocated += actual_pct

    return positions
