# -*- coding: utf-8 -*-
"""レイアウト単位データモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .map_item_record import MapItemRecord


@dataclass
class LayoutRecord:
    """1レイアウト分の地図アイテム群を表すモデル。

    概要:
        同一 `layout_name` を持つ地図アイテムレコードを束ねる。

    引数:
        layout_name: レイアウト名。
        map_items: 地図アイテムデータ一覧。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> layout = LayoutRecord(layout_name="LayoutA")
    """

    layout_name: str
    map_items: list[MapItemRecord] = field(default_factory=list)

    def add_item(self, record: MapItemRecord) -> None:
        """地図アイテムを追加する。

        概要:
            レイアウト配下の地図アイテム一覧へ1件追加する。

        引数:
            record: 追加対象の地図アイテムデータ。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> layout.add_item(record)
        """
        self.map_items.append(record)
