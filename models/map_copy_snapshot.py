# -*- coding: utf-8 -*-
"""地図コピー元スナップショットモデル。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapCopySnapshot:
    """地図コピー用に取得した元地図情報を保持するモデル。

    概要:
        取得ボタン押下時点のExtentとexpressionを保持し、
        コピー実行時に再取得せず適用できるようにする。

    引数:
        source_layout_name: 元レイアウト名。
        source_map_item_id: 元地図アイテムID。
        source_occurrence_index: 同一ID内での1始まり出現順。
        source_display_name: 元地図の表示名。
        xmin: Extentのxmin。
        ymin: Extentのymin。
        xmax: Extentのxmax。
        ymax: Extentのymax。
        expression: `dataDefinedMapLayers.expression`。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> snapshot = MapCopySnapshot("LayoutA", "map1", 1, "map1 (#1)", 0.0, 0.0, 1.0, 1.0, "'Road'")
    """

    source_layout_name: str
    source_map_item_id: str
    source_occurrence_index: int
    source_display_name: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    expression: str
