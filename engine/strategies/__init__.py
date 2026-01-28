"""
Trading strategies for backtesting
"""
from .ma_cross import SmaCross, EmaCross, MaTouchStrategy

__all__ = ['SmaCross', 'EmaCross', 'MaTouchStrategy']
