# -*- coding: utf-8 -*-
"""処理結果オブジェクト群。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LogLevel(str, Enum):
    """ログレベル定義。

    概要:
        UI表示用のログレベルを列挙値として提供する。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> level = LogLevel.INFO
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class LogMessage:
    """ログメッセージを表すモデル。

    概要:
        レベルと表示文言、任意の対象情報を保持する。

    引数:
        level: ログレベル。
        message: 表示文言。
        layout_name: 対象レイアウト名。
        map_item_id: 対象アイテムID。
        csv_line_no: 対象CSV行番号。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> log = LogMessage(LogLevel.INFO, "処理開始")
    """

    level: LogLevel
    message: str
    layout_name: str | None = None
    map_item_id: str | None = None
    csv_line_no: int | None = None

    def format_for_ui(self) -> str:
        """UI表示向け文字列へ整形する。

        概要:
            ログレベルと対象情報を含む表示テキストを生成する。

        引数:
            なし。

        戻り値:
            str: UI表示用文字列。

        例外:
            なし。

        使用例:
            >>> text = log.format_for_ui()
        """
        parts: list[str] = [self.level.value, self.message]
        if self.layout_name:
            parts.append(f"layout={self.layout_name}")
        if self.map_item_id:
            parts.append(f"item={self.map_item_id}")
        if self.csv_line_no is not None:
            parts.append(f"line={self.csv_line_no}")
        return ": ".join([parts[0], " | ".join(parts[1:])])


@dataclass
class LayoutProcessResult:
    """レイアウト単位の処理結果。

    概要:
        1レイアウト分の件数や警告・エラー状態を保持する。

    引数:
        layout_name: レイアウト名。
        target_count: 対象件数。
        success_count: 成功件数。
        has_warning: 警告有無。
        has_error: エラー有無。
        needs_review_suffix: `_要確認` 付与要否。
        messages: レイアウト関連ログ一覧。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> lr = LayoutProcessResult(layout_name="A")
    """

    layout_name: str
    target_count: int = 0
    success_count: int = 0
    has_warning: bool = False
    has_error: bool = False
    needs_review_suffix: bool = False
    messages: list[LogMessage] = field(default_factory=list)


@dataclass
class OperationResult:
    """主要処理全体の結果オブジェクト。

    概要:
        成否、警告・エラー有無、件数集計、ログ、レイアウト結果を保持する。

    引数:
        success: 処理成功可否。
        fatal_error: 致命的エラー有無。
        has_warning: 警告有無。
        has_error: エラー有無。
        target_layout_count: 処理対象レイアウト数。
        success_layout_count: 成功レイアウト数。
        warning_layout_count: 警告付きレイアウト数。
        failed_layout_count: 失敗レイアウト数。
        logs: ログ一覧。
        layout_results: レイアウト単位結果一覧。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> result = OperationResult(success=True)
    """

    success: bool
    fatal_error: bool = False
    has_warning: bool = False
    has_error: bool = False
    target_layout_count: int = 0
    success_layout_count: int = 0
    warning_layout_count: int = 0
    failed_layout_count: int = 0
    logs: list[LogMessage] = field(default_factory=list)
    layout_results: list[LayoutProcessResult] = field(default_factory=list)

    def add_log(self, log: LogMessage) -> None:
        """ログを追加し状態フラグを更新する。

        概要:
            ログレベルに応じて警告/エラーフラグを更新する。

        引数:
            log: 追加するログ。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> result.add_log(log)
        """
        self.logs.append(log)
        if log.level == LogLevel.WARNING:
            self.has_warning = True
        if log.level == LogLevel.ERROR:
            self.has_error = True

    def summary_text(self) -> str:
        """処理概要テキストを返す。

        概要:
            UI表示向けに件数集計を簡潔な文字列へ整形する。

        引数:
            なし。

        戻り値:
            str: 件数サマリ文字列。

        例外:
            なし。

        使用例:
            >>> text = result.summary_text()
        """
        return (
            f"対象={self.target_layout_count}, 成功={self.success_layout_count}, "
            f"警告付き={self.warning_layout_count}, 失敗={self.failed_layout_count}"
        )
