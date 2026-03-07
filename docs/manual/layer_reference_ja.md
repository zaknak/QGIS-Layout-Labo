# レイヤ機能マニュアル（モデル層・サービス層・ユーティリティ層）

## 1. 本ドキュメントの目的

本ドキュメントは、`LayoutMapTransfer` プラグインの以下3層で提供される機能を、実装ベースで整理した運用・開発向けマニュアルです。

- モデル層（`models/`）
- サービス層（`services/`）
- ユーティリティ層（`utils/`）

## 2. 全体構成と依存方向

- モデル層: データ構造定義（QGIS API依存を最小化）
- サービス層: 業務処理（CSV I/O、適用、再作成、任意コピー）
- ユーティリティ層: 共通補助（ログ生成、QGISレイアウト操作、CSVヘッダー定義）

依存は概ね次の方向です。

- サービス層 -> モデル層
- サービス層 -> ユーティリティ層
- ユーティリティ層 -> モデル層（一部）

## 3. モデル層（`models/`）

### 3.1 `map_item_record.py`

#### `MapItemRecord`（dataclass, frozen）

- 目的: CSV1行相当の地図アイテム情報を保持する
- 主な項目:
- `layout_name: str`
- `map_item_id: str`
- `xmin/ymin/xmax/ymax: float`
- `expression: str`
- `source_line_no: int | None`（CSV行番号追跡）
- 主な利用箇所:
- `CsvService.read_csv` で生成
- 各サービスで `itemById()` 適用時の入力データとして使用

### 3.2 `layout_record.py`

#### `LayoutRecord`（dataclass）

- 目的: 1レイアウト分の地図アイテム群をまとめる
- 主な項目:
- `layout_name: str`
- `map_items: list[MapItemRecord]`
- 主なメソッド:
- `add_item(record)` 地図アイテムを追加

### 3.3 `csv_layout_dataset.py`

#### `CsvLayoutDataset`（dataclass）

- 目的: CSV全体（複数レイアウト）を管理する
- 主な項目:
- `layouts: dict[str, LayoutRecord]`
- 主なメソッド:
- `add_record(record)` レイアウト単位で自動グルーピング
- `get_layout_names()` レイアウト名一覧（昇順）
- `get_layout(layout_name)` 特定レイアウト取得
- `get_layout_map_item_count(layout_name)` 地図アイテム件数取得
- `get_layout_name_with_counts()` `(layout_name, count)` 一覧
- `iter_layouts()` `LayoutRecord` 一覧（昇順）

### 3.4 `map_item_selection.py`

#### `MapItemSelection`（dataclass, frozen）

- 目的: UIで地図アイテムを一意に扱う識別子
- 背景: 同一 `map_item_id` が重複するレイアウトに対応
- 主な項目:
- `map_item_id: str`
- `occurrence_index: int`（同一ID内の1始まり順）
- `display_name: str`（例: `map1 (#2)`）

### 3.5 `map_copy_snapshot.py`

#### `MapCopySnapshot`（dataclass, frozen）

- 目的: 「地図コピー」機能の取得時点スナップショットを保持
- 主な項目:
- 元情報（`source_layout_name`, `source_map_item_id`, `source_occurrence_index`, `source_display_name`）
- 値本体（`xmin/ymin/xmax/ymax`, `expression`）
- 特徴: コピー実行時に再取得せず、取得時点の値を適用する

### 3.6 `operation_result.py`

#### `LogLevel`（Enum）

- `INFO` / `WARNING` / `ERROR`

#### `LogMessage`（dataclass）

- 目的: UIログ1件分
- 主な項目:
- `level`, `message`
- 任意メタ: `layout_name`, `map_item_id`, `csv_line_no`
- 主なメソッド:
- `format_for_ui()` 表示文字列生成

#### `LayoutProcessResult`（dataclass）

- 目的: レイアウト単位の処理結果
- 主な項目:
- `target_count`, `success_count`
- `has_warning`, `has_error`
- `needs_review_suffix`（`_要確認` 判定）
- `messages`

