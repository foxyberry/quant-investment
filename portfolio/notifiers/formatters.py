"""
Notification Formatters
알림 포맷팅 헬퍼 함수

Usage:
    from portfolio.notifiers.formatters import format_daily_report, format_order_notification
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def format_daily_report(
    date: datetime,
    portfolio_value: float,
    daily_pnl: float,
    daily_pnl_pct: float,
    holdings: List[Dict[str, Any]],
    trades: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    일일 리포트 포맷팅

    Args:
        date: 리포트 날짜
        portfolio_value: 포트폴리오 총 가치
        daily_pnl: 일일 손익 (금액)
        daily_pnl_pct: 일일 손익 (%)
        holdings: 보유 종목 목록
        trades: 당일 거래 목록

    Returns:
        포맷된 리포트 문자열
    """
    lines = [
        f"📊 Daily Report - {date.strftime('%Y-%m-%d')}",
        "=" * 40,
        f"Portfolio Value: {portfolio_value:,.0f}",
        f"Daily P&L: {daily_pnl:+,.0f} ({daily_pnl_pct:+.2f}%)",
        "",
        "Holdings:",
    ]

    for h in holdings:
        pnl_pct = h.get("pnl_pct", 0)
        emoji = "📈" if pnl_pct >= 0 else "📉"
        lines.append(
            f"  {emoji} {h['ticker']}: {h.get('current_value', 0):,.0f} ({pnl_pct:+.1f}%)"
        )

    if trades:
        lines.append("")
        lines.append(f"Trades Today: {len(trades)}")
        for t in trades[:5]:  # Show max 5
            lines.append(f"  • {t.get('side', '')} {t.get('ticker', '')} x{t.get('quantity', 0)}")

    lines.append("=" * 40)
    return "\n".join(lines)


def format_order_notification(
    ticker: str,
    side: str,
    quantity: int,
    price: float,
    status: str
) -> str:
    """
    주문 알림 포맷팅

    Args:
        ticker: 종목 코드
        side: 주문 방향 (BUY/SELL)
        quantity: 수량
        price: 가격
        status: 주문 상태

    Returns:
        포맷된 주문 알림 문자열
    """
    emoji = "🟢" if side == "BUY" else "🔴"
    return (
        f"{emoji} Order {status}\n"
        f"Ticker: {ticker}\n"
        f"Side: {side}\n"
        f"Quantity: {quantity}\n"
        f"Price: {price:,.0f}\n"
        f"Value: {quantity * price:,.0f}"
    )


def format_price_alert(
    ticker: str,
    current_price: float,
    target_price: float,
    alert_type: str
) -> str:
    """
    가격 알림 포맷팅

    Args:
        ticker: 종목 코드
        current_price: 현재 가격
        target_price: 목표 가격
        alert_type: 알림 타입 (TARGET/STOP_LOSS/TAKE_PROFIT)

    Returns:
        포맷된 가격 알림 문자열
    """
    diff_pct = ((current_price - target_price) / target_price) * 100

    if alert_type == "STOP_LOSS":
        emoji = "🛑"
    elif alert_type == "TAKE_PROFIT":
        emoji = "💰"
    else:
        emoji = "🎯"

    return (
        f"{emoji} Price Alert - {alert_type}\n"
        f"Ticker: {ticker}\n"
        f"Current: {current_price:,.0f}\n"
        f"Target: {target_price:,.0f}\n"
        f"Diff: {diff_pct:+.2f}%"
    )
