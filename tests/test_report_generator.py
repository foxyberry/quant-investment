"""
Tests for ReportGenerator module
"""

import pytest
import os
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from pipeline import ReportGenerator, PositionRecommendation, calculate_position_sizes


@dataclass
class MockFullAnalysisResult:
    """Mock FullAnalysisResult for testing"""
    ticker: str
    name: str
    current_price: float
    ma_240: float
    distance_pct: float
    valuation_score: float
    risk_score: float
    entry_recommendation: str
    reasoning: str
    key_risks: List[str]
    catalysts: List[str]
    technical_view: str = "neutral"
    fundamental_view: str = "fair"
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    technical: Dict[str, Any] = field(default_factory=dict)
    fundamental: Dict[str, Any] = field(default_factory=dict)
    news: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@pytest.fixture
def sample_results():
    """Sample analysis results for testing"""
    return [
        MockFullAnalysisResult(
            ticker="DIS",
            name="Walt Disney Co.",
            current_price=110.19,
            ma_240=108.50,
            distance_pct=1.6,
            valuation_score=8,
            risk_score=4,
            entry_recommendation="BUY",
            reasoning="Strong brand with recovering theme park business.",
            key_risks=["Streaming competition", "Theme park cyclicality"],
            catalysts=["New content pipeline", "ESPN streaming launch"],
            target_price=130.0,
            stop_loss_price=104.68,
        ),
        MockFullAnalysisResult(
            ticker="AAPL",
            name="Apple Inc.",
            current_price=185.50,
            ma_240=178.20,
            distance_pct=4.1,
            valuation_score=7,
            risk_score=5,
            entry_recommendation="BUY",
            reasoning="Strong ecosystem with services growth.",
            key_risks=["iPhone dependency", "China exposure"],
            catalysts=["AI features", "Vision Pro adoption"],
            target_price=210.0,
            stop_loss_price=175.23,
        ),
        MockFullAnalysisResult(
            ticker="MSFT",
            name="Microsoft Corp.",
            current_price=420.97,
            ma_240=486.20,
            distance_pct=-13.4,
            valuation_score=6,
            risk_score=6,
            entry_recommendation="WAIT",
            reasoning="Solid company but needs better entry point.",
            key_risks=["Antitrust concerns", "Azure growth slowdown"],
            catalysts=["AI integration", "Enterprise demand"],
        ),
        MockFullAnalysisResult(
            ticker="NFLX",
            name="Netflix Inc.",
            current_price=84.08,
            ma_240=112.00,
            distance_pct=-25.0,
            valuation_score=4,
            risk_score=8,
            entry_recommendation="AVOID",
            reasoning="Valuation concerns amid subscriber uncertainty.",
            key_risks=["Password sharing crackdown impact", "Content costs"],
            catalysts=["Ad tier growth"],
        ),
    ]


@pytest.fixture
def korean_stock_result():
    """Korean stock result for testing currency formatting"""
    return MockFullAnalysisResult(
        ticker="005930.KS",
        name="Samsung Electronics",
        current_price=72000,
        ma_240=70000,
        distance_pct=2.86,
        valuation_score=7,
        risk_score=5,
        entry_recommendation="BUY",
        reasoning="Strong semiconductor position.",
        key_risks=["Memory cycle risk", "Competition"],
        catalysts=["AI chip demand", "HBM growth"],
    )


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestReportGenerator:
    """Tests for ReportGenerator class"""

    def test_init_creates_output_dir(self, temp_output_dir):
        """Test that initialization creates output directory"""
        output_path = os.path.join(temp_output_dir, "test_reports")
        generator = ReportGenerator(output_dir=output_path)
        assert os.path.exists(output_path)

    def test_generate_daily_report_structure(self, sample_results, temp_output_dir):
        """Test that generated report has correct structure"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        # Check required sections
        assert "# Daily Stock Analysis Report" in report
        assert "## Executive Summary" in report
        assert "## Top Recommendations" in report
        assert "## Detailed Analysis" in report
        assert "## Risk Warnings" in report
        assert "## Wait List" in report
        assert "## Avoid List" in report

    def test_executive_summary_counts(self, sample_results, temp_output_dir):
        """Test that executive summary has correct counts"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        assert "Stocks Analyzed**: 4" in report
        assert "Buy Recommendations**: 2" in report
        assert "Wait**: 1" in report
        assert "Avoid**: 1" in report

    def test_market_names(self, sample_results, temp_output_dir):
        """Test market name formatting"""
        generator = ReportGenerator(output_dir=temp_output_dir)

        report_sp500 = generator.generate_daily_report(sample_results, market="SP500")
        assert "S&P 500" in report_sp500

        report_kospi = generator.generate_daily_report(sample_results, market="KOSPI")
        assert "KOSPI (Korea)" in report_kospi

    def test_empty_results(self, temp_output_dir):
        """Test report generation with empty results"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report([], market="SP500")

        assert "No stocks were analyzed today" in report

    def test_save_report(self, sample_results, temp_output_dir):
        """Test saving report to file"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        filepath = generator.save_report(report, filename="test_report.md")

        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            content = f.read()
        assert content == report

    def test_save_report_auto_filename(self, sample_results, temp_output_dir):
        """Test saving report with auto-generated filename"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        filepath = generator.save_report(report)

        assert os.path.exists(filepath)
        assert filepath.endswith(".md")
        assert "analysis_" in filepath

    def test_korean_currency_formatting(self, korean_stock_result, temp_output_dir):
        """Test Korean won currency formatting"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report([korean_stock_result], market="KOSPI")

        assert "72,000 KRW" in report
        assert "70,000 KRW" in report

    def test_us_currency_formatting(self, sample_results, temp_output_dir):
        """Test USD currency formatting"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        assert "$110.19" in report
        assert "$108.50" in report

    def test_high_risk_warnings(self, sample_results, temp_output_dir):
        """Test high risk warnings are included"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(sample_results, market="SP500")

        assert "High Risk Stocks" in report
        assert "NFLX" in report
        assert "Risk 8/10" in report


