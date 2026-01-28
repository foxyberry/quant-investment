"""
Watchlist Model
관심종목 관리 모델

Usage:
    from models.watchlist import Watchlist

    watchlist = Watchlist()
    watchlist.add("005930.KS", name="삼성전자", note="240일선 근접", tags=["korean", "tech"])
    watchlist.add("AAPL", name="Apple", tags=["us", "tech"])

    # Get all
    all_stocks = watchlist.get_all()

    # Filter by tag
    korean = watchlist.filter(tag="korean")

    # Remove
    watchlist.remove("005930.KS")
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import yaml


@dataclass
class WatchlistItem:
    """관심종목 항목"""
    ticker: str
    name: Optional[str] = None
    note: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    added_at: Optional[str] = None
    conditions: List[Dict[str, Any]] = field(default_factory=list)  # 연결된 조건들

    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "note": self.note,
            "tags": self.tags,
            "added_at": self.added_at,
            "conditions": self.conditions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchlistItem":
        return cls(
            ticker=data["ticker"],
            name=data.get("name"),
            note=data.get("note"),
            tags=data.get("tags", []),
            added_at=data.get("added_at"),
            conditions=data.get("conditions", []),
        )


class Watchlist:
    """관심종목 관리 클래스"""

    DEFAULT_PATH = Path(__file__).parent.parent / "config" / "watchlist.yaml"

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = Path(filepath) if filepath else self.DEFAULT_PATH
        self._items: Dict[str, WatchlistItem] = {}
        self._load()

    def _load(self):
        """파일에서 로드"""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                items = data.get("watchlist", [])
                for item_data in items:
                    item = WatchlistItem.from_dict(item_data)
                    self._items[item.ticker] = item
            except Exception as e:
                print(f"Warning: Failed to load watchlist: {e}")

    def _save(self):
        """파일에 저장"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "watchlist": [item.to_dict() for item in self._items.values()]
        }

        with open(self.filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def add(
        self,
        ticker: str,
        name: Optional[str] = None,
        note: Optional[str] = None,
        tags: Optional[List[str]] = None,
        conditions: Optional[List[Dict]] = None
    ) -> WatchlistItem:
        """
        관심종목 추가

        Args:
            ticker: 종목 코드
            name: 종목명
            note: 메모
            tags: 태그 목록
            conditions: 연결된 조건들

        Returns:
            추가된 WatchlistItem
        """
        item = WatchlistItem(
            ticker=ticker,
            name=name,
            note=note,
            tags=tags or [],
            conditions=conditions or [],
        )
        self._items[ticker] = item
        self._save()
        return item

    def remove(self, ticker: str) -> bool:
        """
        관심종목 삭제

        Args:
            ticker: 종목 코드

        Returns:
            삭제 성공 여부
        """
        if ticker in self._items:
            del self._items[ticker]
            self._save()
            return True
        return False

    def get(self, ticker: str) -> Optional[WatchlistItem]:
        """특정 종목 조회"""
        return self._items.get(ticker)

    def get_all(self) -> List[str]:
        """모든 종목 코드 목록"""
        return list(self._items.keys())

    def get_all_items(self) -> List[WatchlistItem]:
        """모든 종목 항목 목록"""
        return list(self._items.values())

    def filter(self, tag: Optional[str] = None) -> List[WatchlistItem]:
        """
        태그로 필터링

        Args:
            tag: 필터링할 태그

        Returns:
            필터링된 종목 목록
        """
        if tag is None:
            return self.get_all_items()

        return [item for item in self._items.values() if tag in item.tags]

    def update(
        self,
        ticker: str,
        name: Optional[str] = None,
        note: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[WatchlistItem]:
        """
        관심종목 정보 업데이트

        Args:
            ticker: 종목 코드
            name: 새 종목명 (None이면 변경 안함)
            note: 새 메모 (None이면 변경 안함)
            tags: 새 태그 목록 (None이면 변경 안함)

        Returns:
            업데이트된 WatchlistItem (없으면 None)
        """
        if ticker not in self._items:
            return None

        item = self._items[ticker]
        if name is not None:
            item.name = name
        if note is not None:
            item.note = note
        if tags is not None:
            item.tags = tags

        self._save()
        return item

    def __contains__(self, ticker: str) -> bool:
        return ticker in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items.values())
