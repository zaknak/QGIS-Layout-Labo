# -*- coding: utf-8 -*-
"""地図アイテム1件分データモデル。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapItemRecord:
    """CSV1行相当の地図アイテム情報を表すモデル。

    概要:
        レイアウト名、地図アイテムID、Extent、expression を保持する。

    引数:
        layout_name: レイアウト名。
        map_item_id: 地図アイテムID。
        xmin: Extentのxmin。
        ymin: Extentのymin。
        xmax: Extentのxmax。
        ymax: Extentのymax。
        expression: dataDefinedMapLayers.expression。
        source_line_no: 元CSV行番号（1始まり、任意）。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> record = MapItemRecord("LayoutA", "map1", 0.0, 0.0, 10.0, 10.0, "'Road'")
    """

    layout_name: str
    map_item_id: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    expression: str
    source_line_no: int | None = None
