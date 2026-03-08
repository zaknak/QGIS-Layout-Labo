# -*- coding: utf-8 -*-
"""プラグイン起動処理モジュール。"""

from __future__ import annotations

import os
from typing import Optional

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialogs.main_dialog import MainDialog


class LayoutLaboPlugin:
    """QGISプラグイン本体クラス。

    概要:
        QGISへのアクション登録、メインダイアログ起動、
        アンロード処理を担当する。

    引数:
        iface: QGISインターフェースオブジェクト。

    戻り値:
        なし。

    例外:
        なし。

    使用例:
        >>> plugin = LayoutLaboPlugin(iface)
        >>> plugin.initGui()
    """

    def __init__(self, iface: object) -> None:
        """プラグインインスタンスを初期化する。

        概要:
            インターフェース参照やGUIアクション保持領域を初期化する。

        引数:
            iface: QGISインターフェースオブジェクト。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> plugin = LayoutLaboPlugin(iface)
        """
        self.iface = iface
        self.action: Optional[QAction] = None
        self.dialog: Optional[MainDialog] = None

    def initGui(self) -> None:
        """QGIS GUIへアクションを登録する。

        概要:
            ツールバーとプラグインメニューへ起動アクションを追加する。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> plugin.initGui()
        """
        icon_path: str = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), "Layout Labo", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Layout Labo", self.action)

    def unload(self) -> None:
        """QGIS GUIからアクションを解除する。

        概要:
            プラグイン無効化時にメニューとツールバーからアクションを外す。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> plugin.unload()
        """
        if self.action is None:
            return
        self.iface.removePluginMenu("Layout Labo", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self) -> None:
        """メインダイアログを表示する。

        概要:
            ダイアログが未生成の場合のみ生成し、表示時に前面へ出す。

        引数:
            なし。

        戻り値:
            なし。

        例外:
            なし。

        使用例:
            >>> plugin.run()
        """
        if self.dialog is None:
            self.dialog = MainDialog(parent=self.iface.mainWindow(), iface=self.iface)
        self.dialog.prepare_for_show()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
