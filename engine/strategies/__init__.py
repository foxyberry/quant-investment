"""
Trading strategies for backtesting
"""
from .ma_cross import SmaCross, EmaCross, MaTouchStrategy
from .graph_strategy import GraphBacktestStrategy

__all__ = ['SmaCross', 'EmaCross', 'MaTouchStrategy', 'GraphBacktestStrategy']
