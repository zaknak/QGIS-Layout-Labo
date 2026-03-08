# -*- coding: utf-8 -*-
"""expressionビルダサービス。"""

from __future__ import annotations

from ..models.map_item_selection import MapItemSelection
from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    find_layout_by_name,
    find_map_item_by_selection,
    set_item_expression,
)


class ExpressionBuilderService:
    """expression生成と適用を担うサービス。

    概要:
        レイヤ名一覧からexpressionを構築し、
        指定レイアウト内の複数地図アイテムへ一括適用する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = ExpressionBuilderService()
    """

    def build_expression(self, layer_names: list[str]) -> tuple[OperationResult, str | None]:
        """レイヤ名一覧からexpressionを構築する。

        概要:
            レイヤ名を `|` で連結し、全体を `'` で囲んだexpressionを生成する。
            レイヤ名内の `'` は `''` にエスケープする。

        引数:
            layer_names: expressionに含めるレイヤ名の並び順付き一覧。

        戻り値:
            tuple[OperationResult, str | None]:
                生成結果とexpression文字列。失敗時はNone。

        例外:
            なし。

        使用例:
            >>> result, expr = service.build_expression(["Road", "Label"])
        """
        result = OperationResult(success=False)
        if not layer_names:
            result.fatal_error = True
            result.failed_layout_count = 1
            result.add_log(build_log(LogLevel.ERROR, "expression対象レイヤ未選択です"))
            return result, None

        escaped_names = [layer_name.replace("'", "''") for layer_name in layer_names]
        expression = "'" + "|".join(escaped_names) + "'"

        result.success = True
        result.success_layout_count = 1
        result.target_layout_count = 1
        result.add_log(build_log(LogLevel.INFO, f"expressionを生成しました: {expression}"))
        return result, expression

    def apply_expression_to_maps(
        self,
        expression: str,
        target_layout_name: str,
        target_selections: list[MapItemSelection],
    ) -> OperationResult:
        """expressionを複数地図アイテムへ適用する。

        概要:
            指定レイアウト内の選択地図アイテムへ
            `dataDefinedMapLayers.expression` を設定する。

        引数:
            expression: 適用するexpression文字列。
            target_layout_name: 適用先レイアウト名。
            target_selections: 適用先地図アイテム選択情報一覧。

        戻り値:
            OperationResult: 適用処理結果。

        例外:
            なし。

        使用例:
            >>> service.apply_expression_to_maps("'Road|Label'", "LayoutA", selections)
        """
        result = OperationResult(success=False)
        result.target_layout_count = 1
        layout_result = LayoutProcessResult(layout_name=target_layout_name, target_count=len(target_selections))

        if not expression:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "適用するexpressionがありません"))
            result.layout_results.append(layout_result)
            return result

        if not target_layout_name:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "適用先レイアウト未選択です"))
            result.layout_results.append(layout_result)
            return result

        if not target_selections:
            result.fatal_error = True
            result.failed_layout_count = 1
            layout_result.has_error = True
            result.add_log(build_log(LogLevel.ERROR, "適用先地図アイテム未選択です", layout_name=target_layout_name))
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
            result.add_log(build_log(LogLevel.ERROR, "適用先レイアウトが見つかりません", layout_name=target_layout_name))
            result.layout_results.append(layout_result)
            return result

        for selection in target_selections:
            map_item_id = selection.map_item_id
            try:
                target_map_item = find_map_item_by_selection(target_layout, selection)
                if target_map_item is None:
                    layout_result.has_warning = True
                    result.add_log(
                        build_log(
                            LogLevel.WARNING,
                            "適用先地図アイテムが見つかりません",
                            layout_name=target_layout_name,
                            map_item_id=map_item_id,
                        )
                    )
                    continue
                set_item_expression(target_map_item, expression)
                layout_result.success_count += 1
            except RuntimeError as exc:
                layout_result.has_error = True
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=target_layout_name, map_item_id=map_item_id))

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
        result.add_log(build_log(LogLevel.INFO, "expression適用処理が完了しました", layout_name=target_layout_name))
        return result
