# -*- coding: utf-8 -*-
"""レイアウト情報エクスポートサービス。"""

from __future__ import annotations

from qgis.core import QgsRectangle

from ..models.map_item_record import MapItemRecord
from ..models.operation_result import LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import find_layout_by_name, get_item_expression, get_map_items
from .csv_service import CsvService


class LayoutExportService:
    """既存レイアウトからCSV出力用データを抽出するサービス。

    概要:
        指定レイアウトの地図アイテム情報を収集し、CSVサービスへ受け渡す。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutExportService(csv_service)
    """

    def __init__(self, csv_service: CsvService) -> None:
        """サービスを初期化する。

        概要:
            CSV書き出し処理を委譲する `CsvService` を受け取る。

        引数:
            csv_service: CSVサービス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> service = LayoutExportService(csv_service)
        """
        self._csv_service = csv_service

    def export_layouts(self, layout_names: list[str], csv_path: str) -> OperationResult:
        """指定レイアウト群をCSVへエクスポートする。

        概要:
            レイアウトごとに地図アイテム情報を抽出し、CSVへ書き出す。

        引数:
            layout_names: エクスポート対象レイアウト名一覧。
            csv_path: 出力先CSVパス。

        戻り値:
            OperationResult: エクスポート結果。

        例外:
            なし。

        使用例:
            >>> result = service.export_layouts(["LayoutA"], "/tmp/out.csv")
        """
        result = OperationResult(success=False)
        result.target_layout_count = len(layout_names)

        records: list[MapItemRecord] = []
        for layout_name in layout_names:
            layout = find_layout_by_name(layout_name)
            if layout is None:
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, "レイアウトが見つかりません", layout_name=layout_name))
                continue
            try:
                map_items = get_map_items(layout)
                for map_item in map_items:
                    extent: QgsRectangle = map_item.extent()
                    expression = get_item_expression(map_item)
                    records.append(
                        MapItemRecord(
                            layout_name=layout_name,
                            map_item_id=map_item.id(),
                            xmin=extent.xMinimum(),
                            ymin=extent.yMinimum(),
                            xmax=extent.xMaximum(),
                            ymax=extent.yMaximum(),
                            expression=expression,
                        )
                    )
                result.success_layout_count += 1
            except RuntimeError as exc:
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=layout_name))

        write_result = self._csv_service.write_csv(csv_path=csv_path, records=records)
        result.logs.extend(write_result.logs)
        result.has_warning = result.has_warning or write_result.has_warning
        result.has_error = result.has_error or write_result.has_error
        result.fatal_error = result.fatal_error or write_result.fatal_error

        if write_result.success and result.failed_layout_count == 0:
            result.success = True
        elif write_result.success and result.success_layout_count > 0:
            result.success = True
            result.has_warning = True
        else:
            result.success = False

        return result
