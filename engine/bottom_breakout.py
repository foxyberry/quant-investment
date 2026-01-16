import pandas as pd
from datetime import datetime
from typing import Dict, Any
from utils.timezone_utils import get_current_market_time

class BottomBreakoutStrategy:
    """
    바닥 돌파 전략 클래스
    """
    
    def __init__(self, breakout_threshold: float = 1.05, stop_loss_threshold: float = 0.95):
        self.breakout_threshold = breakout_threshold
        self.stop_loss_threshold = stop_loss_threshold
    
    def analyze(self, data: pd.DataFrame, lookback_days: int = 20) -> Dict[str, Any]:
        """
        바닥 돌파 분석을 수행합니다.
        
        Args:
            data: 주가 데이터 (OHLCV)
            lookback_days: 바닥을 찾을 기간 (일)
            
        Returns:
            분석 결과 딕셔너리
        """
        if len(data) < lookback_days + 1:
            return None
            
        # 바닥 계산 (lookback_days만큼의 과거 구간에서)
        recent_lows = data['Low'].iloc[-(lookback_days + 1):-1]  # 오늘은 제외
        bottom_price = recent_lows.min()
        bottom_date = recent_lows.idxmin()
        
        # 돌파가격과 손절가격 계산
        breakout_price = bottom_price * self.breakout_threshold
        stop_loss_price = bottom_price * self.stop_loss_threshold
        
        # 현재가격
        current_price = data['Close'].iloc[-1]
        
        # 돌파 여부 확인
        is_breakout = current_price >= breakout_price
        
        # 손절 여부 확인
        is_stop_loss = current_price <= stop_loss_price
        
        # 바닥 대비 상승률
        price_change_pct = ((current_price - bottom_price) / bottom_price) * 100
        
        return {
            'bottom_price': bottom_price,
            'bottom_date': bottom_date,
            'breakout_price': breakout_price,
            'stop_loss_price': stop_loss_price,
            'current_price': current_price,
            'is_breakout': is_breakout,
            'is_stop_loss': is_stop_loss,
            'price_change_pct': price_change_pct,
            'analysis_date': get_current_market_time()
        }
