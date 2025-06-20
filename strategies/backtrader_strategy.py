import backtrader as bt
from datetime import timedelta
import logging

class BottomBreakoutStrategy(bt.Strategy):
    """
    Breakout strategy using backtrader
    
    This strategy:
    - Buys when price breaks above 5% of recent bottom (over `lookback_days`)
    - Sells on 5% drop below that bottom (fixed at entry)
    - Or sells at 10% profit, or if price stagnates >10 days
    """
    
    params = (
        ('volume_threshold', 1.5),
        ('lookback_days', 20),
        ('breakout_threshold', 1.05),
        ('take_profit_threshold', 1.1),
        ('stop_loss_threshold', 0.95),
        ('position_size', 0.95),
        ('debug', False),
    )
    
    def __init__(self):
        # Internal state
        self.in_position = False
        self.entry_price = None
        self.entry_date = None
        self.stop_loss_price = None
        
        # Record keeping
        self.signals = []
        self.trades = []
        self.portfolio_values = []
        
        # Logger
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def log(self, txt, dt=None, level=logging.INFO):
        dt = dt or self.datas[0].datetime.date(0)
        message = f'{dt.isoformat()}: {txt}'
        if self.params.debug:
            print(message)
        self.logger.log(level, message)

    def next(self):
        data = self.datas[0]
        current_date = data.datetime.date(0)
        current_price = data.close[0]
        
        # Track portfolio value
        self.portfolio_values.append(self.broker.getvalue())

        # Skip if not enough data
        if len(data) < self.params.lookback_days:
            return

        # Get lookback low prices
        lookback_lows = [data.low[-i] for i in range(1, self.params.lookback_days + 1)]
        if not lookback_lows:
            return

        bottom_price = min(lookback_lows)
        breakout_price = bottom_price * self.params.breakout_threshold

        # === BUY Logic ===
        if not self.position and current_price > breakout_price:
            size = int((self.broker.getcash() * self.params.position_size) / current_price)
            if size > 0:
                self.buy(size=size)
                self.in_position = True
                self.entry_price = current_price
                self.entry_date = current_date
                self.stop_loss_price = bottom_price * self.params.stop_loss_threshold  # fixed at entry

                self.signals.append({
                    'date': current_date,
                    'action': 'BUY',
                    'price': current_price,
                    'size': size,
                    'bottom_price': bottom_price,
                    'breakout_price': breakout_price
                })
                self.log(f'BUY CREATED: ${current_price:.2f}, Size: {size}, Breakout from ${bottom_price:.2f}')

        # === SELL Logic ===
        elif self.position:
            sell_signal = False
            sell_reason = ""

            if current_price <= self.stop_loss_price:
                sell_signal = True
                sell_reason = "STOP_LOSS"

            elif current_price >= self.entry_price * self.params.take_profit_threshold:
                sell_signal = True
                sell_reason = "TAKE_PROFIT"

            elif current_price > self.entry_price and current_date > self.entry_date + timedelta(days=10):
                sell_signal = True
                sell_reason = "TIME_OUT"

            if sell_signal:
                self.close()
                self.in_position = False

                return_pct = ((current_price - self.entry_price) / self.entry_price) * 100 if self.entry_price else 0

                self.signals.append({
                    'date': current_date,
                    'action': 'SELL',
                    'price': current_price,
                    'reason': sell_reason,
                    'return_pct': return_pct
                })

                self.trades.append({
                    'entry_date': self.entry_date,
                    'entry_price': self.entry_price,
                    'exit_date': current_date,
                    'exit_price': current_price,
                    'return_pct': return_pct,
                    'reason': sell_reason
                })

                self.log(f'SELL CREATED: ${current_price:.2f}, Reason: {sell_reason}, Return: {return_pct:.2f}%')

                # Reset
                self.entry_price = None
                self.entry_date = None
                self.stop_loss_price = None

class SimpleBuyHoldStrategy(bt.Strategy):
    """
    Simple buy and hold strategy for comparison
    """
    
    params = (
        ('debug', False),  # Enable debug logging
    )
    
    def __init__(self):
        self.bought = False
        self.trades = []
        self.portfolio_values = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    def log(self, txt, dt=None, level=logging.INFO):
        """Unified logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        message = f'{dt.isoformat()}: {txt}'
        
        if self.params.debug:
            print(message)
            
        self.logger.log(level, message)
        
    def next(self):
        """Called for every bar"""
        # Record portfolio value
        self.portfolio_values.append(self.broker.getvalue())
        
        # Buy on first day if not already bought
        if not self.bought and len(self) == 1:
            size = int(self.broker.getcash() / self.data.close[0])
            if size > 0:
                self.buy(size=size)
                self.bought = True
                current_date = self.datas[0].datetime.date(0)
                
                self.trades.append({
                    'entry_date': current_date,
                    'entry_price': self.data.close[0],
                    'exit_date': None,
                    'exit_price': None,
                    'return_pct': 0,
                    'reason': 'BUY_AND_HOLD'
                })
                
                self.log(f'BUY AND HOLD: ${self.data.close[0]:.2f}, Size: {size}') 