#### `OperationResult`（dataclass）

- 目的: 主要処理全体の結果
- 主な項目:
- 成否系: `success`, `fatal_error`, `has_warning`, `has_error`
- 集計系: `target_layout_count`, `success_layout_count`, `warning_layout_count`, `failed_layout_count`
- 詳細系: `logs`, `layout_results`
- 主なメソッド:
- `add_log(log)` ログ追加と警告/エラーフラグ更新
- `summary_text()` 件数サマリ文字列生成

## 4. サービス層（`services/`）

### 4.1 `csv_service.py`

#### `CsvService.read_csv(csv_path)`

- 役割: 固定仕様CSVを読み込み `CsvLayoutDataset` に変換
- 返却:
- `tuple[OperationResult, CsvLayoutDataset]`
- 主な検証:
- 必須列 (`CSV_HEADERS`) の存在
- `layout_name` / `map_item_id` / Extent列の空値検証
- Extent列の `float` 変換
- `(layout_name, map_item_id)` 重複検出
- エラー方針:
- 行不正または重複が1件でもあれば `fatal_error=True`
- 最終的に空データセットを返す
- CSV空データ時:
- 成功扱いで `WARNING: CSVにデータ行がありません`

#### `CsvService.write_csv(csv_path, records)`

- 役割: `MapItemRecord` 一覧を固定列順でCSV出力
- 仕様:
- BOM付きUTF-8 (`utf-8-sig`)
- 全項目 `QUOTE_ALL`
- 親ディレクトリ自動作成
- 返却:
- `OperationResult`
- 主な失敗要因:
- ファイルI/O失敗
- CSV書き出し失敗

### 4.2 `layout_export_service.py`

#### `LayoutExportService.export_layouts(layout_names, csv_path)`

- 役割: 既存レイアウトから地図アイテム情報を収集してCSV出力
- 処理概要:
- 各レイアウトを名前検索
- `get_map_items()` で地図アイテム抽出
- `extent()` と `get_item_expression()` を `MapItemRecord` 化
- `CsvService.write_csv()` へ委譲
- 返却:
- `OperationResult`
- 判定:
- 書き出し成功 + 全レイアウト成功 -> `success=True`
- 書き出し成功 + 一部失敗 -> `success=True` かつ `has_warning=True`
- 書き出し失敗 -> `success=False`

### 4.3 `layout_import_service.py`

#### `LayoutImportService.apply_to_existing_layouts(dataset, target_layout_names)`

- 役割: CSVデータを既存レイアウトへ適用
- 対応ルール:
- `layout_name` 完全一致で対象レイアウト取得
- 地図アイテムは `itemById(map_item_id)` で解決
- 適用内容:
- Extent (`set_item_extent`)
- expression (`set_item_expression`)
- 警告ケース:
- CSV内に対象レイアウトなし
- プロジェクト内に対象レイアウトなし
- 地図アイテム数不一致
- `itemById()` 不一致
- エラーケース:
- QGIS API処理失敗
- 返却:
- `OperationResult`（`layout_results` にレイアウト別詳細を格納）

### 4.4 `layout_rebuild_service.py`

#### `LayoutRebuildService.rebuild_layouts(dataset, template_path, target_layout_names)`

- 役割: QPTテンプレートからレイアウトを再作成しCSV内容を反映
- 前処理:
- QPT読込 (`QDomDocument.setContent`)
- 対象ごとに同名既存レイアウト削除 (`remove_layout_if_exists`)
- 生成:
- `QgsPrintLayout.loadFromTemplate`
- 適用:
- `itemById()` で地図アイテム解決
- Extent/expression を設定
- 警告時:
- `needs_review_suffix=True`
- 新レイアウト名を `layout_name + "_要確認"` に変更
- 返却:
- `OperationResult`
- 致命エラー:
- テンプレート読込失敗、ファイルオープン失敗など

