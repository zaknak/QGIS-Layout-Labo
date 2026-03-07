# -*- coding: utf-8 -*-
"""地図アイテム任意コピーサービス。"""

from __future__ import annotations

from qgis.core import QgsRectangle

from ..models.map_copy_snapshot import MapCopySnapshot
from ..models.map_item_selection import MapItemSelection
from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    find_layout_by_name,
    find_map_item_by_selection,
    get_item_expression,
    set_item_expression,
    set_item_extent,
)


class LayoutMapCopyService:
    """任意地図アイテム間で値をコピーするサービス。

    概要:
        元地図からスナップショットを取得し、コピー先地図へ
        Extentとexpressionを任意選択で適用する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutMapCopyService()
    """

    def fetch_snapshot(
        self,
        source_layout_name: str,
        source_selection: MapItemSelection,
    ) -> tuple[OperationResult, MapCopySnapshot | None]:
        """元地図からコピー用スナップショットを取得する。

        概要:
            指定元レイアウトと地図選択情報を用いて、
            Extentとexpressionを取得しスナップショットとして返す。

        引数:
            source_layout_name: 元レイアウト名。
            source_selection: 元地図選択情報。

        戻り値:
            tuple[OperationResult, MapCopySnapshot | None]:
                処理結果と取得スナップショット。失敗時はNone。

        例外:
            なし。

        使用例:
            >>> result, snapshot = service.fetch_snapshot("LayoutA", selection)
        """
        result = OperationResult(success=False)
        result.target_layout_count = 1
        layout_result = LayoutProcessResult(layout_name=source_layout_name, target_count=1)

        if not source_layout_name:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "元レイアウト未選択です"))
            result.layout_results.append(layout_result)
            return result, None

        try:
            layout = find_layout_by_name(source_layout_name)
        except RuntimeError as exc:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=source_layout_name))
            result.layout_results.append(layout_result)
            return result, None

        if layout is None:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "元レイアウトが見つかりません", layout_name=source_layout_name))
            result.layout_results.append(layout_result)
            return result, None

        try:
            source_map_item = find_map_item_by_selection(layout, source_selection)
            if source_map_item is None:
                result.fatal_error = True
                result.failed_layout_count = 1
                layout_result.has_error = True
                result.add_log(
                    build_log(
                        LogLevel.ERROR,
                        "元地図アイテムが見つかりません",
                        layout_name=source_layout_name,
                        map_item_id=source_selection.map_item_id,
                    )
                )
                result.layout_results.append(layout_result)
                return result, None

            extent = source_map_item.extent()
            expression = get_item_expression(source_map_item)
            snapshot = MapCopySnapshot(
                source_layout_name=source_layout_name,
                source_map_item_id=source_selection.map_item_id,
                source_occurrence_index=source_selection.occurrence_index,
                source_display_name=source_selection.display_name,
                xmin=extent.xMinimum(),
                ymin=extent.yMinimum(),
                xmax=extent.xMaximum(),
                ymax=extent.yMaximum(),
                expression=expression,
            )
        except RuntimeError as exc:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=source_layout_name))
            result.layout_results.append(layout_result)
            return result, None
        except Exception as exc:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, f"元地図情報の取得に失敗しました: {exc}", layout_name=source_layout_name))
            result.layout_results.append(layout_result)
            return result, None

        layout_result.success_count = 1
        result.success_layout_count = 1
        result.success = True
        result.add_log(
            build_log(
                LogLevel.INFO,
                "元地図からスナップショットを取得しました",
                layout_name=source_layout_name,
                map_item_id=source_selection.map_item_id,
            )
        )
        result.layout_results.append(layout_result)
        return result, snapshot

    def apply_snapshot(
        self,
        snapshot: MapCopySnapshot | None,
        target_layout_name: str,
        target_selections: list[MapItemSelection],
        apply_extent: bool,
        apply_expression: bool,
    ) -> OperationResult:
        """スナップショットを指定地図群へ適用する。

        概要:
            取得済みスナップショットをコピー先レイアウトの
            複数地図アイテムへ反映し、結果オブジェクトを返す。

        引数:
            snapshot: 適用元スナップショット。
            target_layout_name: コピー先レイアウト名。
            target_selections: コピー先地図選択情報一覧。
            apply_extent: Extent適用可否。
            apply_expression: expression適用可否。

        戻り値:
            OperationResult: コピー処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.apply_snapshot(snapshot, "LayoutB", selections, True, False)
        """
        result = OperationResult(success=False)
        result.target_layout_count = 1
        layout_result = LayoutProcessResult(layout_name=target_layout_name, target_count=len(target_selections))

        if snapshot is None:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "取得スナップショットがありません"))
            result.layout_results.append(layout_result)
            return result

        if not target_layout_name:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "コピー先レイアウト未選択です"))
            result.layout_results.append(layout_result)
            return result

        if not target_selections:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "コピー先地図アイテム未選択です", layout_name=target_layout_name))
            result.layout_results.append(layout_result)
            return result

        if not apply_extent and not apply_expression:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "コピー対象（EXTENT / expression）が未選択です", layout_name=target_layout_name))
            result.layout_results.append(layout_result)
            return result

        try:
            target_layout = find_layout_by_name(target_layout_name)
        except RuntimeError as exc:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=target_layout_name))
            result.layout_results.append(layout_result)
            return result

        if target_layout is None:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "コピー先レイアウトが見つかりません", layout_name=target_layout_name))
            result.layout_results.append(layout_result)
            return result

        rectangle = QgsRectangle(snapshot.xmin, snapshot.ymin, snapshot.xmax, snapshot.ymax)
        for selection in target_selections:
            map_item_id = selection.map_item_id
            try:
                target_map_item = find_map_item_by_selection(target_layout, selection)
                if target_map_item is None:
                    layout_result.has_warning = True
                    result.add_log(
                        build_log(
                            LogLevel.WARNING,
                            "コピー先地図アイテムが見つかりません",
                            layout_name=target_layout_name,
                            map_item_id=map_item_id,
                        )
                    )
                    continue
                if apply_extent:
                    set_item_extent(target_map_item, rectangle)
                if apply_expression:
                    set_item_expression(target_map_item, snapshot.expression)
                layout_result.success_count += 1
            except RuntimeError as exc:
                layout_result.has_error = True
                result.add_log(
                    build_log(
                        LogLevel.ERROR,
                        str(exc),
                        layout_name=target_layout_name,
                        map_item_id=map_item_id,
                    )
                )

        if layout_result.has_error:
            result.failed_layout_count = 1
        elif layout_result.has_warning:
            result.warning_layout_count = 1
            result.success_layout_count = 1
        else:
            result.success_layout_count = 1

        result.has_warning = result.warning_layout_count > 0
        result.has_error = result.failed_layout_count > 0
        result.success = not result.has_error
        result.layout_results.append(layout_result)
        result.add_log(
            build_log(
                LogLevel.INFO,
                "地図コピー処理が完了しました",
                layout_name=target_layout_name,
            )
        )
        return result
