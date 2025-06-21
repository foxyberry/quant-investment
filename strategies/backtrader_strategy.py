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
        'timeout_days': 10,
        'position_size': 0.5,
        'debug': False,
        'verbose_logging': True,  # Enable detailed trade logging
        'start_date': None,
        'end_date': None,
        'symbol': 'UNKNOWN',  # Default symbol name
    }
    
    def __init__(self, **kwargs):
        # Merge default params with provided kwargs
        self.params = self.default_params.copy()
        self.params.update(kwargs)
        
        # Internal state
        self.entry_price = None
        self.entry_date = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
        # Track which symbols currently have positions or pending orders
        # This prevents buying more of the same stock until it's sold
        self.held_symbols = set()  # Store symbol names
        self.pending_orders = {}  # Store pending orders {order_id: symbol}
        
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
        self.log2("=== BottomBreakoutStrategy Initialized ===", level=logging.INFO)
        self.log2(f"Parameters: lookback_days={self.params['lookback_days']}, "
                f"breakout_threshold={self.params['breakout_threshold']:.1%}, "
                f"take_profit_threshold={self.params['take_profit_threshold']:.1%}, "
                f"stop_loss_threshold={self.params['stop_loss_threshold']:.1%}, "
                f"start_date={self.params['start_date'].date() if self.params['start_date'] else 'None'}, "
                f"timeout_days={self.params['timeout_days']}, "
                f"position_size={self.params['position_size']:.1%}, "
                f"end_date={self.params['end_date'].date() if self.params['end_date'] else 'None'}",
                level=logging.INFO)

    def _log(self, prefix: str, txt: str, level: int = logging.INFO):
        message = f'{prefix}: {txt}'
        if self.params['debug'] or self.params['verbose_logging']:
            print(message)
        self.logger.log(level, message)
        
    def log(self, txt, dt=None, level=logging.INFO):
        dt = dt or self.datas[0].datetime.date(0)
        self._log(dt.isoformat(), txt, level)

    def log2(self, txt, level=logging.INFO):
        self._log("Default", txt, level)
        

    def start(self):
        """Called when strategy starts"""
        self.log2("=== Strategy Started ===", level=logging.INFO)
        self.log2(f"Initial cash: ${self.broker.getcash():,.2f}", level=logging.INFO)

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
        
        # Show held symbols summary
        if self.held_symbols:
            self.log(f"Symbols held during strategy: {len(self.held_symbols)}", level=logging.INFO)
            for symbol in sorted(self.held_symbols):
                self.log(f"  - {symbol}", level=logging.DEBUG)
        else:
            self.log("No symbols were held during this period", level=logging.INFO)

    def get_held_symbols_status(self):
        """Helper method to get current held symbols status for debugging"""
        return {
            'count': len(self.held_symbols),
            'symbols': list(self.held_symbols),
            'pending_orders': len(self.pending_orders)
        }
    
    def notify_order(self, order):
        """Called when order status changes"""
        if order.status in [order.Completed]:
            # Order completed successfully
            if order.isbuy():
                symbol = self.pending_orders.get(order.ref, self.datas[0]._name or "UNKNOWN")
                self.log(f"✅ BUY ORDER COMPLETED - {symbol} at ${order.executed.price:.2f}, Size: {order.executed.size}", 
                        level=logging.INFO)
            elif order.issell():
                symbol = self.pending_orders.get(order.ref, self.datas[0]._name or "UNKNOWN")
                self.log(f"✅ SELL ORDER COMPLETED - {symbol} at ${order.executed.price:.2f}, Size: {order.executed.size}", 
                        level=logging.INFO)
                
                # Now that sell order is completed, clean up tracking
                if symbol in self.held_symbols:
                    self.held_symbols.remove(symbol)
                    self.log(f"🔓 Cleared held symbol {symbol} - allowing re-entry", 
                            level=logging.INFO)
                
                # Reset position tracking state
                self.entry_price = None
                self.entry_date = None
                self.stop_loss_price = None
                self.take_profit_price = None
                self.log(f"🔄 Reset position tracking state", level=logging.INFO)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Order failed - clean up tracking
            if order.ref in self.pending_orders:
                symbol = self.pending_orders[order.ref]
                self.log(f"❌ ORDER FAILED - {symbol}: {order.getstatusname()}", level=logging.WARNING)
                
                # For failed buy orders, remove from held symbols
                if order.isbuy() and symbol in self.held_symbols:
                    self.held_symbols.remove(symbol)
                    self.log(f"🔓 Cleared held symbol {symbol} due to failed buy order", 
                            level=logging.INFO)
                    
        # Clean up pending orders tracking
        if order.ref in self.pending_orders:
            del self.pending_orders[order.ref]

    def next(self):
        data = self.datas[0]
        current_date = data.datetime.date(0)

        current_price = data.close[0]
        current_volume = data.volume[0]
        
        
        # Track portfolio value
        portfolio_value = self.broker.getvalue()
        self.portfolio_values.append(portfolio_value)

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


        bottom_price = min(lookback_lows)
        bottom_price_index = lookback_lows.index(bottom_price)  # Index in lookback_lows list
        
        days_ago = bottom_price_index + 1
        bottom_date = data.datetime.date(-days_ago)  # Negative index to go back in time
        
        bottom_to_current_pct = ((current_price - bottom_price) / bottom_price) * 100
                
        volume_lookback = min(10, len(data) - 1)  
        if volume_lookback > 0:
            recent_volumes = [data.volume[-i] for i in range(1, volume_lookback + 1)]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        else: 
            avg_volume = current_volume
            volume_ratio = 1.0


        breakout_price = bottom_price * self.params['breakout_threshold'] 
               
        # Daily market status log (only if verbose logging enabled)
        if self.params['verbose_logging'] :
            if self.position.size > 0:
                self.log(f"============ Market Analysis - Price: ${current_price:.2f}, Position Size: {self.position.size}",
                    level=logging.DEBUG)
            else :
                self.log(f"============ Market Analysis - Price: ${current_price:.2f}, "
                    f"Bottom: ${bottom_price:.2f} on {bottom_date} ({days_ago} days ago, {bottom_to_current_pct:+.1f}%), "
                    f"Breakout: ${breakout_price:.2f}, "
                    f"Volume: {current_volume:,.0f} ({volume_ratio:.1f}x (avg))", 
                    level=logging.DEBUG)

        # === BUY Logic - First Breakout Only ===
        # Check if we have no position AND no pending orders for this symbol
        if self.position.size == 0:
            
            is_breakout_today = current_price >= breakout_price
            was_recently_below = any(close < breakout_price for close in lookback_lows)
            
            is_fresh_breakout = is_breakout_today and was_recently_below
        
            if not is_fresh_breakout:
                if is_breakout_today and not was_recently_below:
                    message = "BREAKOUT NOT FRESH"
                if not is_breakout_today and was_recently_below:
                    message = "NOT TODAY BREAKOUT"
                else :
                    message = "NOT ENOUGH CONDITION"
                    
                self.log(message, level=logging.DEBUG)
                if self.params['verbose_logging']:
                    self.log(f"⚠️ SKIPPING BUY - {message}", 
                            level=logging.DEBUG)
                    self.log(f"   Current: ${current_price:.2f}, Breakout: ${breakout_price:.2f}", 
                            level=logging.DEBUG)
                    self.log(f"   Bottom (5-day): ${bottom_price:.2f}", 
                            level=logging.DEBUG)
                return
            
            
            symbol = data._name or "UNKNOWN"

            
            if symbol in self.held_symbols:
                if self.params['verbose_logging']:
                    self.log(f"⚠️ SKIPPING BUY - Already holding {symbol}", 
                            level=logging.INFO)
                    self.log(f"   Current price: ${current_price:.2f}, Breakout: ${breakout_price:.2f}", 
                            level=logging.DEBUG)
                return
            
            
            available_cash = self.broker.getcash()
            size = int((available_cash * self.params['position_size']) / current_price)

            if size > 0:
                
                if volume_ratio >= self.params['volume_threshold']:
    
                    order = self.buy(size=size)
                    
                    # Track pending order to prevent duplicate buys
                    if order:
                        self.pending_orders[order.ref] = symbol
                    
                    # Set entry tracking (will be confirmed when order executes)
                    self.entry_price = current_price
                    self.entry_date = current_date
                    
                    self.stop_loss_price = bottom_price * self.params['stop_loss_threshold']
                    self.take_profit_price = current_price * self.params['take_profit_threshold']
                    
                    # Mark this symbol as held (preventing further buys)
                    self.held_symbols.add(symbol)
                    
                    self.total_trades += 1
                    
                    # Enhanced buy logging
                    self.log(f"🚀 BUY EXECUTED - FIRST BREAKOUT!", level=logging.INFO)
                    self.log(f"   💰 Symbol: {symbol}", level=logging.INFO)
                    self.log(f"   💵 Price: ${current_price:.2f} (Size: {size} shares, ${size * current_price:,.2f})", 
                            level=logging.INFO)
                    self.log(f"   📊 5-Day Bottom: ${bottom_price:.2f}", level=logging.INFO)
                    self.log(f"   📈 Breakout: ${breakout_price:.2f} ({self.params['breakout_threshold']:.1%})", 
                            level=logging.INFO)
                    self.log(f"   📊 Volume: {current_volume:,.0f} ({volume_ratio:.2f}x avg, threshold: {self.params['volume_threshold']:.2f}x)", 
                            level=logging.INFO)
                    self.log(f"   🛡️ Stop loss: ${self.stop_loss_price:.2f} (5% below 5-day bottom)", 
                            level=logging.INFO)
                    self.log(f"   🎯 Take profit: ${self.take_profit_price:.2f} ({self.params['take_profit_threshold']:.1%} above entry)", 
                            level=logging.INFO)
                    self.log(f"   ⏰ Timeout: {current_date + timedelta(days=10)} (10 days)", level=logging.INFO)
                    self.log(f"   🔒 Marked {symbol} as held (no additional buys until sold)", level=logging.INFO)

                    # Record signal
                    self.signals.append({
                        'date': current_date,
                        'action': 'BUY',
                        'price': current_price,
                        'size': size,
                        'bottom_price': bottom_price,  # Use 5-day bottom
                        'bottom_date': None,  # We don't track the specific date for 5-day bottom
                        'days_from_bottom': None,
                        'breakout_price': breakout_price,
                        'volume_ratio': volume_ratio,
                        'portfolio_value': portfolio_value
                    })
                else:
                    self.log(f"⚠️ SKIPPING BUY - Volume ratio below threshold ({volume_ratio:.1f}x < {self.params['volume_threshold']:.1f}x)", 
                            level=logging.DEBUG)

        # === SELL Logic ===
        elif self.position.size > 0:
            sell_signal = False
            sell_reason = ""
            
            # Safety check: ensure entry_date and entry_price are set
            if self.entry_date is None or self.entry_price is None:
                self.log(f"⚠️ WARNING: Position exists but entry tracking missing. Skipping sell logic this bar.", 
                        level=logging.WARNING)
                self.log(f"   Position size: {self.position.size}, Current price: ${current_price:.2f}", 
                        level=logging.WARNING)
                # Don't reset tracking here - this could cause incorrect sells
                # Instead, skip this bar and wait for proper state
                return
            
            days_held = (current_date - self.entry_date).days
            current_return_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            
            # Analyze exit conditions - with proper null checks
            if self.stop_loss_price is not None and current_price <= self.stop_loss_price:
                sell_signal = True
                sell_reason = "STOP_LOSS"
                self.log(f"🛑 STOP LOSS TRIGGERED! Price ${current_price:.2f} <= ${self.stop_loss_price:.2f}", 
                        level=logging.WARNING)

            elif self.take_profit_price is not None and current_price >= self.take_profit_price:
                sell_signal = True
                sell_reason = "TAKE_PROFIT"
                self.log(f"🎯 TAKE PROFIT TRIGGERED! Price ${current_price:.2f} >= TAKE PROFIT ${self.take_profit_price:.2f}", 
                        level=logging.INFO)

            elif (self.entry_price is not None and current_price > self.entry_price and 
                  current_date > self.entry_date + timedelta(days=10)):
                sell_signal = True
                sell_reason = "TIME_OUT"
                self.log(f"⏰ TIMEOUT TRIGGERED! Held for {days_held} days with {current_return_pct:+.2f}% return", 
                        level=logging.INFO)
            
            # Daily position status (only if verbose logging and no sell signal)
            elif self.params['verbose_logging']:
                self.log(f"📊 Position Status - Days held: {days_held}, "
                        f"Current: ${current_price:.2f} ({current_return_pct:+.2f}%), "
                        f"Stop Lost: ${self.stop_loss_price:.2f}, "
                        f"Target Take Profit: ${self.take_profit_price:.2f}", 
                        level=logging.DEBUG)

            # Execute sell if conditions met
            if sell_signal:
                # Sell the entire position
                order = self.sell(size=self.position.size)
                
                # Track pending sell order
                if order:
                    symbol = data._name or "UNKNOWN"
                    self.pending_orders[order.ref] = symbol
                
                # Update trade statistics
                if current_return_pct > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                # Enhanced sell logging
                symbol = data._name or "UNKNOWN"
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

                # Note: Don't clear held_symbols or reset tracking here!
                # This will be done in notify_order() when the sell order is actually completed
                # to prevent timing issues with position tracking

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