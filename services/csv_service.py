# -*- coding: utf-8 -*-
"""CSV入出力サービス。"""

from __future__ import annotations

import csv
from pathlib import Path

from ..models.csv_layout_dataset import CsvLayoutDataset
from ..models.map_item_record import MapItemRecord
from ..models.operation_result import LogLevel, OperationResult
from ..utils.csv_helpers import CSV_HEADERS
from ..utils.logger import build_log


class CsvService:
    """CSVの読み書きを担当するサービス。

    概要:
        固定仕様CSVの読み込み・書き出し、検証、データセット変換を行う。

    引数:
        なし。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> service = CsvService()
    """

    def read_csv(self, csv_path: str) -> tuple[OperationResult, CsvLayoutDataset]:
        """CSVを読み込みデータセットへ変換する。

        概要:
            必須列チェック、値検証、重複検出を行いながら
            `CsvLayoutDataset` を構築する。

        引数:
            csv_path: 読み込み対象CSVパス。

        戻り値:
            tuple[OperationResult, CsvLayoutDataset]: 処理結果とデータセット。

        例外:
            なし。

        使用例:
            >>> result, dataset = service.read_csv("/tmp/data.csv")
        """
        result = OperationResult(success=False)
        dataset = CsvLayoutDataset()
        seen_keys: set[tuple[str, str]] = set()

        try:
            with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as file_obj:
                reader = csv.DictReader(file_obj)
                headers = reader.fieldnames or []
                missing_headers = [header for header in CSV_HEADERS if header not in headers]
                if missing_headers:
                    result.fatal_error = True
                    result.add_log(build_log(LogLevel.ERROR, f"必須列不足: {missing_headers}"))
                    return result, dataset

                for line_no, row in enumerate(reader, start=2):
                    validated = self._validate_and_convert_row(row=row, line_no=line_no, result=result)
                    if validated is None:
                        result.fatal_error = True
                        continue
                    duplicate_key = (validated.layout_name, validated.map_item_id)
                    if duplicate_key in seen_keys:
                        result.fatal_error = True
                        result.add_log(
                            build_log(
                                LogLevel.ERROR,
                                "layout_name と map_item_id の重複行を検出しました",
                                layout_name=validated.layout_name,
                                map_item_id=validated.map_item_id,
                                csv_line_no=line_no,
                            )
                        )
                        continue
                    seen_keys.add(duplicate_key)
                    dataset.add_record(validated)
        except OSError as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, f"CSVファイルを開けませんでした: {exc}"))
            return result, dataset
        except csv.Error as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, f"CSV読み込みに失敗しました: {exc}"))
            return result, dataset

        if result.fatal_error:
            result.success = False
            return result, CsvLayoutDataset()

        result.success = True
        result.target_layout_count = len(dataset.layouts)
        if result.target_layout_count == 0:
            result.add_log(build_log(LogLevel.WARNING, "CSVにデータ行がありません"))
        else:
            result.add_log(build_log(LogLevel.INFO, "CSV読み込みに成功しました"))
        return result, dataset

    def write_csv(self, csv_path: str, records: list[MapItemRecord]) -> OperationResult:
        """地図アイテムレコード一覧をCSVへ書き出す。

        概要:
            固定列順とBOM付きUTF-8でCSVファイルを生成する。

        引数:
            csv_path: 出力先CSVパス。
            records: 書き出し対象レコード一覧。

        戻り値:
            OperationResult: 書き出し処理結果。

        例外:
            なし。

        使用例:
            >>> result = service.write_csv("/tmp/out.csv", records)
        """
        result = OperationResult(success=False)
        try:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
            with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as file_obj:
                writer = csv.DictWriter(file_obj, fieldnames=CSV_HEADERS, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                for record in records:
                    writer.writerow(
                        {
                            "layout_name": record.layout_name,
                            "map_item_id": record.map_item_id,
                            "xmin": record.xmin,
                            "ymin": record.ymin,
                            "xmax": record.xmax,
                            "ymax": record.ymax,
                            "expression": record.expression,
                        }
                    )
        except (OSError, csv.Error) as exc:
            result.fatal_error = True
            result.add_log(build_log(LogLevel.ERROR, f"CSV書き出しに失敗しました: {exc}"))
            return result

        result.success = True
        result.target_layout_count = len({record.layout_name for record in records})
        result.success_layout_count = result.target_layout_count
        result.add_log(build_log(LogLevel.INFO, "CSV書き出しに成功しました"))
        return result

    def _validate_and_convert_row(
        self,
        row: dict[str, str | None],
        line_no: int,
        result: OperationResult,
    ) -> MapItemRecord | None:
        """CSV1行を検証してレコードへ変換する。

        概要:
            必須値チェックと数値変換を実施し、問題があればERRORログを追加する。

        引数:
            row: CSV行辞書。
            line_no: CSV行番号。
            result: ログ追記対象の結果オブジェクト。

        戻り値:
            MapItemRecord | None: 成功時のレコード。失敗時None。

        例外:
            なし。

        使用例:
            >>> record = service._validate_and_convert_row(row, 2, result)
        """
        layout_name = row.get("layout_name")
        map_item_id = row.get("map_item_id")
        xmin = row.get("xmin")
        ymin = row.get("ymin")
        xmax = row.get("xmax")
        ymax = row.get("ymax")
        expression = row.get("expression") or ""

        if layout_name is None or layout_name == "":
            result.add_log(build_log(LogLevel.ERROR, "layout_name が空値です", csv_line_no=line_no))
            return None
        if map_item_id is None or map_item_id == "":
            result.add_log(build_log(LogLevel.ERROR, "map_item_id が空値です", csv_line_no=line_no))
            return None
        if xmin in (None, "") or ymin in (None, "") or xmax in (None, "") or ymax in (None, ""):
            result.add_log(build_log(LogLevel.ERROR, "Extent列に空値があります", csv_line_no=line_no))
            return None

        try:
            xmin_f = float(xmin)
            ymin_f = float(ymin)
            xmax_f = float(xmax)
            ymax_f = float(ymax)
        except ValueError:
            result.add_log(build_log(LogLevel.ERROR, "Extent列の数値変換に失敗しました", csv_line_no=line_no))
            return None

        return MapItemRecord(
            layout_name=layout_name,
            map_item_id=map_item_id,
            xmin=xmin_f,
            ymin=ymin_f,
            xmax=xmax_f,
            ymax=ymax_f,
            expression=expression,
            source_line_no=line_no,
        )
