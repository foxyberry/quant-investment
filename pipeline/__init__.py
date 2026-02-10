"""
Pipeline Module
Analysis and report generation pipeline

Usage:
    from pipeline import ReportGenerator, PositionRecommendation, calculate_position_sizes

    # Generate reports
    generator = ReportGenerator()
    report = generator.generate_daily_report(results, market="SP500")
    filepath = generator.save_report(report)

    # Calculate position sizes
    positions = calculate_position_sizes(
        results,
        portfolio_value=100000,
        max_position_pct=5.0
    )
"""

from .report_generator import (
    ReportGenerator,
    PositionRecommendation,
    calculate_position_sizes,
)

__all__ = [
    "ReportGenerator",
    "PositionRecommendation",
    "calculate_position_sizes",
]
