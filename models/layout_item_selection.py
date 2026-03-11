# -*- coding: utf-8 -*-
"""レイアウトアイテム選択情報モデル。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutItemSelection:
    """UI選択用のレイアウトアイテム識別情報を表すモデル。

    概要:
        レイアウト内アイテムをUIから安全に選択できるよう、
        UUID、表示名、種別名、所属ページ名、item id を保持する。

    引数:
        item_uuid: レイアウトアイテムUUID。
        item_id: レイアウトアイテムID。
        item_type_name: UI表示向けのアイテム種別名。
        page_name: UI表示向けの所属ページ名。
        display_name: UI表示名。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> selection = LayoutItemSelection("uuid-1", "title", "ラベル", "1ページ目", "ラベル / title / 1ページ目")
    """

    item_uuid: str
    item_id: str
    item_type_name: str
    page_name: str
    display_name: str
