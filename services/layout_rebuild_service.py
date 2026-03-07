# -*- coding: utf-8 -*-
"""テンプレートを使ったレイアウト再作成サービス。"""

from __future__ import annotations

from qgis.PyQt.QtXml import QDomDocument
from qgis.core import QgsPrintLayout, QgsProject, QgsReadWriteContext, QgsRectangle

from ..models.csv_layout_dataset import CsvLayoutDataset
from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    get_map_items,
    remove_layout_if_exists,
    set_item_expression,
    set_item_extent,
)


class LayoutRebuildService:
    """CSVデータを新テンプレートへ反映して再作成するサービス。

    概要:
        QPTテンプレートから新規レイアウトを生成し、CSV内容を適用する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutRebuildService()
    """

    def rebuild_layouts(
        self,
        dataset: CsvLayoutDataset,
        template_path: str,
        target_layout_names: list[str],
    ) -> OperationResult:
        """指定レイアウト群をテンプレートから再作成する。

        概要:
            テンプレートを読み込み、同名既存レイアウトを削除後、
            CSVのExtentとexpressionを反映したレイアウトを新規作成する。

        引数:
            dataset: CSV全体データ。
            template_path: QPTテンプレートファイルパス。
            target_layout_names: 再作成対象レイアウト名一覧。

        戻り値:
            OperationResult: 再作成処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.rebuild_layouts(dataset, "/tmp/template.qpt", ["LayoutA"])
        """
        result = OperationResult(success=False)
        result.target_layout_count = len(target_layout_names)

        dom_document = QDomDocument()
        try:
            with open(template_path, mode="r", encoding="utf-8") as template_file:
                template_xml = template_file.read()
            loaded, error_message, error_line, _error_column = dom_document.setContent(template_xml)
            if not loaded:
                result.fatal_error = True
                result.add_log(
                    build_log(
                        LogLevel.ERROR,
                        f"テンプレートXML読込に失敗しました: {error_message} (line={error_line})",
                    )
                )
                return result
        except OSError as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, f"テンプレートファイルを開けませんでした: {exc}"))
            return result

        manager = QgsProject.instance().layoutManager()
        for layout_name in target_layout_names:
            layout_result = LayoutProcessResult(layout_name=layout_name)
            dataset_layout = dataset.get_layout(layout_name)
            if dataset_layout is None:
                layout_result.has_warning = True
                result.warning_layout_count += 1
                result.add_log(build_log(LogLevel.WARNING, "CSV内に対象レイアウトがありません", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            final_layout_name = layout_name
            try:
                remove_layout_if_exists(layout_name)
            except RuntimeError as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            try:
                new_layout = QgsPrintLayout(QgsProject.instance())
                new_layout.initializeDefaults()
                load_status, _error = new_layout.loadFromTemplate(dom_document, QgsReadWriteContext())
                if not load_status:
                    raise RuntimeError("テンプレートからレイアウトを生成できませんでした")
            except Exception as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, f"レイアウト作成に失敗しました: {exc}", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            try:
                map_items = get_map_items(new_layout)
                layout_result.target_count = len(dataset_layout.map_items)
                if len(map_items) != len(dataset_layout.map_items):
                    layout_result.has_warning = True
                    result.add_log(build_log(LogLevel.WARNING, "地図アイテム数が一致しません", layout_name=layout_name))

                for map_record in dataset_layout.map_items:
                    map_item = new_layout.itemById(map_record.map_item_id)
                    if map_item is None:
                        layout_result.has_warning = True
                        result.add_log(
                            build_log(
                                LogLevel.WARNING,
                                "地図アイテムがテンプレートで見つかりません",
                                layout_name=layout_name,
                                map_item_id=map_record.map_item_id,
                                csv_line_no=map_record.source_line_no,
                            )
                        )
                        continue
                    rectangle = QgsRectangle(map_record.xmin, map_record.ymin, map_record.xmax, map_record.ymax)
                    set_item_extent(map_item, rectangle)
                    set_item_expression(map_item, map_record.expression)
                    layout_result.success_count += 1

                if layout_result.has_warning:
                    layout_result.needs_review_suffix = True
                    final_layout_name = f"{layout_name}_要確認"
                    try:
                        remove_layout_if_exists(final_layout_name)
                    except RuntimeError:
                        pass
            except RuntimeError as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            new_layout.setName(final_layout_name)
            if not manager.addLayout(new_layout):
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, "再作成レイアウト追加に失敗しました", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            if layout_result.has_warning:
                result.warning_layout_count += 1
                result.success_layout_count += 1
            else:
                result.success_layout_count += 1
            result.layout_results.append(layout_result)

        result.has_warning = result.warning_layout_count > 0
        result.has_error = result.failed_layout_count > 0
        result.success = not result.fatal_error and not result.has_error
        result.add_log(build_log(LogLevel.INFO, "再作成処理が完了しました"))
        return result
