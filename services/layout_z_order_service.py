# -*- coding: utf-8 -*-
"""ページ考慮のzvalue再設定サービス。"""

from __future__ import annotations

from dataclasses import dataclass

from qgis.PyQt.QtCore import QPointF, QRectF
from qgis.core import QgsLayoutItem, QgsLayoutItemPage

from ..models.operation_result import LayoutProcessResult, LogLevel, OperationResult
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import find_layout_by_name


@dataclass(frozen=True)
class _ItemSortInfo:
    """zvalue再設定時の内部ソート情報を表す。

    概要:
        再採番に必要な対象アイテムと判定済み属性を保持する。

    引数:
        item: 対象レイアウトアイテム。
        item_label: ログ表示向け識別文字列。
        page_index: 所属ページ番号（0始まり）。ページ外はNone。
        original_z_value: 実行前zvalue。
        original_order_index: 取得順インデックス。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> info = _ItemSortInfo(item=obj, item_label="map1", page_index=0, original_z_value=2.0, original_order_index=1)
    """

    item: object
    item_label: str
    page_index: int | None
    original_z_value: float
    original_order_index: int


class LayoutZOrderService:
    """ページを考慮してzvalueを再設定するサービス。

    概要:
        ページ内の相対順を維持しつつ、1ページ目を最前面としてzvalueを振り直す。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutZOrderService()
        >>> result = service.reorder_by_page(["LayoutA"])
    """

    def reorder_by_page(self, target_layout_names: list[str]) -> OperationResult:
        """対象レイアウト群へページ考慮zvalue再設定を適用する。

        概要:
            各レイアウトでページ所属を判定し、1ページ目優先でzvalueを再採番する。

        引数:
            target_layout_names: 処理対象レイアウト名一覧。

        戻り値:
            OperationResult: 処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.reorder_by_page(["LayoutA", "LayoutB"])
        """
        result = OperationResult(success=True)
        result.target_layout_count = len(target_layout_names)

        for layout_name in target_layout_names:
            layout_result = LayoutProcessResult(layout_name=layout_name)
            layout = find_layout_by_name(layout_name)
            if layout is None:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, "レイアウトが見つかりません", layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            try:
                page_rects = self._collect_page_rects(layout)
                page_count = len(page_rects)
                if page_count == 0:
                    raise RuntimeError("ページ情報を取得できませんでした")

                sortable_items = self._collect_sortable_items(layout, page_rects, layout_name, result, layout_result)
                layout_result.target_count = len(sortable_items)

                if not sortable_items:
                    result.add_log(build_log(LogLevel.INFO, "再設定対象アイテムがありません", layout_name=layout_name))
                    result.success_layout_count += 1
                    result.layout_results.append(layout_result)
                    continue

                self._apply_reordered_z_values(layout, sortable_items, page_count)
                layout_result.success_count = len(sortable_items)
            except RuntimeError as exc:
                layout_result.has_error = True
                result.failed_layout_count += 1
                result.add_log(build_log(LogLevel.ERROR, str(exc), layout_name=layout_name))
                result.layout_results.append(layout_result)
                continue

            if layout_result.has_warning:
                result.warning_layout_count += 1
            result.success_layout_count += 1
            result.layout_results.append(layout_result)

        result.has_warning = result.warning_layout_count > 0
        result.has_error = result.failed_layout_count > 0
        result.success = not result.has_error
        result.add_log(build_log(LogLevel.INFO, "zvalue再設定処理が完了しました"))
        return result

    def _collect_page_rects(self, layout: object) -> list[QRectF]:
        """レイアウト内ページ矩形一覧を取得する。

        概要:
            ページコレクションから各ページのシーン矩形を収集する。

        引数:
            layout: 対象レイアウト。

        戻り値:
            list[QRectF]: ページ矩形一覧（0始まりページ順）。

        例外:
            RuntimeError: ページ取得に失敗した場合。

        使用例:
            >>> page_rects = self._collect_page_rects(layout)
        """
        try:
            page_collection = layout.pageCollection()
            pages = page_collection.pages()
        except Exception as exc:
            raise RuntimeError(f"ページ情報取得に失敗しました: {exc}") from exc

        rects: list[QRectF] = []
        for page in pages:
            try:
                rects.append(page.sceneBoundingRect())
            except Exception as exc:
                raise RuntimeError(f"ページ矩形取得に失敗しました: {exc}") from exc
        return rects

    def _collect_sortable_items(
        self,
        layout: object,
        page_rects: list[QRectF],
        layout_name: str,
        result: OperationResult,
        layout_result: LayoutProcessResult,
    ) -> list[_ItemSortInfo]:
        """zvalue再採番対象アイテム一覧を生成する。

        概要:
            ページアイテムを除外し、各アイテムのページ所属と現行zvalueを収集する。

        引数:
            layout: 対象レイアウト。
            page_rects: ページ矩形一覧。
            layout_name: ログ出力用のレイアウト名。
            result: 全体結果オブジェクト。
            layout_result: レイアウト単位結果。

        戻り値:
            list[_ItemSortInfo]: 再採番対象情報一覧。

        例外:
            RuntimeError: アイテム情報取得に失敗した場合。

        使用例:
            >>> infos = self._collect_sortable_items(layout, page_rects, "LayoutA", result, layout_result)
        """
        try:
            all_items = layout.items()
        except Exception as exc:
            raise RuntimeError(f"レイアウトアイテム取得に失敗しました: {exc}") from exc

        sortable_items: list[_ItemSortInfo] = []
        for index, item in enumerate(all_items):
            if not isinstance(item, QgsLayoutItem):
                continue
            if isinstance(item, QgsLayoutItemPage):
                continue
            try:
                item_rect = item.sceneBoundingRect()
                center_point = item_rect.center()
                page_index = self._resolve_page_index(center_point, page_rects)
                item_label = self._build_item_label(item, index)
                sortable_items.append(
                    _ItemSortInfo(
                        item=item,
                        item_label=item_label,
                        page_index=page_index,
                        original_z_value=float(item.zValue()),
                        original_order_index=index,
                    )
                )
                if page_index is None:
                    layout_result.has_warning = True
                    result.add_log(
                        build_log(
                            LogLevel.WARNING,
                            "ページ外アイテムを最後尾グループとして処理します",
                            layout_name=layout_name,
                            map_item_id=item_label,
                        )
                    )
            except Exception as exc:
                raise RuntimeError(f"アイテム情報取得に失敗しました: {exc}") from exc
        return sortable_items

    def _resolve_page_index(self, center_point: QPointF, page_rects: list[QRectF]) -> int | None:
        """中心点から所属ページを判定する。

        概要:
            アイテム中心点が包含される最初のページを所属ページとする。

        引数:
            center_point: アイテム中心点。
            page_rects: ページ矩形一覧。

        戻り値:
            int | None: 所属ページ番号（0始まり）。ページ外はNone。

        例外:
            なし。

        使用例:
            >>> page_index = self._resolve_page_index(point, page_rects)
        """
        for page_index, page_rect in enumerate(page_rects):
            if page_rect.contains(center_point):
                return page_index
        return None

    def _build_item_label(self, item: object, fallback_index: int) -> str:
        """ログ表示向けのアイテム識別文字列を生成する。

        概要:
            item.id() があれば優先使用し、無い場合は型名とインデックスを使用する。

        引数:
            item: 対象アイテム。
            fallback_index: 代替識別用インデックス。

        戻り値:
            str: 識別文字列。

        例外:
            なし。

        使用例:
            >>> label = self._build_item_label(item, 3)
        """
        item_id = ""
        if hasattr(item, "id"):
            try:
                raw_id = item.id()
                if isinstance(raw_id, str):
                    item_id = raw_id.strip()
            except Exception:
                item_id = ""
        if item_id:
            return item_id
        return f"{type(item).__name__}#{fallback_index + 1}"

    def _apply_reordered_z_values(self, layout: object, sortable_items: list[_ItemSortInfo], page_count: int) -> None:
        """収集済みアイテムへzvalue再設定を適用する。

        概要:
            `moveItemToTop(..., deferUpdate=True)` と `updateZValues()` を用いて
            レイアウト内部モデルと整合したz順更新を行う。

        引数:
            layout: 対象レイアウト。
            sortable_items: 再採番対象情報一覧。
            page_count: ページ数。

        戻り値:
            なし。

        例外:
            RuntimeError: zvalue設定に失敗した場合。

        使用例:
            >>> self._apply_reordered_z_values(layout, infos, 2)
        """
        outside_items = [item for item in sortable_items if item.page_index is None]
        inside_items = [item for item in sortable_items if item.page_index is not None]

        front_order_items: list[_ItemSortInfo] = []
        for page_index in range(page_count):
            page_items = [item for item in inside_items if item.page_index == page_index]
            front_order_items.extend(self._sort_items_within_page(page_items, keep_front=True))
        front_order_items.extend(self._sort_items_within_page(outside_items, keep_front=True))

        if not front_order_items:
            return

        try:
            # 後面から順に top へ積み上げることで、最終的に front_order を再現する。
            for item_info in reversed(front_order_items):
                layout.moveItemToTop(item_info.item, True)
            layout.updateZValues()
            layout.refresh()
        except Exception as exc:
            raise RuntimeError(f"zvalue設定に失敗しました: {exc}") from exc

    def _sort_items_within_page(self, items: list[_ItemSortInfo], keep_front: bool) -> list[_ItemSortInfo]:
        """ページ内の相対順を維持したソート結果を返す。

        概要:
            既存zvalue順と取得順を使って安定ソートし、前面順または後面順を返す。

        引数:
            items: 同一ページ内アイテム一覧。
            keep_front: Trueで前面順、Falseで後面順。

        戻り値:
            list[_ItemSortInfo]: ソート済みアイテム一覧。

        例外:
            なし。

        使用例:
            >>> ordered = self._sort_items_within_page(items, keep_front=False)
        """
        if keep_front:
            return sorted(items, key=lambda entry: (-entry.original_z_value, entry.original_order_index))
        return sorted(items, key=lambda entry: (entry.original_z_value, entry.original_order_index))
