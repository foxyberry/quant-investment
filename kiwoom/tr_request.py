"""Compatibility wrapper for TR request helpers.

This module keeps the phase-document path (`kiwoom/tr_request.py`) while
delegating to the active implementation in `kiwoom/tr.py`.
"""

from kiwoom.tr import KiwoomTrClient, TrRequest

__all__ = ["KiwoomTrClient", "TrRequest"]
