from datetime import datetime
import logging


class BottomBreakoutAnalyzer:
    def __init__(self, get_data_fn, logger=None):
        """
        get_data_fn: 함수를 인자로 받음. 심볼과 조회 일수를 받아서 데이터프레임 반환
        """
        self.get_data_fn = get_data_fn
        self.logger = logger or logging.getLogger(__name__)

    def analyze(self, symbol: str, lookback_days: int = 20):
        try:
            # +1일 포함 (오늘 포함)
            data = self.get_data_fn(symbol, lookback_days + 1)

            if len(data) < lookback_days + 1:
                self.logger.warning(f"{symbol} 데이터 길이 부족")
                return None

            # 바닥 계산 (오늘 제외)
            recent_lows = data['Low'].iloc[-(lookback_days + 1):-1]
            bottom_price = recent_lows.min()
            bottom_date = recent_lows.idxmin()
            breakout_price = bottom_price * 1.05
            stop_loss_price = bottom_price * 0.95

            # 오늘 종가
            current_price = data['Close'].iloc[-1]

            # 어제까지 종가가 breakout_price 미만이어야 함
            prev_closes = data['Close'].iloc[-(lookback_days):-1]
            has_broken_before = (prev_closes >= breakout_price).any()
            is_breakout_today = current_price >= breakout_price

            # 조건: 오늘 처음 돌파
            is_fresh_breakout = (not has_broken_before) and is_breakout_today

            # 거래량 분석
            avg_volume = data['Volume'].iloc[-11:-1].mean()
            recent_volume = data['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

            result = {
                'symbol': symbol,
                'current_price': current_price,
                'bottom_date': bottom_date,
                'bottom_price': bottom_price,
                'breakout_price': breakout_price,
                'stop_loss_price': stop_loss_price,
                'is_breakout_today': is_breakout_today,
                'is_fresh_breakout': is_fresh_breakout,
                'price_from_bottom_pct': ((current_price - bottom_price) / bottom_price) * 100,
                'volume_ratio': volume_ratio,
                'avg_volume_10d': avg_volume,
                'analysis_date': datetime.now()
            }

            return result

        except Exception as e:
            self.logger.warning(f"{symbol} 분석 실패: {e}")
            return None
