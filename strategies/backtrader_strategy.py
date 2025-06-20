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
    
    # Default parameters as dictionary
    default_params = {
        'volume_threshold': 1.5,
        'lookback_days': 20,  # Default value, should be overridden by config
        'breakout_threshold': 1.05,
        'take_profit_threshold': 1.1,
        'stop_loss_threshold': 0.95,
        'position_size': 0.5,
        'debug': False,
        'verbose_logging': True,  # Enable detailed trade logging
        'start_date': None,
        'end_date': None,
    }
    
    def __init__(self, **kwargs):
        # Merge default params with provided kwargs
        self.params = self.default_params.copy()
        self.params.update(kwargs)
        
        # Internal state
        self.in_position = False
        self.entry_price = None
        self.entry_date = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
        # Track which bottom prices we've already bought at
        # This prevents re-buying the same stock at the same bottom level
        self.bought_bottoms = set()  # Store (symbol, bottom_price) tuples
        
        # Record keeping
        self.signals = []
        self.trades = []
        self.portfolio_values = []
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Logger
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Strategy initialization log
        self.log("=== BottomBreakoutStrategy Initialized ===", level=logging.INFO)
        self.log(f"Parameters: lookback_days={self.params['lookback_days']}, "
                f"breakout_threshold={self.params['breakout_threshold']:.1%}, "
                f"take_profit_threshold={self.params['take_profit_threshold']:.1%}, "
                f"stop_loss_threshold={self.params['stop_loss_threshold']:.1%}", level=logging.INFO)

    def log(self, txt, dt=None, level=logging.INFO):

        prefix = dt.isoformat() if dt else "Default"
        message = f'{prefix}: {txt}'

        if self.params['debug'] or self.params['verbose_logging']:
            print(message)
        self.logger.log(level, message)

    def start(self):
        """Called when strategy starts"""
        self.log("=== Strategy Started ===", level=logging.INFO)
        self.log(f"Initial cash: ${self.broker.getcash():,.2f}", level=logging.INFO)

    def stop(self):
        """Called when strategy ends"""
        final_value = self.broker.getvalue()
        total_return = ((final_value - 100000) / 100000) * 100  # Assuming 100k initial
        
        self.log("=== Strategy Completed ===", level=logging.INFO)
        self.log(f"Final portfolio value: ${final_value:,.2f}", level=logging.INFO)
        self.log(f"Total return: {total_return:.2f}%", level=logging.INFO)
        self.log(f"Total trades: {self.total_trades}", level=logging.INFO)
        self.log(f"Winning trades: {self.winning_trades}", level=logging.INFO)
        self.log(f"Losing trades: {self.losing_trades}", level=logging.INFO)
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            self.log(f"Win rate: {win_rate:.1f}%", level=logging.INFO)
        
        # Show bought bottoms summary
        if self.bought_bottoms:
            self.log(f"Bought bottoms tracked: {len(self.bought_bottoms)}", level=logging.INFO)
            print(self.bought_bottoms)
            for symbol, bottom_price in sorted(self.bought_bottoms):
                self.log(f"  - {symbol}: ${bottom_price:.2f}", level=logging.DEBUG)
        else:
            self.log("No bottoms were bought during this period", level=logging.INFO)

    def get_bought_bottoms_status(self):
        """Helper method to get current bought bottoms status for debugging"""
        return {
            'count': len(self.bought_bottoms),
            'bottoms': list(self.bought_bottoms)
        }

    def next(self):
        data = self.datas[0]
        current_date = data.datetime.date(0)

        if(self.params['start_date'] and self.params['start_date'].date() > current_date):
            self.log(f"Waiting for start date: {self.params['start_date']} > {current_date}", level=logging.INFO)
            return
        
        current_price = data.close[0]
        current_volume = data.volume[0]
        
        # Track portfolio value
        portfolio_value = self.broker.getvalue()
        self.portfolio_values.append(portfolio_value)

        # Skip if not enough historical data to calculate lookback bottom
        # We need at least lookback_days of data BEFORE the current date
        if len(data) < self.params['lookback_days'] + 1:  # +1 because we need current day plus lookback days
            if self.params['verbose_logging']:
                self.log(f"Waiting for sufficient historical data ({len(data)}/{self.params['lookback_days'] + 1} days)", 
                        level=logging.DEBUG)
            return

        # Get lookback low prices (excluding current day)
        # data.low[-1] is yesterday, data.low[-2] is day before yesterday, etc.
        try:
            lookback_lows = [data.low[-i] for i in range(1, self.params['lookback_days'] + 1)]
        except IndexError:
            # Safety check - if we can't access enough historical data, skip
            if self.params['verbose_logging']:
                self.log(f"Cannot access {self.params['lookback_days']} days of historical data", 
                        level=logging.DEBUG)
            return
        
        if not lookback_lows:
            return

        # Market analysis
        bottom_price = min(lookback_lows)
        
        # Find the date when the bottom price occurred
        bottom_price_index = lookback_lows.index(bottom_price)  # Index in lookback_lows list
        # Convert to actual date: lookback_lows[0] is data.low[-1] (yesterday), so add 1
        days_ago = bottom_price_index + 1
        bottom_date = data.datetime.date(-days_ago)  # Negative index to go back in time
        
        breakout_price = bottom_price * self.params['breakout_threshold']
        bottom_to_current_pct = ((current_price - bottom_price) / bottom_price) * 100
        
        # Volume analysis (last 10 days excluding current day)
        volume_lookback = min(10, len(data) - 1)  # Don't include current day, max 10 days
        if volume_lookback > 0:
            recent_volumes = [data.volume[-i] for i in range(1, volume_lookback + 1)]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        else:
            # Not enough volume history, use current volume as baseline
            avg_volume = current_volume
            volume_ratio = 1.0

        # Daily market status log (only if verbose logging enabled)
        if self.params['verbose_logging'] and not self.position:
            self.log(f"Market Analysis - Price: ${current_price:.2f}, "
                    f"Bottom: ${bottom_price:.2f} on {bottom_date} ({days_ago} days ago, {bottom_to_current_pct:+.1f}%), "
                    f"Breakout: ${breakout_price:.2f}, "
                    f"Volume: {current_volume:,.0f} ({volume_ratio:.1f}x avg)", 
                    level=logging.DEBUG)

        # === BUY Logic - First Breakout Only ===
        if not self.position and current_price > breakout_price:
            # Check if this is the FIRST breakout (yesterday was below breakout, today is above)
            yesterday_price = data.close[-1]  # Yesterday's closing price
            is_first_breakout = yesterday_price <= breakout_price and current_price > breakout_price
            
            if not is_first_breakout:
                if self.params['verbose_logging']:
                    self.log(f"⚠️ SKIPPING BUY - Not first breakout (Yesterday: ${yesterday_price:.2f}, "
                            f"Today: ${current_price:.2f}, Breakout: ${breakout_price:.2f})", 
                            level=logging.DEBUG)
                return
            
            # Get current symbol name for tracking
            symbol = self.datas[0]._name if hasattr(self.datas[0], '_name') else 'UNKNOWN'
            
            bottom_key = (symbol, round(bottom_price, 2))

            if bottom_key in self.bought_bottoms:
                if self.params['verbose_logging']:
                    self.log(f"⚠️ SKIPPING BUY - Already bought {symbol} at bottom ${bottom_price:.2f}", 
                            level=logging.INFO)
                    self.log(f"   Current price: ${current_price:.2f}, Breakout: ${breakout_price:.2f}", 
                            level=logging.DEBUG)
                return
            
            # Calculate position size
            available_cash = self.broker.getcash()
            size = int((available_cash * self.params['position_size']) / current_price)
            
            if size > 0:
                # Volume condition check
                if volume_ratio >= self.params['volume_threshold']:
                    # Execute buy order
                    order = self.buy(size=size)
                    
                    # Record entry details
                    self.in_position = True
                    self.entry_price = current_price
                    self.entry_date = current_date
                    self.stop_loss_price = bottom_price * self.params['stop_loss_threshold']
                    self.take_profit_price = current_price * self.params['take_profit_threshold']
                    
                    # Add this bottom to bought bottoms set
                    self.bought_bottoms.add(bottom_key)
                    
                    # Update trade statistics
                    self.total_trades += 1
                    
                    # Enhanced buy logging
                    self.log(f"🚀 BUY EXECUTED - FIRST BREAKOUT!", level=logging.INFO)
                    self.log(f"   💰 Symbol: {symbol}", level=logging.INFO)
                    self.log(f"   💵 Price: ${current_price:.2f} (Size: {size} shares, ${size * current_price:,.2f})", 
                            level=logging.INFO)
                    self.log(f"   📊 Bottom: ${bottom_price:.2f} on {bottom_date} ({days_ago} days ago)", 
                            level=logging.INFO)
                    self.log(f"   📈 Breakout: ${breakout_price:.2f} ({self.params['breakout_threshold']:.1%})", 
                            level=logging.INFO)
                    self.log(f"   📊 Volume: {current_volume:,.0f} ({volume_ratio:.1f}x avg, threshold: {self.params['volume_threshold']:.1f}x)", 
                            level=logging.INFO)
                    self.log(f"   🛡️ Stop loss: ${self.stop_loss_price:.2f} ({self.params['stop_loss_threshold']:.1%})", 
                            level=logging.INFO)
                    self.log(f"   🎯 Take profit: ${self.take_profit_price:.2f} ({self.params['take_profit_threshold']:.1%})", 
                            level=logging.INFO)
                    self.log(f"   ⏰ Timeout: {current_date + timedelta(days=10)} (10 days)", level=logging.INFO)
                    self.log(f"   🔒 Marked bottom ${bottom_price:.2f} as bought (no re-buy)", level=logging.INFO)

                    # Record signal
                    self.signals.append({
                        'date': current_date,
                        'action': 'BUY',
                        'price': current_price,
                        'size': size,
                        'bottom_price': bottom_price,
                        'bottom_date': bottom_date,
                        'days_from_bottom': days_ago,
                        'breakout_price': breakout_price,
                        'volume_ratio': volume_ratio,
                        'portfolio_value': portfolio_value
                    })

        # === SELL Logic ===
        elif self.position:
            sell_signal = False
            sell_reason = ""
            days_held = (current_date - self.entry_date).days
            current_return_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            # Analyze exit conditions
            if current_price <= self.stop_loss_price:
                sell_signal = True
                sell_reason = "STOP_LOSS"
                self.log(f"🛑 STOP LOSS TRIGGERED! Price ${current_price:.2f} <= ${self.stop_loss_price:.2f}", 
                        level=logging.WARNING)

            elif current_price >= self.take_profit_price:
                sell_signal = True
                sell_reason = "TAKE_PROFIT"
                self.log(f"🎯 TAKE PROFIT TRIGGERED! Price ${current_price:.2f} >= ${self.take_profit_price:.2f}", 
                        level=logging.INFO)

            elif current_price > self.entry_price and current_date > self.entry_date + timedelta(days=10):
                sell_signal = True
                sell_reason = "TIME_OUT"
                self.log(f"⏰ TIMEOUT TRIGGERED! Held for {days_held} days with {current_return_pct:+.2f}% return", 
                        level=logging.INFO)
            
            # Daily position status (only if verbose logging and no sell signal)
            elif self.params['verbose_logging']:
                self.log(f"📊 Position Status - Days held: {days_held}, "
                        f"Current: ${current_price:.2f} ({current_return_pct:+.2f}%), "
                        f"Stop: ${self.stop_loss_price:.2f}, "
                        f"Target: ${self.take_profit_price:.2f}", 
                        level=logging.DEBUG)

            # Execute sell if conditions met
            if sell_signal:
                order = self.sell()
                
                # Update trade statistics
                if current_return_pct > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                # Enhanced sell logging
                symbol = self.datas[0]._name if hasattr(self.datas[0], '_name') else 'UNKNOWN'
                self.log(f"💸 SELL EXECUTED - {sell_reason}!", level=logging.INFO)
                self.log(f"   💰 Symbol: {symbol}", level=logging.INFO)
                self.log(f"   💵 Entry: ${self.entry_price:.2f} on {self.entry_date}", level=logging.INFO)
                self.log(f"   💵 Exit: ${current_price:.2f} on {current_date}", level=logging.INFO)
                self.log(f"   📊 Return: {current_return_pct:+.2f}% over {days_held} days", level=logging.INFO)
                self.log(f"   📈 P&L: ${(current_price - self.entry_price) * self.position.size:+,.2f}", 
                        level=logging.INFO)

                # Record trade
                self.trades.append({
                    'entry_date': self.entry_date,
                    'exit_date': current_date,
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'return_pct': current_return_pct,
                    'days_held': days_held,
                    'reason': sell_reason,
                    'size': self.position.size
                })

                # Reset position state
                self.in_position = False
                self.entry_price = None
                self.entry_date = None
                self.stop_loss_price = None
                self.take_profit_price = None

class SimpleBuyHoldStrategy(bt.Strategy):
    """
    Simple buy and hold strategy for comparison
    """
    
    # Default parameters as dictionary
    default_params = {
        'debug': False,  # Enable debug logging
    }
    
    def __init__(self, **kwargs):
        # Merge default params with provided kwargs
        self.params = self.default_params.copy()
        self.params.update(kwargs)
        
        self.bought = False
        self.trades = []
        self.portfolio_values = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    def log(self, txt, dt=None, level=logging.INFO):
        """Unified logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        message = f'{dt.isoformat()}: {txt}'
        
        if self.params['debug']:
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