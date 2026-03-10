# -*- coding: utf-8 -*-
"""地図アイテム選択情報モデル。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapItemSelection:
    """UI選択用の地図アイテム識別情報を表すモデル。

    概要:
        同一ID重複時でも地図アイテムを一意に扱えるよう、
        `map_item_id` と出現順を保持し、UI表示用の
        表示レイヤ設定モードも保持する。

    引数:
        map_item_id: 地図アイテムID。
        occurrence_index: 同一ID内での1始まり出現順。
        layer_display_mode: 表示レイヤ設定モード。
        layer_display_expression: `式` モード時に表示するexpression。
        display_name: UI表示名。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> selection = MapItemSelection("map1", 1, "既定", "", "map1 (#1) [既定]")
    """

    map_item_id: str
    occurrence_index: int
    layer_display_mode: str
    layer_display_expression: str
    display_name: str
