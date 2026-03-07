# -*- coding: utf-8 -*-
"""既存レイアウトへCSVを適用するサービス。"""

from __future__ import annotations

from qgis.core import QgsRectangle

from ..models.csv_layout_dataset import CsvLayoutDataset
from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    find_layout_by_name,
    get_map_items,
    set_item_expression,
    set_item_extent,
)


class LayoutImportService:
    """CSV情報を既存レイアウトへ適用するサービス。

    概要:
        CSVデータセットを対象レイアウトへ反映し、結果オブジェクトを返す。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutImportService()
    """

    def apply_to_existing_layouts(
        self,
        dataset: CsvLayoutDataset,
        target_layout_names: list[str],
    ) -> OperationResult:
        """CSVデータを既存レイアウトへ適用する。

        概要:
            `layout_name` 完全一致の既存レイアウトへ `itemById()` で適用する。

        引数:
            dataset: CSV全体データ。
            target_layout_names: UIで選択された適用対象レイアウト名一覧。

        戻り値:
            OperationResult: インポート処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.apply_to_existing_layouts(dataset, ["LayoutA"])
        """
        result = OperationResult(success=True)
        result.target_layout_count = len(target_layout_names)

        for layout_name in target_layout_names:
            layout_result = LayoutProcessResult(layout_name=layout_name)
            dataset_layout = dataset.get_layout(layout_name)
            if dataset_layout is None:
                result.warning_layout_count += 1
                layout_result.has_warning = True
                result.add_log(build_log(LogLevel.WARNING, "CSV内に対象レイアウトがありません", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            layout = find_layout_by_name(layout_name)
            if layout is None:
                result.warning_layout_count += 1
                layout_result.has_warning = True
                result.add_log(build_log(LogLevel.WARNING, "プロジェクト内に対象レイアウトがありません", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            try:
                map_items = get_map_items(layout)
            except RuntimeError as exc:
                result.failed_layout_count += 1
                layout_result.has_error = True
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            layout_result.target_count = len(dataset_layout.map_items)
            if len(map_items) != len(dataset_layout.map_items):
                layout_result.has_warning = True
                result.add_log(build_log(LogLevel.WARNING, "地図アイテム数が一致しません", layout_name=layout_name))

            for map_record in dataset_layout.map_items:
                map_item = layout.itemById(map_record.map_item_id)
                if map_item is None:
                    layout_result.has_warning = True
                    result.add_log(
                        build_log(
                            LogLevel.WARNING,
                            "地図アイテムが見つかりません",
                            layout_name=layout_name,
                            map_item_id=map_record.map_item_id,
                            csv_line_no=map_record.source_line_no,
                        )
                    )
                    continue
                try:
                    rectangle = QgsRectangle(map_record.xmin, map_record.ymin, map_record.xmax, map_record.ymax)
                    set_item_extent(map_item, rectangle)
                    set_item_expression(map_item, map_record.expression)
                    layout_result.success_count += 1
                except RuntimeError as exc:
                    layout_result.has_error = True
                    result.add_log(
                        build_log(
                            LogLevel.ERROR,
                            str(exc),
                            layout_name=layout_name,
                            map_item_id=map_record.map_item_id,
                            csv_line_no=map_record.source_line_no,
                        )
                    )

            if layout_result.has_error:
                result.failed_layout_count += 1
            elif layout_result.has_warning:
                result.warning_layout_count += 1
                result.success_layout_count += 1
            else:
                result.success_layout_count += 1

            result.layout_results.append(layout_result)

        result.has_warning = result.warning_layout_count > 0
        result.has_error = result.failed_layout_count > 0
        result.success = not result.has_error
        result.add_log(build_log(LogLevel.INFO, "インポート処理が完了しました"))
        return result
