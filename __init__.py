# -*- coding: utf-8 -*-
"""QGISプラグインのエントリポイントモジュール。"""

from .plugin import LayoutMapTransferPlugin


def classFactory(iface: object) -> LayoutMapTransferPlugin:
    """QGISからプラグインインスタンスを生成する。

    概要:
        QGISプラグインの標準エントリポイントとして、
        `LayoutMapTransferPlugin` のインスタンスを返す。

    引数:
        iface: QGISインターフェースオブジェクト。

    戻り値:
        LayoutMapTransferPlugin: プラグイン本体インスタンス。

    例外:
        なし。

    使用例:
        >>> plugin = classFactory(iface)
    """
    return LayoutMapTransferPlugin(iface)
