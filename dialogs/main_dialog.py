# -*- coding: utf-8 -*-
"""メインダイアログUI制御。"""

from __future__ import annotations

import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
)

from ..models.csv_layout_dataset import CsvLayoutDataset
from ..models.map_copy_snapshot import MapCopySnapshot
from ..models.map_item_selection import MapItemSelection
from ..models.operation_result import LogLevel, OperationResult
from ..services.csv_service import CsvService
from ..services.layout_export_service import LayoutExportService
from ..services.layout_import_service import LayoutImportService
from ..services.layout_map_copy_service import LayoutMapCopyService
from ..services.layout_rebuild_service import LayoutRebuildService
from ..utils.logger import build_log
from ..utils.qgis_layout_helpers import (
    get_layout_map_item_selections,
    get_project_layout_name_with_map_item_counts,
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "main_dialog.ui"))


class MainDialog(QDialog, FORM_CLASS):
    """プラグインの単一メインダイアログ。

    概要:
        `.ui` を読み込み、入力取得、イベント接続、
        サービス結果のUI反映を担当する。

    引数:
        parent: 親ウィジェット。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> dialog = MainDialog()
        >>> dialog.prepare_for_show()
    """

    def __init__(self, parent: object | None = None) -> None:
        """ダイアログ初期化を行う。

        概要:
            UIロード、サービス生成、ウィジェット初期化、シグナル接続を実施する。

        引数:
            parent: 親ウィジェット。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog = MainDialog(parent=None)
        """
        super().__init__(parent)
        self.setupUi(self)

        self._csv_service = CsvService()
        self._layout_export_service = LayoutExportService(csv_service=self._csv_service)
        self._layout_import_service = LayoutImportService()
        self._layout_rebuild_service = LayoutRebuildService()
        self._layout_map_copy_service = LayoutMapCopyService()

        self._import_dataset = CsvLayoutDataset()
        self._rebuild_dataset = CsvLayoutDataset()

        self._source_map_selections: list[MapItemSelection] = []
        self._target_map_selections: list[MapItemSelection] = []
        self._map_copy_snapshot: MapCopySnapshot | None = None

        self._configure_widgets()
        self._connect_signals()

    def prepare_for_show(self) -> None:
        """表示前準備を行う。

        概要:
            ダイアログ表示のたびにレイアウト一覧を再取得してUIへ反映する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog.prepare_for_show()
        """
        self.refresh_project_layout_lists()

    def _configure_widgets(self) -> None:
        """ウィジェットの初期表示設定を行う。

        概要:
            ログ欄の読取専用化や複数選択設定などの初期状態を統一する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._configure_widgets()
        """
        self.textEditLogs.setReadOnly(True)
        self.textEditMapCopySnapshot.setReadOnly(True)
        self.labelSummary.setText("")
        for list_widget in (
            self.listWidgetExportLayouts,
            self.listWidgetImportCsvLayouts,
            self.listWidgetImportTargetLayouts,
            self.listWidgetRebuildCsvLayouts,
            self.listWidgetRebuildTargetLayouts,
            self.listWidgetMapCopyTargets,
        ):
            list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        self.checkMapCopyExtent.setChecked(True)
        self.checkMapCopyExpression.setChecked(False)

    def _connect_signals(self) -> None:
        """UIイベントのシグナル接続を行う。

        概要:
            ボタン押下やタブ切替イベントをハンドラへ接続する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._connect_signals()
        """
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
        self.btnExportReload.clicked.connect(self.refresh_project_layout_lists)
        self.btnImportReload.clicked.connect(self.refresh_project_layout_lists)
        self.btnRebuildReload.clicked.connect(self.refresh_project_layout_lists)
        self.btnMapCopyReload.clicked.connect(self.refresh_project_layout_lists)
        self.btnExportBrowse.clicked.connect(self._browse_export_csv)
        self.btnImportBrowse.clicked.connect(self._browse_import_csv)
        self.btnRebuildCsvBrowse.clicked.connect(self._browse_rebuild_csv)
        self.btnTemplateBrowse.clicked.connect(self._browse_template)
        self.btnExportRun.clicked.connect(self._run_export)
        self.btnImportRun.clicked.connect(self._run_import)
        self.btnRebuildRun.clicked.connect(self._run_rebuild)
        self.comboMapCopySourceLayout.currentIndexChanged.connect(self._on_map_copy_source_layout_changed)
        self.comboMapCopySourceMap.currentIndexChanged.connect(self._on_map_copy_source_map_changed)
        self.comboMapCopyTargetLayout.currentIndexChanged.connect(self._on_map_copy_target_layout_changed)
        self.btnMapCopyCapture.clicked.connect(self._capture_map_copy_snapshot)
        self.btnMapCopyRun.clicked.connect(self._run_map_copy)

    def _on_tab_changed(self, _index: int) -> None:
        """タブ切替イベント時に一覧再読込を行う。

        概要:
            キャッシュ固定禁止要件に従い、タブ切替時に毎回再取得する。

        引数:
            _index: 選択タブインデックス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._on_tab_changed(0)
        """
        self.refresh_project_layout_lists()

    def refresh_project_layout_lists(self) -> None:
        """プロジェクトレイアウト一覧をUIへ反映する。

        概要:
            現在のQGISプロジェクト状態からレイアウト名と地図アイテム数を再取得し、
            各タブの対象選択リストへ設定する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog.refresh_project_layout_lists()
        """
        try:
            layout_entries = get_project_layout_name_with_map_item_counts()
        except RuntimeError as exc:
            self._append_result_logs(
                OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, str(exc))])
            )
            return

        self._set_items_with_checkboxes(self.listWidgetExportLayouts, layout_entries)
        self._set_items_with_checkboxes(self.listWidgetImportTargetLayouts, layout_entries)
        self._set_items_with_checkboxes(self.listWidgetRebuildTargetLayouts, layout_entries)
        self._set_layout_combo_items(self.comboMapCopySourceLayout, layout_entries)
        self._set_layout_combo_items(self.comboMapCopyTargetLayout, layout_entries)
        self._reload_map_copy_source_map_items()
        self._reload_map_copy_target_map_items()

    def _set_items_with_checkboxes(self, list_widget: QListWidget, items: list[tuple[str, int]]) -> None:
        """チェックボックス付きリスト項目を再構築する。

        概要:
            渡されたレイアウト名と地図アイテム数の一覧を全消去後に
            チェックボックス項目として登録する。

        引数:
            list_widget: 設定対象リスト。
            items: 表示項目一覧。要素は `(layout_name, map_item_count)`。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._set_items_with_checkboxes(widget, [("A", 2), ("B", 1)])
        """
        list_widget.clear()
        for layout_name, map_item_count in items:
            display_text = f"{layout_name} ({map_item_count})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, layout_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            list_widget.addItem(item)

    def _set_layout_combo_items(self, combo_box: QComboBox, items: list[tuple[str, int]]) -> None:
        """レイアウト選択コンボボックス項目を再構築する。

        概要:
            レイアウト名と地図アイテム数の表示を設定し、可能なら前回選択を復元する。

        引数:
            combo_box: 設定対象コンボボックス。
            items: 表示項目一覧。要素は `(layout_name, map_item_count)`。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._set_layout_combo_items(combo, [("A", 2)])
        """
        previous_layout_name = self._get_selected_layout_name(combo_box)
        combo_box.blockSignals(True)
        combo_box.clear()
        for layout_name, map_item_count in items:
            combo_box.addItem(f"{layout_name} ({map_item_count})", layout_name)
        if combo_box.count() > 0:
            target_index = 0
            if previous_layout_name:
                for index in range(combo_box.count()):
                    data = combo_box.itemData(index)
                    if isinstance(data, str) and data == previous_layout_name:
                        target_index = index
                        break
            combo_box.setCurrentIndex(target_index)
        combo_box.blockSignals(False)

    def _get_checked_items(self, list_widget: QListWidget) -> list[str]:
        """チェック済み項目のレイアウト名一覧を返す。

        概要:
            リストウィジェット内のチェック状態を走査し、
            `Qt.UserRole` に保持した生のレイアウト名を収集する。

        引数:
            list_widget: 取得対象リスト。

        戻り値:
            list[str]: チェック済みレイアウト名一覧。

        例外:
            なし。

        使用例:
            >>> selected = dialog._get_checked_items(widget)
        """
        checked: list[str] = []
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if item.checkState() == Qt.Checked:
                raw_layout_name = item.data(Qt.UserRole)
                if isinstance(raw_layout_name, str) and raw_layout_name:
                    checked.append(raw_layout_name)
                else:
                    checked.append(item.text())
        return checked

    def _get_selected_layout_name(self, combo_box: QComboBox) -> str:
        """コンボボックスの現在選択レイアウト名を返す。

        概要:
            `itemData` から選択レイアウト名を取得し、未選択時は空文字を返す。

        引数:
            combo_box: 取得対象コンボボックス。

        戻り値:
            str: レイアウト名。未選択時は空文字。

        例外:
            なし。

        使用例:
            >>> name = dialog._get_selected_layout_name(combo)
        """
        data = combo_box.currentData()
        if isinstance(data, str):
            return data
        return ""

    def _selection_key(self, selection: MapItemSelection) -> tuple[str, int]:
        """地図選択情報の比較キーを返す。

        概要:
            UI再構築時の選択復元に使うキーを生成する。

        引数:
            selection: 対象の地図選択情報。

        戻り値:
            tuple[str, int]: `(map_item_id, occurrence_index)`。

        例外:
            なし。

        使用例:
            >>> key = dialog._selection_key(selection)
        """
        return (selection.map_item_id, selection.occurrence_index)

    def _browse_export_csv(self) -> None:
        """エクスポート先CSVを選択する。

        概要:
            保存ダイアログを開き、選択結果を入力欄へ設定する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._browse_export_csv()
        """
        path, _ = QFileDialog.getSaveFileName(self, "CSV保存先", "", "CSV (*.csv)")
        if path:
            self.lineEditExportCsv.setText(path)

    def _browse_import_csv(self) -> None:
        """インポート用CSVを選択する。

        概要:
            ファイルダイアログでCSVを選択し、読み込み処理を起動する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._browse_import_csv()
        """
        path, _ = QFileDialog.getOpenFileName(self, "CSV選択", "", "CSV (*.csv)")
        if not path:
            return
        self.lineEditImportCsv.setText(path)
        self._load_csv_for_import(path)

    def _browse_rebuild_csv(self) -> None:
        """再作成用CSVを選択する。

        概要:
            ファイルダイアログでCSVを選択し、読み込み処理を起動する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._browse_rebuild_csv()
        """
        path, _ = QFileDialog.getOpenFileName(self, "CSV選択", "", "CSV (*.csv)")
        if not path:
            return
        self.lineEditRebuildCsv.setText(path)
        self._load_csv_for_rebuild(path)

    def _browse_template(self) -> None:
        """テンプレートQPTを選択する。

        概要:
            ファイルダイアログでQPTを選択し、入力欄へ設定する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._browse_template()
        """
        path, _ = QFileDialog.getOpenFileName(self, "テンプレート選択", "", "QGIS Template (*.qpt)")
        if path:
            self.lineEditTemplate.setText(path)

    def _load_csv_for_import(self, path: str) -> None:
        """インポート用CSVを読み込む。

        概要:
            CSVサービスで読み込み、結果ログ表示と一覧反映を行う。

        引数:
            path: CSVファイルパス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._load_csv_for_import("/tmp/input.csv")
        """
        result, dataset = self._csv_service.read_csv(path)
        self._append_result_logs(result)
        if result.success:
            self._import_dataset = dataset
            self._set_items_with_checkboxes(self.listWidgetImportCsvLayouts, dataset.get_layout_name_with_counts())

    def _load_csv_for_rebuild(self, path: str) -> None:
        """再作成用CSVを読み込む。

        概要:
            CSVサービスで読み込み、結果ログ表示と一覧反映を行う。

        引数:
            path: CSVファイルパス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._load_csv_for_rebuild("/tmp/input.csv")
        """
        result, dataset = self._csv_service.read_csv(path)
        self._append_result_logs(result)
        if result.success:
            self._rebuild_dataset = dataset
            self._set_items_with_checkboxes(self.listWidgetRebuildCsvLayouts, dataset.get_layout_name_with_counts())

    def _reload_map_copy_source_map_items(self) -> None:
        """元地図選択コンボボックスを再構築する。

        概要:
            現在の元レイアウトに属する地図アイテムを取得し、
            重複IDを区別できる表示名でコンボボックスへ設定する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._reload_map_copy_source_map_items()
        """
        layout_name = self._get_selected_layout_name(self.comboMapCopySourceLayout)
        previous_selection = self._get_selected_source_map_selection()
        try:
            self._source_map_selections = get_layout_map_item_selections(layout_name) if layout_name else []
        except RuntimeError as exc:
            self._source_map_selections = []
            self._append_result_logs(
                OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, str(exc))])
            )

        previous_key = self._selection_key(previous_selection) if previous_selection is not None else None
        self.comboMapCopySourceMap.blockSignals(True)
        self.comboMapCopySourceMap.clear()
        for index, selection in enumerate(self._source_map_selections):
            self.comboMapCopySourceMap.addItem(selection.display_name, index)
        if self.comboMapCopySourceMap.count() > 0:
            target_index = 0
            if previous_key is not None:
                for index, selection in enumerate(self._source_map_selections):
                    if self._selection_key(selection) == previous_key:
                        target_index = index
                        break
            self.comboMapCopySourceMap.setCurrentIndex(target_index)
        self.comboMapCopySourceMap.blockSignals(False)

    def _reload_map_copy_target_map_items(self) -> None:
        """コピー先地図リストを再構築する。

        概要:
            現在のコピー先レイアウトに属する地図アイテムを取得し、
            チェックボックス付き複数選択リストへ設定する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._reload_map_copy_target_map_items()
        """
        layout_name = self._get_selected_layout_name(self.comboMapCopyTargetLayout)
        previous_checked_keys = {self._selection_key(selection) for selection in self._get_checked_target_map_selections()}
        try:
            self._target_map_selections = get_layout_map_item_selections(layout_name) if layout_name else []
        except RuntimeError as exc:
            self._target_map_selections = []
            self._append_result_logs(
                OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, str(exc))])
            )

        self.listWidgetMapCopyTargets.clear()
        for index, selection in enumerate(self._target_map_selections):
            item = QListWidgetItem(selection.display_name)
            item.setData(Qt.UserRole, index)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self._selection_key(selection) in previous_checked_keys:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.listWidgetMapCopyTargets.addItem(item)

    def _on_map_copy_source_layout_changed(self, _index: int) -> None:
        """元レイアウト変更時の処理を行う。

        概要:
            元地図一覧を再取得し、既存スナップショットを破棄する。

        引数:
            _index: 変更後インデックス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._on_map_copy_source_layout_changed(0)
        """
        self._reload_map_copy_source_map_items()
        self._clear_map_copy_snapshot()

    def _on_map_copy_source_map_changed(self, _index: int) -> None:
        """元地図変更時の処理を行う。

        概要:
            元地図が変更されたため、既存スナップショットを破棄する。

        引数:
            _index: 変更後インデックス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._on_map_copy_source_map_changed(0)
        """
        self._clear_map_copy_snapshot()

    def _on_map_copy_target_layout_changed(self, _index: int) -> None:
        """コピー先レイアウト変更時の処理を行う。

        概要:
            コピー先地図一覧を再取得し、チェック可能リストを更新する。

        引数:
            _index: 変更後インデックス。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._on_map_copy_target_layout_changed(0)
        """
        self._reload_map_copy_target_map_items()

    def _clear_map_copy_snapshot(self) -> None:
        """地図コピー用スナップショットをクリアする。

        概要:
            保持中のスナップショットを破棄し、表示欄を初期文言へ戻す。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._clear_map_copy_snapshot()
        """
        self._map_copy_snapshot = None
        self.textEditMapCopySnapshot.setPlainText("未取得")

    def _get_selected_source_map_selection(self) -> MapItemSelection | None:
        """元地図コンボボックスの現在選択を返す。

        概要:
            コンボボックスの `itemData` を使い、元地図選択情報を返す。

        引数:
            なし。

        戻り値:
            MapItemSelection | None: 選択情報。未選択時はNone。

        例外:
            なし。

        使用例:
            >>> selection = dialog._get_selected_source_map_selection()
        """
        data = self.comboMapCopySourceMap.currentData()
        if not isinstance(data, int):
            return None
        if data < 0 or data >= len(self._source_map_selections):
            return None
        return self._source_map_selections[data]

    def _get_checked_target_map_selections(self) -> list[MapItemSelection]:
        """コピー先地図リストのチェック済み選択を返す。

        概要:
            複数選択リストのチェック状態を走査し、
            選択された地図アイテム識別情報を返す。

        引数:
            なし。

        戻り値:
            list[MapItemSelection]: チェック済み選択情報一覧。

        例外:
            なし。

        使用例:
            >>> selections = dialog._get_checked_target_map_selections()
        """
        checked: list[MapItemSelection] = []
        for index in range(self.listWidgetMapCopyTargets.count()):
            item = self.listWidgetMapCopyTargets.item(index)
            if item.checkState() != Qt.Checked:
                continue
            data = item.data(Qt.UserRole)
            if not isinstance(data, int):
                continue
            if data < 0 or data >= len(self._target_map_selections):
                continue
            checked.append(self._target_map_selections[data])
        return checked

    def _format_snapshot_text(self, snapshot: MapCopySnapshot) -> str:
        """スナップショット表示テキストを生成する。

        概要:
            UI表示用に元レイアウト、元地図、Extent、expressionを整形する。

        引数:
            snapshot: 表示対象スナップショット。

        戻り値:
            str: 表示テキスト。

        例外:
            なし。

        使用例:
            >>> text = dialog._format_snapshot_text(snapshot)
        """
        return (
            f"layout={snapshot.source_layout_name}\n"
            f"map={snapshot.source_display_name}\n"
            f"xmin={snapshot.xmin}\n"
            f"ymin={snapshot.ymin}\n"
            f"xmax={snapshot.xmax}\n"
            f"ymax={snapshot.ymax}\n"
            f"expression={snapshot.expression}"
        )

    def _capture_map_copy_snapshot(self) -> None:
        """元地図からスナップショットを取得する。

        概要:
            元レイアウトと元地図選択を検証し、
            サービス経由でExtentとexpressionを取得して保持する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._capture_map_copy_snapshot()
        """
        source_layout_name = self._get_selected_layout_name(self.comboMapCopySourceLayout)
        source_selection = self._get_selected_source_map_selection()

        if not source_layout_name:
            self._append_result_logs(
                OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "元レイアウト未選択です")])
            )
            return
        if source_selection is None:
            self._append_result_logs(
                OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "元地図アイテム未選択です")])
            )
            return

        result, snapshot = self._layout_map_copy_service.fetch_snapshot(source_layout_name, source_selection)
        self._append_result_logs(result)
        if result.success and snapshot is not None:
            self._map_copy_snapshot = snapshot
            self.textEditMapCopySnapshot.setPlainText(self._format_snapshot_text(snapshot))

    def _run_export(self) -> None:
        """エクスポート処理を実行する。

        概要:
            入力検証後にエクスポートサービスを呼び、結果を反映する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._run_export()
        """
        selected_layouts = self._get_checked_items(self.listWidgetExportLayouts)
        csv_path = self.lineEditExportCsv.text().strip()
        validation = self._validate_export_input(selected_layouts, csv_path)
        if validation is not None:
            self._append_result_logs(validation)
            return
        result = self._layout_export_service.export_layouts(selected_layouts, csv_path)
        self._append_result_logs(result)
        self.refresh_project_layout_lists()

    def _run_import(self) -> None:
        """インポート処理を実行する。

        概要:
            入力検証後にCSV再読込と適用処理を実施し、結果を反映する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._run_import()
        """
        csv_path = self.lineEditImportCsv.text().strip()
        selected_targets = self._get_checked_items(self.listWidgetImportTargetLayouts)
        validation = self._validate_import_input(csv_path, selected_targets)
        if validation is not None:
            self._append_result_logs(validation)
            return
        self._load_csv_for_import(csv_path)
        result = self._layout_import_service.apply_to_existing_layouts(self._import_dataset, selected_targets)
        self._append_result_logs(result)
        self.refresh_project_layout_lists()

    def _run_rebuild(self) -> None:
        """再作成処理を実行する。

        概要:
            入力検証後にCSV再読込と再作成処理を実施し、結果を反映する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._run_rebuild()
        """
        csv_path = self.lineEditRebuildCsv.text().strip()
        template_path = self.lineEditTemplate.text().strip()
        selected_targets = self._get_checked_items(self.listWidgetRebuildTargetLayouts)
        validation = self._validate_rebuild_input(csv_path, template_path, selected_targets)
        if validation is not None:
            self._append_result_logs(validation)
            return
        self._load_csv_for_rebuild(csv_path)
        result = self._layout_rebuild_service.rebuild_layouts(
            dataset=self._rebuild_dataset,
            template_path=template_path,
            target_layout_names=selected_targets,
        )
        self._append_result_logs(result)
        self.refresh_project_layout_lists()

    def _run_map_copy(self) -> None:
        """地図コピー処理を実行する。

        概要:
            保持済みスナップショットとコピー先選択を検証し、
            サービス経由でEXTENT/expressionを適用する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._run_map_copy()
        """
        target_layout_name = self._get_selected_layout_name(self.comboMapCopyTargetLayout)
        target_selections = self._get_checked_target_map_selections()
        apply_extent = self.checkMapCopyExtent.isChecked()
        apply_expression = self.checkMapCopyExpression.isChecked()

        validation = self._validate_map_copy_input(
            snapshot=self._map_copy_snapshot,
            target_layout_name=target_layout_name,
            target_selections=target_selections,
            apply_extent=apply_extent,
            apply_expression=apply_expression,
        )
        if validation is not None:
            self._append_result_logs(validation)
            return

        result = self._layout_map_copy_service.apply_snapshot(
            snapshot=self._map_copy_snapshot,
            target_layout_name=target_layout_name,
            target_selections=target_selections,
            apply_extent=apply_extent,
            apply_expression=apply_expression,
        )
        self._append_result_logs(result)
        self.refresh_project_layout_lists()

    def _validate_export_input(self, layout_names: list[str], csv_path: str) -> OperationResult | None:
        """エクスポート入力の検証を行う。

        概要:
            レイアウト選択とCSV出力パスの必須チェックを行う。

        引数:
            layout_names: 選択レイアウト名一覧。
            csv_path: CSV出力パス。

        戻り値:
            OperationResult | None: エラー時は結果オブジェクト、問題ない場合None。

        例外:
            なし。

        使用例:
            >>> err = dialog._validate_export_input(["A"], "/tmp/a.csv")
        """
        if not layout_names:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "レイアウト未選択です")])
        if not csv_path:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "CSVパス未指定です")])
        return None

    def _validate_import_input(self, csv_path: str, target_layouts: list[str]) -> OperationResult | None:
        """インポート入力の検証を行う。

        概要:
            CSV指定と適用対象選択の必須チェックを行う。

        引数:
            csv_path: CSVパス。
            target_layouts: 適用対象レイアウト名一覧。

        戻り値:
            OperationResult | None: エラー時は結果オブジェクト、問題ない場合None。

        例外:
            なし。

        使用例:
            >>> err = dialog._validate_import_input("/tmp/a.csv", ["A"])
        """
        if not csv_path:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "CSVファイル未指定です")])
        if not target_layouts:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "適用対象レイアウト未選択です")])
        return None

    def _validate_rebuild_input(self, csv_path: str, template_path: str, target_layouts: list[str]) -> OperationResult | None:
        """再作成入力の検証を行う。

        概要:
            CSV、テンプレート、再作成対象選択の必須チェックを行う。

        引数:
            csv_path: CSVパス。
            template_path: テンプレートQPTパス。
            target_layouts: 再作成対象レイアウト名一覧。

        戻り値:
            OperationResult | None: エラー時は結果オブジェクト、問題ない場合None。

        例外:
            なし。

        使用例:
            >>> err = dialog._validate_rebuild_input("/tmp/a.csv", "/tmp/t.qpt", ["A"])
        """
        if not csv_path:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "CSVファイル未指定です")])
        if not template_path:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "テンプレート未指定です")])
        if not target_layouts:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "再作成対象レイアウト未選択です")])
        return None

    def _validate_map_copy_input(
        self,
        snapshot: MapCopySnapshot | None,
        target_layout_name: str,
        target_selections: list[MapItemSelection],
        apply_extent: bool,
        apply_expression: bool,
    ) -> OperationResult | None:
        """地図コピー入力の検証を行う。

        概要:
            スナップショット、コピー先、コピー対象指定の必須チェックを行う。

        引数:
            snapshot: 保持済みスナップショット。
            target_layout_name: コピー先レイアウト名。
            target_selections: コピー先地図選択情報。
            apply_extent: Extent適用可否。
            apply_expression: expression適用可否。

        戻り値:
            OperationResult | None: エラー時は結果オブジェクト、問題ない場合None。

        例外:
            なし。

        使用例:
            >>> err = dialog._validate_map_copy_input(snapshot, "LayoutB", selections, True, False)
        """
        if snapshot is None:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "取得スナップショット未作成です")])
        if not target_layout_name:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "コピー先レイアウト未選択です")])
        if not target_selections:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "コピー先地図アイテム未選択です")])
        if not apply_extent and not apply_expression:
            return OperationResult(success=False, fatal_error=True, has_error=True, logs=[build_log(LogLevel.ERROR, "コピー対象（EXTENT / expression）未選択です")])
        return None

    def _append_result_logs(self, result: OperationResult) -> None:
        """結果ログとサマリをUIへ反映する。

        概要:
            サービス層の結果オブジェクトを受けてログ欄へ追記し、
            サマリラベルを更新する。

        引数:
            result: 反映対象の結果オブジェクト。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> dialog._append_result_logs(result)
        """
        for log in result.logs:
            self.textEditLogs.append(log.format_for_ui())
        self.labelSummary.setText(result.summary_text())