class TestPositionRecommendation:
    """Tests for PositionRecommendation dataclass"""

    def test_to_dict(self):
        """Test conversion to dictionary"""
        pos = PositionRecommendation(
            ticker="AAPL",
            shares=10,
            amount=1850.0,
            position_pct=5.0,
            stop_loss=170.0,
            target_price=200.0,
        )

        d = pos.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["shares"] == 10
        assert d["amount"] == 1850.0
        assert d["position_pct"] == 5.0
        assert d["stop_loss"] == 170.0
        assert d["target_price"] == 200.0


class TestCalculatePositionSizes:
    """Tests for calculate_position_sizes function"""

    def test_basic_position_sizing(self, sample_results):
        """Test basic position size calculation"""
        positions = calculate_position_sizes(
            sample_results,
            portfolio_value=100000,
            max_position_pct=5.0,
        )

        assert len(positions) == 2  # Only BUY recommendations
        assert all(p.ticker in ["DIS", "AAPL"] for p in positions)

    def test_position_size_limits(self, sample_results):
        """Test that position sizes respect limits"""
        positions = calculate_position_sizes(
            sample_results,
            portfolio_value=100000,
            max_position_pct=5.0,
            min_position_pct=2.0,
        )

        for p in positions:
            assert p.position_pct <= 5.0
            assert p.position_pct >= 2.0

    def test_total_allocation_limit(self, sample_results):
        """Test that total allocation respects limit"""
        positions = calculate_position_sizes(
            sample_results,
            portfolio_value=100000,
            max_position_pct=5.0,
            max_total_pct=10.0,
        )

        total_pct = sum(p.position_pct for p in positions)
        assert total_pct <= 10.0

    def test_empty_results(self):
        """Test with no BUY recommendations"""
        wait_result = MockFullAnalysisResult(
            ticker="MSFT",
            name="Microsoft",
            current_price=400.0,
            ma_240=380.0,
            distance_pct=5.26,
            valuation_score=6,
            risk_score=6,
            entry_recommendation="WAIT",
            reasoning="Wait for better entry",
            key_risks=["Risk 1"],
            catalysts=["Catalyst 1"],
        )

        positions = calculate_position_sizes(
            [wait_result],
            portfolio_value=100000,
        )

        assert len(positions) == 0

    def test_position_amounts(self, sample_results):
        """Test that position amounts are calculated correctly"""
        positions = calculate_position_sizes(
            sample_results,
            portfolio_value=100000,
            max_position_pct=5.0,
        )

        for p in positions:
            # Find the original result
            result = next(r for r in sample_results if r.ticker == p.ticker)
            expected_amount = p.shares * result.current_price
            assert abs(p.amount - expected_amount) < 0.01

    def test_stop_loss_included(self, sample_results):
        """Test that stop loss is included from analysis result"""
        positions = calculate_position_sizes(
            sample_results,
            portfolio_value=100000,
        )

        dis_position = next(p for p in positions if p.ticker == "DIS")
        assert dis_position.stop_loss is not None
        assert dis_position.stop_loss == 104.68  # From the sample data


class TestPrintSummary:
    """Tests for print_summary method"""

    def test_print_summary_no_error(self, sample_results, temp_output_dir, capsys):
        """Test that print_summary runs without error"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        generator.print_summary(sample_results)

        captured = capsys.readouterr()
        assert "ANALYSIS SUMMARY" in captured.out
        assert "Total Analyzed: 4" in captured.out
        assert "BUY:" in captured.out

    def test_print_summary_empty_results(self, temp_output_dir, capsys):
        """Test print_summary with empty results"""
        generator = ReportGenerator(output_dir=temp_output_dir)
        generator.print_summary([])

        captured = capsys.readouterr()
        assert "No results to summarize" in captured.out


class TestPositionTable:
    """Tests for position sizing table generation"""

    def test_position_table_in_report(self, sample_results, temp_output_dir):
        """Test that position table is included when positions are provided"""
        positions = [
            PositionRecommendation(
                ticker="DIS",
                shares=45,
                amount=4958.0,
                position_pct=5.0,
                stop_loss=104.68,
            ),
            PositionRecommendation(
                ticker="AAPL",
                shares=26,
                amount=4823.0,
                position_pct=4.8,
                stop_loss=175.23,
            ),
        ]

        generator = ReportGenerator(output_dir=temp_output_dir)
        report = generator.generate_daily_report(
            sample_results,
            positions=positions,
            market="SP500",
        )

        assert "## Position Sizing" in report
        assert "DIS" in report
        assert "45" in report  # shares
        assert "$104.68" in report  # stop loss
