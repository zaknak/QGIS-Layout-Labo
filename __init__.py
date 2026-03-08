# -*- coding: utf-8 -*-
"""QGISプラグインのエントリポイントモジュール。"""

from .plugin import LayoutLaboPlugin


def classFactory(iface: object) -> LayoutLaboPlugin:
    """QGISからプラグインインスタンスを生成する。

    概要:
        QGISプラグインの標準エントリポイントとして、
        `LayoutLaboPlugin` のインスタンスを返す。

    引数:
        iface: QGISインターフェースオブジェクト。

    戻り値:
        LayoutLaboPlugin: プラグイン本体インスタンス。

    例外:
        なし。

    使用例:
        >>> plugin = classFactory(iface)
    """
    return LayoutLaboPlugin(iface)
