# -*- coding: utf-8 -*-
"""レイアウトアイテム複製サービス。"""

from __future__ import annotations

from qgis.PyQt.QtXml import QDomDocument

from ..models.layout_item_selection import LayoutItemSelection
from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    duplicate_layout_items_to_layout,
    find_layout_by_name,
    find_layout_item_by_uuid,
    get_layout_item_page_name,
    serialize_layout_items_to_xml,
)


class LayoutItemDuplicateService:
    """レイアウトアイテム複製機能を提供するサービス。

    概要:
        単一元レイアウトの選択アイテム群を、複数の既存レイアウトへ
        新規アイテムとして複製する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutItemDuplicateService()
    """

    def duplicate_items(
        self,
        source_layout_name: str,
        source_selections: list[LayoutItemSelection],
        target_layout_names: list[str],
    ) -> OperationResult:
        """選択レイアウトアイテム群を複数レイアウトへ複製する。

        概要:
            元レイアウトから選択アイテムを再取得し、XML経由で
            各コピー先レイアウトへ新規追加する。

        引数:
            source_layout_name: 元レイアウト名。
            source_selections: 元アイテム選択情報一覧。
            target_layout_names: コピー先レイアウト名一覧。

        戻り値:
            OperationResult: 複製処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.duplicate_items("LayoutA", selections, ["LayoutB"])
        """
        result = OperationResult(success=False)
        result.target_layout_count = len(target_layout_names)

        validation_error = self._validate_input(source_layout_name, source_selections, target_layout_names)
        if validation_error is not None:
            return validation_error

        try:
            source_layout = find_layout_by_name(source_layout_name)
        except RuntimeError as exc:
            return self._build_fatal_result(str(exc), source_layout_name)

        if source_layout is None:
            return self._build_fatal_result("元レイアウトが見つかりません", source_layout_name)

        try:
            source_items = self._resolve_source_items(source_layout, source_layout_name, source_selections)
            source_dom = serialize_layout_items_to_xml(source_items)
            source_xml = source_dom.toString()
        except RuntimeError as exc:
            return self._build_fatal_result(str(exc), source_layout_name)

        for target_layout_name in target_layout_names:
            layout_result = LayoutProcessResult(layout_name=target_layout_name, target_count=len(source_items))

            try:
                target_layout = find_layout_by_name(target_layout_name)
            except RuntimeError as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=target_layout_name))
                result.layout_results.append(layout_result)
                continue

            if target_layout is None:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, "コピー先レイアウトが見つかりません", layout_name=target_layout_name))
                result.layout_results.append(layout_result)
                continue

            try:
                copied_items = duplicate_layout_items_to_layout(target_layout, self._build_target_dom(source_xml))
                layout_result.success_count = len(copied_items)
                if len(copied_items) != len(source_items):
                    layout_result.has_warning = True
                    result.add_log(
                        build_log(
                            LogLevel.WARNING,
                            "一部アイテムのみ複製されました",
                            layout_name=target_layout_name,
                        )
                    )
                self._collect_page_warnings(target_layout_name, copied_items, result, layout_result)
            except RuntimeError as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=target_layout_name))
                result.layout_results.append(layout_result)
                continue

            if layout_result.has_error:
                result.failed_layout_count += 1
            elif layout_result.has_warning:
                result.warning_layout_count += 1
                result.success_layout_count += 1
            else:
                result.success_layout_count += 1

            result.layout_results.append(layout_result)
            result.add_log(build_log(LogLevel.INFO, "アイテム複製処理が完了しました", layout_name=target_layout_name))

        result.has_warning = result.warning_layout_count > 0
        result.has_error = result.failed_layout_count > 0
        result.success = not result.has_error
        result.add_log(build_log(LogLevel.INFO, "アイテム複製全体処理が完了しました"))
        return result

    def _build_target_dom(self, source_xml: str) -> QDomDocument:
        """複製先レイアウト用のXMLドキュメントを生成する。

        概要:
            元XML文字列から毎回新しい `QDomDocument` を構築し、
            レイアウト追加処理間の状態共有を避ける。

        引数:
            source_xml: 複製元XML文字列。

        戻り値:
            QDomDocument: 複製先用XMLドキュメント。

        例外:
            RuntimeError: XML再構築に失敗した場合。

        使用例:
            >>> dom = service._build_target_dom(xml_text)
        """
        document = QDomDocument("LayoutLaboDuplicateItems")
        loaded, error_message, error_line, _error_column = document.setContent(source_xml)
        if not loaded:
            raise RuntimeError(f"複製元XMLの再構築に失敗しました: line={error_line}, message={error_message}")
        return document

    def _validate_input(
        self,
        source_layout_name: str,
        source_selections: list[LayoutItemSelection],
        target_layout_names: list[str],
    ) -> OperationResult | None:
        """複製入力値の必須条件を検証する。

        概要:
            元レイアウト、元アイテム、コピー先レイアウトの必須条件と
            同一レイアウト禁止条件を確認する。

        引数:
            source_layout_name: 元レイアウト名。
            source_selections: 元アイテム選択情報一覧。
            target_layout_names: コピー先レイアウト名一覧。

        戻り値:
            OperationResult | None: エラー結果。問題ない場合はNone。

        例外:
            なし。

        使用例:
            >>> err = service._validate_input("LayoutA", selections, ["LayoutB"])
        """
        if not source_layout_name:
            return self._build_fatal_result("元レイアウト未選択です")
        if not source_selections:
            return self._build_fatal_result("元アイテム未選択です", source_layout_name)
        if not target_layout_names:
            return self._build_fatal_result("コピー先レイアウト未選択です", source_layout_name)
        if source_layout_name in target_layout_names:
            return self._build_fatal_result("コピー元レイアウトをコピー先に含めることはできません", source_layout_name)
        return None

    def _resolve_source_items(
        self,
        source_layout: object,
        source_layout_name: str,
        source_selections: list[LayoutItemSelection],
    ) -> list[object]:
        """元レイアウトから複製対象アイテム実体を再取得する。

        概要:
            UIが保持する選択情報からUUIDでアイテムを引き直し、
            複製元実体の一覧を返す。

        引数:
            source_layout: 元レイアウト。
            source_layout_name: 元レイアウト名。
            source_selections: 元アイテム選択情報一覧。

        戻り値:
            list[object]: 複製対象アイテム一覧。

        例外:
            RuntimeError: アイテム取得に失敗した場合。

        使用例:
            >>> items = service._resolve_source_items(layout, "LayoutA", selections)
        """
        source_items: list[object] = []
        for selection in source_selections:
            item = find_layout_item_by_uuid(source_layout, selection.item_uuid)
            if item is None:
                raise RuntimeError(f"元アイテムが見つかりません: {selection.item_id or selection.display_name}")
            source_items.append(item)
        if not source_items:
            raise RuntimeError(f"元アイテムが取得できません: {source_layout_name}")
        return source_items

    def _collect_page_warnings(
        self,
        target_layout_name: str,
        copied_items: list[object],
        result: OperationResult,
        layout_result: LayoutProcessResult,
    ) -> None:
        """複製後アイテムのページ外配置警告を収集する。

        概要:
            複製先でページに所属しないアイテムを検出し、警告ログを追加する。

        引数:
            target_layout_name: コピー先レイアウト名。
            copied_items: 複製後アイテム一覧。
            result: 全体結果オブジェクト。
            layout_result: レイアウト単位結果。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> service._collect_page_warnings("LayoutB", copied_items, result, layout_result)
        """
        for copied_item in copied_items:
            page_name = get_layout_item_page_name(copied_item)
            if page_name != "ページ外":
                continue
            layout_result.has_warning = True
            item_id = ""
            item_id_method = getattr(copied_item, "id", None)
            if callable(item_id_method):
                item_id = item_id_method() or ""
            result.add_log(
                build_log(
                    LogLevel.WARNING,
                    "ページ外に配置された複製アイテムがあります",
                    layout_name=target_layout_name,
                    map_item_id=item_id or "item",
                )
            )

    def _build_fatal_result(self, message: str, layout_name: str | None = None) -> OperationResult:
        """致命的入力エラー向け結果を生成する。

        概要:
            早期終了時に使う失敗結果を統一形式で返す。

        引数:
            message: エラーメッセージ。
            layout_name: 必要に応じた対象レイアウト名。

        戻り値:
            OperationResult: 失敗結果。

        例外:
            なし。

        使用例:
            >>> result = service._build_fatal_result("元レイアウト未選択です")
        """
        result = OperationResult(success=False, fatal_error=True, has_error=True)
        result.failed_layout_count = 1
        if layout_name:
            result.layout_results.append(LayoutProcessResult(layout_name=layout_name, has_error=True))
        result.add_log(build_log(LogLevel.ERROR, message, layout_name=layout_name))
        return result
