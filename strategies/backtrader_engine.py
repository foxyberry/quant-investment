import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from strategies.backtrader_strategy import BottomBreakoutStrategy, SimpleBuyHoldStrategy
from utils.fetch import get_historical_data
from utils.timezone_utils import prepare_dataframe_for_backtrader, make_timezone_naive

class BacktraderEngine:
    """
    Backtrader 백테스팅 엔진
    """
    
    def __init__(self, initial_cash: float = 100000, commission: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
        self.logger = logging.getLogger(__name__)
        
    def prepare_data_for_backtrader(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Backtrader용 데이터 준비
        
        Args:
            symbol: 주식 심볼
            start_date: 시작일
            end_date: 종료일
            
        Returns:
            Backtrader용 DataFrame
        """
        try:
            # Get historical data
            data = get_historical_data(symbol, start_date, end_date)
            
            if data is None or data.empty:
                self.logger.warning(f"No data available for {symbol}")
                return None
                
            self.logger.debug(f"Raw data for {symbol}: {len(data)} rows, index type: {type(data.index)}")
            
            # Ensure we have required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                self.logger.error(f"Missing required columns for {symbol}. Available: {list(data.columns)}")
                return None
            
            # Prepare DataFrame for backtrader (converts to timezone-naive)
            data = prepare_dataframe_for_backtrader(data)
            self.logger.debug(f"After timezone conversion for {symbol}: index type: {type(data.index)}")
            
            # Ensure index is named 'Date' or similar for backtrader
            if data.index.name != 'Date':
                data.index.name = 'Date'
            
            # Validate data quality
            if data.isnull().any().any():
                self.logger.warning(f"Data for {symbol} contains null values")
                data = data.dropna()
                
            if data.empty:
                self.logger.warning(f"No valid data remaining for {symbol} after cleaning")
                return None
                
            self.logger.debug(f"Final data for {symbol}: {len(data)} rows, "
                            f"date range: {data.index.min()} to {data.index.max()}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error preparing data for {symbol}: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime,
                    strategy_class=BottomBreakoutStrategy, strategy_params: Dict = None) -> Dict:
        """
        단일 종목 백테스트 실행
        
        Args:
            symbol: 주식 심볼
            start_date: 시작일
            end_date: 종료일
            strategy_class: 전략 클래스
            strategy_params: 전략 파라미터
            
        Returns:
            백테스트 결과
        """
        try:
            # Convert dates to timezone-naive for backtrader
            start_date = make_timezone_naive(start_date)
            end_date = make_timezone_naive(end_date)
            
            # Prepare data
            data = self.prepare_data_for_backtrader(symbol, start_date, end_date)
            if data is None:
                return {'error': f'No data available for {symbol}'}
            
            # Create cerebro
            cerebro = bt.Cerebro()
            
            # Add data feed
            data_feed = bt.feeds.PandasData(
                dataname=data,
                datetime=None,  # Use index as datetime
                open='Open',
                high='High',
                low='Low',
                close='Close',
                volume='Volume',
                openinterest=-1
            )
            cerebro.adddata(data_feed)
            
            # Add strategy
            if strategy_params is None:
                strategy_params = {}
            cerebro.addstrategy(strategy_class, **strategy_params)
            
            # Set initial cash and commission
            cerebro.broker.setcash(self.initial_cash)
            cerebro.broker.setcommission(commission=self.commission)
            
            # Run backtest
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run()
            final_value = cerebro.broker.getvalue()
            
            # Calculate metrics
            total_return = (final_value - initial_value) / initial_value * 100
            strategy = results[0]
            
            # Get trade statistics
            trades = strategy.trades if hasattr(strategy, 'trades') else []
            num_trades = len(trades)
            
            # Calculate max drawdown
            portfolio_values = strategy.portfolio_values if hasattr(strategy, 'portfolio_values') else []
            max_drawdown = self._calculate_max_drawdown(portfolio_values) if portfolio_values else 0
            
            return {
                'symbol': symbol,
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return_pct': total_return,
                'num_trades': num_trades,
                'max_drawdown_pct': max_drawdown,
                'start_date': start_date,
                'end_date': end_date,
                'strategy': strategy_class.__name__,
                'trades': trades
            }
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {symbol}: {e}")
            return {'error': str(e)}
    
    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not portfolio_values:
            return 0
            
        peak = portfolio_values[0]
        max_dd = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
                
        return max_dd
    
    def batch_backtest(self, symbols: List[str], start_date: datetime, end_date: datetime,
                      strategy_class=BottomBreakoutStrategy, strategy_params: Dict = None) -> List[Dict]:
        """
        여러 종목에 대해 백테스트 실행
        
        Args:
            symbols: 주식 심볼 리스트
            start_date: 시작일
            end_date: 종료일
            strategy_class: 전략 클래스
            strategy_params: 전략 파라미터
            
        Returns:
            백테스트 결과 리스트
        """
        results = []
        
        for symbol in symbols:
            self.logger.info(f"Running backtest for {symbol}")
            result = self.run_backtest(symbol, start_date, end_date, strategy_class, strategy_params)
            results.append(result)
            
        return results
    
    def compare_strategies(self, symbol: str, start_date: datetime, end_date: datetime,
                          strategies: List[Tuple] = None) -> Dict:
        """
        여러 전략 비교
        
        Args:
            symbol: 주식 심볼
            start_date: 시작일
            end_date: 종료일
            strategies: 전략 리스트 [(strategy_class, strategy_params), ...]
            
        Returns:
            전략 비교 결과
        """
        if strategies is None or len(strategies) == 0:
            strategies = [
                (BottomBreakoutStrategy, {}),
                (SimpleBuyHoldStrategy, {})
            ]
        
        results = {}
        
        for strategy_class, strategy_params in strategies:
            strategy_name = strategy_class.__name__
            self.logger.info(f"Testing strategy: {strategy_name}")
            
            result = self.run_backtest(symbol, start_date, end_date, strategy_class, strategy_params)
            results[strategy_name] = result
            
        return results 