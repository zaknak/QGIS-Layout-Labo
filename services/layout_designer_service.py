# -*- coding: utf-8 -*-
"""レイアウト編集画面更新サービス。"""

from __future__ import annotations

from ..models.operation_result import LogLevel, OperationResult
from ..utils.logger import build_log


class LayoutDesignerService:
    """開いているLayout Designerの再描画を行うサービス。

    概要:
        zvalue再設定後に対象レイアウトの編集画面表示を更新する責務を持つ。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = LayoutDesignerService()
    """

    def refresh_open_designers(self, iface: object | None, target_layout_names: list[str]) -> OperationResult:
        """開いているLayout Designerの再描画を行う。

        概要:
            `iface.openLayoutDesigners()` から対象レイアウトを特定し、
            レイアウトとビューの再描画を実施する。

        引数:
            iface: QGISインターフェースオブジェクト。
            target_layout_names: 更新対象レイアウト名一覧。

        戻り値:
            OperationResult: 更新処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.refresh_open_designers(iface, ["LayoutA"])
        """
        result = OperationResult(success=True)
        if iface is None or not target_layout_names:
            return result

        try:
            open_designers = iface.openLayoutDesigners()
        except Exception as exc:
            result.success = False
            result.has_warning = True
            result.add_log(build_log(LogLevel.WARNING, f"レイアウト編集画面更新に失敗しました: {exc}"))
            return result

        target_layout_name_set = set(target_layout_names)
        refreshed_count = 0
        for designer in open_designers:
            try:
                designer_layout = designer.layout()
            except Exception:
                continue
            if designer_layout is None:
                continue
            try:
                layout_name = designer_layout.name()
            except Exception:
                continue
            if layout_name not in target_layout_name_set:
                continue
            try:
                designer_layout.refresh()
                view = designer.view()
                if view is not None:
                    viewport = view.viewport()
                    if viewport is not None:
                        viewport.update()
                refreshed_count += 1
            except Exception as exc:
                result.has_warning = True
                result.add_log(
                    build_log(
                        LogLevel.WARNING,
                        f"レイアウト編集画面の再描画に失敗しました: {exc}",
                        layout_name=layout_name,
                    )
                )

        if refreshed_count > 0:
            result.add_log(build_log(LogLevel.INFO, f"レイアウト編集画面を更新しました: {refreshed_count}件"))
        return result
