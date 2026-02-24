"""Compatibility wrapper for screen number allocator.

This module keeps the phase-document path (`kiwoom/screen_manager.py`) while
delegating to the active implementation in `kiwoom/realtime.py`.
"""

from kiwoom.realtime import ScreenManager

__all__ = ["ScreenManager"]
