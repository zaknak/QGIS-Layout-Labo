# -*- coding: utf-8 -*-
"""CSV全体データモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .layout_record import LayoutRecord
from .map_item_record import MapItemRecord


@dataclass
class CsvLayoutDataset:
    """CSV全体をレイアウト単位で保持するデータセット。

    概要:
        複数レイアウトの地図アイテム情報を辞書構造で管理し、
        一覧取得やレイアウト単位取得を提供する。

    引数:
        layouts: レイアウト名をキーとした辞書。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> dataset = CsvLayoutDataset()
    """

    layouts: dict[str, LayoutRecord] = field(default_factory=dict)

    def add_record(self, record: MapItemRecord) -> None:
        """地図アイテムレコードをデータセットへ追加する。

        概要:
            レイアウト名でグルーピングしながらデータを格納する。

        引数:
            record: 追加対象の地図アイテムレコード。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dataset.add_record(record)
        """
        layout: LayoutRecord = self.layouts.setdefault(
            record.layout_name,
            LayoutRecord(layout_name=record.layout_name),
        )
        layout.add_item(record)

    def get_layout_names(self) -> list[str]:
        """レイアウト名一覧を返す。

        概要:
            CSVデータセット内に含まれるレイアウト名を昇順で返す。

        引数:
            なし。

        戻り値:
            list[str]: レイアウト名一覧。

        例外:
            なし。

        使用例:
            >>> names = dataset.get_layout_names()
        """
        return sorted(self.layouts.keys())

    def get_layout(self, layout_name: str) -> LayoutRecord | None:
        """指定レイアウト名のデータを返す。

        概要:
            レイアウト名に一致する `LayoutRecord` を取得する。

        引数:
            layout_name: 取得対象レイアウト名。

        戻り値:
            LayoutRecord | None: 一致データ。存在しない場合はNone。

        例外:
            なし。

        使用例:
            >>> layout = dataset.get_layout("LayoutA")
        """
        return self.layouts.get(layout_name)

    def get_layout_map_item_count(self, layout_name: str) -> int:
        """指定レイアウトの地図アイテム数を返す。

        概要:
            指定したレイアウト名に対応する地図アイテム件数を返す。
            該当レイアウトが存在しない場合は0を返す。

        引数:
            layout_name: 件数取得対象のレイアウト名。

        戻り値:
            int: 地図アイテム件数。

        例外:
            なし。

        使用例:
            >>> count = dataset.get_layout_map_item_count("LayoutA")
        """
        layout = self.layouts.get(layout_name)
        if layout is None:
            return 0
        return len(layout.map_items)

    def get_layout_name_with_counts(self) -> list[tuple[str, int]]:
        """レイアウト名と地図アイテム数の一覧を返す。

        概要:
            データセット内のレイアウトを名前昇順で走査し、
            表示用にレイアウト名と地図アイテム件数の組を返す。

        引数:
            なし。

        戻り値:
            list[tuple[str, int]]: `[(layout_name, map_item_count), ...]` の一覧。

        例外:
            なし。

        使用例:
            >>> entries = dataset.get_layout_name_with_counts()
        """
        return [(layout_name, self.get_layout_map_item_count(layout_name)) for layout_name in self.get_layout_names()]

    def iter_layouts(self) -> list[LayoutRecord]:
        """レイアウト単位データ一覧を返す。

        概要:
            レイアウト名昇順で `LayoutRecord` の一覧を返す。

        引数:
            なし。

        戻り値:
            list[LayoutRecord]: レイアウト単位データ一覧。

        例外:
            なし。

        使用例:
            >>> layouts = dataset.iter_layouts()
        """
        return [self.layouts[name] for name in self.get_layout_names()]