### 4.5 `layout_map_copy_service.py`

#### `LayoutMapCopyService.fetch_snapshot(source_layout_name, source_selection)`

- 役割: 元地図1件からコピー元スナップショットを取得
- 解決方法:
- レイアウト: `find_layout_by_name`
- 地図: `find_map_item_by_selection`（ID + occurrence_index）
- 取得内容:
- Extent4値 + expression
- 返却:
- `tuple[OperationResult, MapCopySnapshot | None]`
- 失敗時:
- `fatal_error=True` で `snapshot=None`

#### `LayoutMapCopyService.apply_snapshot(snapshot, target_layout_name, target_selections, apply_extent, apply_expression)`

- 役割: スナップショットを複数のコピー先地図へ反映
- 入力検証:
- snapshot必須
- コピー先レイアウト必須
- コピー先地図1件以上必須
- `apply_extent` / `apply_expression` のどちらか必須
- 適用:
- 地図解決は `find_map_item_by_selection`
- 選択に応じて Extent / expression を適用
- 返却:
- `OperationResult`
- 警告:
- コピー先地図が見つからない場合は継続

## 5. ユーティリティ層（`utils/`）

### 5.1 `csv_helpers.py`

#### `CSV_HEADERS`

- 役割: 固定CSV仕様の列定義
- 定義順:
- `layout_name`, `map_item_id`, `xmin`, `ymin`, `xmax`, `ymax`, `expression`
- 主な利用箇所:
- `CsvService.read_csv` の必須列検証
- `CsvService.write_csv` の列順出力

### 5.2 `logger.py`

#### `build_log(level, message, layout_name=None, map_item_id=None, csv_line_no=None)`

- 役割: `LogMessage` の一元生成
- 利点:
- ログ生成の引数形式を全層で統一
- `OperationResult.add_log` と組み合わせて状態管理を簡潔化

### 5.3 `qgis_layout_helpers.py`

QGIS API呼び出しを関数群へ集約し、失敗時は `RuntimeError` にラップして上位へ返す。

#### レイアウト一覧・検索

- `get_project_layout_names()`
- `get_project_layout_name_with_map_item_counts()`
- `find_layout_by_name(layout_name)`
- `remove_layout_if_exists(layout_name)`

#### 地図アイテム取得・識別

- `get_map_items(layout)` `QgsLayoutItemMap` のみ抽出
- `build_map_item_selections(layout)` 重複ID対応の表示・識別情報生成
- `get_layout_map_item_selections(layout_name)` 指定レイアウト版
- `find_map_item_by_selection(layout, selection)` ID+出現順で地図を特定

#### 属性取得・設定

- `get_item_expression(map_item)` `dataDefinedMapLayers.expression` 取得
- `set_item_extent(map_item, rectangle)` Extent設定
- `set_item_expression(map_item, expression)` expression設定

## 6. 典型フロー（層横断）

### 6.1 CSVインポート

1. `CsvService.read_csv()` でCSV検証・内部モデル化
2. `LayoutImportService.apply_to_existing_layouts()` でQGIS反映
3. `OperationResult.logs` と `summary_text()` をUIへ表示

### 6.2 再作成

1. `CsvService.read_csv()` で入力読込
2. `LayoutRebuildService.rebuild_layouts()` でテンプレート再作成
3. 警告発生レイアウトは `_要確認` 付与

### 6.3 地図コピー

1. `LayoutMapCopyService.fetch_snapshot()` で元地図情報を取得
2. `LayoutMapCopyService.apply_snapshot()` で複数地図へ反映
3. `OperationResult` で成功・警告・失敗をUI表示

## 7. 運用上の注意

- サービス層はUI部品を直接操作しない
- 実行結果は必ず `OperationResult` で扱う
- QGIS API直接呼び出しは可能な限り `qgis_layout_helpers.py` を経由する
- CSV列仕様変更時は `CSV_HEADERS` と `CsvService` の検証・入出力を同時更新する
