# -*- coding: utf-8 -*-
"""ログメッセージ生成ユーティリティ。"""

from __future__ import annotations

from ..models.operation_result import LogLevel, LogMessage


def build_log(
    level: LogLevel,
    message: str,
    layout_name: str | None = None,
    map_item_id: str | None = None,
    csv_line_no: int | None = None,
) -> LogMessage:
    """ログメッセージを生成する。

    概要:
        指定パラメータから `LogMessage` を構築して返す。

    引数:
        level: ログレベル。
        message: 文言。
        layout_name: 対象レイアウト名。
        map_item_id: 対象地図アイテムID。
        csv_line_no: CSV行番号。

    戻り値:
        LogMessage: 生成したログ。

    例外:
        なし。

    使用例:
        >>> log = build_log(LogLevel.INFO, "開始")
    """
    return LogMessage(
        level=level,
        message=message,
        layout_name=layout_name,
        map_item_id=map_item_id,
        csv_line_no=csv_line_no,
    )
