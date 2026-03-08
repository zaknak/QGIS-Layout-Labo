# -*- coding: utf-8 -*-
"""プロジェクト参照系サービス。"""

from __future__ import annotations

from ..models.map_item_selection import MapItemSelection
from ..models.operation_result import LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    get_layout_map_item_selections,
    get_project_layer_names_in_tree_order,
    get_project_layout_name_with_map_item_counts,
)


class ProjectQueryService:
    """プロジェクト状態の参照系処理を提供するサービス。

    概要:
        UI層からQGIS API呼び出しを分離するため、
        レイアウト一覧、地図アイテム選択候補、レイヤ一覧の取得を担当する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = ProjectQueryService()
    """

    def load_layout_name_with_map_item_counts(self) -> tuple[OperationResult, list[tuple[str, int]]]:
        """レイアウト名と地図アイテム数を取得する。

        概要:
            現在プロジェクトのレイアウト情報を取得し、
            `(layout_name, map_item_count)` の一覧として返す。

        引数:
            なし。

        戻り値:
            tuple[OperationResult, list[tuple[str, int]]]:
                処理結果とレイアウト情報一覧。

        例外:
            なし。

        使用例:
            >>> result, entries = service.load_layout_name_with_map_item_counts()
        """
        result = OperationResult(success=False)
        try:
            entries = get_project_layout_name_with_map_item_counts()
        except RuntimeError as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc)))
            return result, []

        result.success = True
        result.target_layout_count = len(entries)
        return result, entries

    def load_map_item_selections(self, layout_name: str) -> tuple[OperationResult, list[MapItemSelection]]:
        """指定レイアウトの地図アイテム選択候補を取得する。

        概要:
            同一ID重複を含む地図アイテムを
            `MapItemSelection` 一覧として返す。

        引数:
            layout_name: 対象レイアウト名。

        戻り値:
            tuple[OperationResult, list[MapItemSelection]]:
                処理結果と地図アイテム選択候補一覧。

        例外:
            なし。

        使用例:
            >>> result, selections = service.load_map_item_selections("LayoutA")
        """
        result = OperationResult(success=False)
        if not layout_name:
            result.success = True
            return result, []

        try:
            selections = get_layout_map_item_selections(layout_name)
        except RuntimeError as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc)))
            return result, []

        result.success = True
        result.target_layout_count = 1
        return result, selections

    def load_layer_names_in_tree_order(self) -> tuple[OperationResult, list[str]]:
        """レイヤパネル順のレイヤ名一覧を取得する。

        概要:
            現在プロジェクトのレイヤ名をレイヤツリー順で返す。

        引数:
            なし。

        戻り値:
            tuple[OperationResult, list[str]]:
                処理結果とレイヤ名一覧。

        例外:
            なし。

        使用例:
            >>> result, layers = service.load_layer_names_in_tree_order()
        """
        result = OperationResult(success=False)
        try:
            layer_names = get_project_layer_names_in_tree_order()
        except RuntimeError as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc)))
            return result, []

        result.success = True
        return result, layer_names
