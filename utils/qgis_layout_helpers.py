# -*- coding: utf-8 -*-
"""QGISレイアウト操作ヘルパー。"""

from __future__ import annotations

from qgis.PyQt.QtCore import QPointF, QRectF
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import (
    QgsLayoutItem,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayerTreeLayer,
    QgsLayoutObject,
    QgsProject,
    QgsProperty,
    QgsRectangle,
    QgsReadWriteContext,
)

from ..models.layout_item_selection import LayoutItemSelection
from ..models.map_item_selection import MapItemSelection


LAYER_DISPLAY_MODE_DEFAULT = "既定"
LAYER_DISPLAY_MODE_EXPRESSION = "式"
LAYER_DISPLAY_MODE_FIXED = "固定"


def get_project_layout_names() -> list[str]:
    """現在プロジェクトのレイアウト名一覧を返す。

    概要:
        QGISプロジェクトからレイアウト名を取得して昇順で返す。

    引数:
        なし。

    戻り値:
        list[str]: レイアウト名一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> names = get_project_layout_names()
    """
    try:
        manager = QgsProject.instance().layoutManager()
        names: list[str] = [layout.name() for layout in manager.layouts()]
        return sorted(names)
    except Exception as exc:
        raise RuntimeError(f"レイアウト一覧の取得に失敗しました: {exc}") from exc


def get_project_layout_name_with_map_item_counts() -> list[tuple[str, int]]:
    """現在プロジェクトのレイアウト名と地図アイテム数を返す。

    概要:
        QGISプロジェクトから各レイアウトを取得し、
        レイアウト名昇順で `(layout_name, map_item_count)` の一覧を返す。

    引数:
        なし。

    戻り値:
        list[tuple[str, int]]: レイアウト名と地図アイテム数の一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> entries = get_project_layout_name_with_map_item_counts()
    """
    try:
        manager = QgsProject.instance().layoutManager()
        entries: list[tuple[str, int]] = []
        for layout in manager.layouts():
            map_item_count = len(get_map_items(layout))
            entries.append((layout.name(), map_item_count))
        return sorted(entries, key=lambda entry: entry[0])
    except Exception as exc:
        raise RuntimeError(f"レイアウト一覧の取得に失敗しました: {exc}") from exc


def get_project_layout_name_with_item_counts() -> list[tuple[str, int]]:
    """現在プロジェクトのレイアウト名と非ページアイテム数を返す。

    概要:
        各レイアウトからページ以外のレイアウトアイテム数を取得し、
        レイアウト名昇順で `(layout_name, item_count)` の一覧を返す。

    引数:
        なし。

    戻り値:
        list[tuple[str, int]]: レイアウト名と非ページアイテム数の一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> entries = get_project_layout_name_with_item_counts()
    """
    try:
        manager = QgsProject.instance().layoutManager()
        entries: list[tuple[str, int]] = []
        for layout in manager.layouts():
            item_count = len(get_layout_items(layout))
            entries.append((layout.name(), item_count))
        return sorted(entries, key=lambda entry: entry[0])
    except Exception as exc:
        raise RuntimeError(f"レイアウト一覧の取得に失敗しました: {exc}") from exc


def get_project_layer_names_in_tree_order() -> list[str]:
    """レイヤパネル順のレイヤ名一覧を返す。

    概要:
        QGISプロジェクトのレイヤツリーから表示順でレイヤ名を取得する。

    引数:
        なし。

    戻り値:
        list[str]: レイヤパネル順のレイヤ名一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> names = get_project_layer_names_in_tree_order()
    """
    try:
        root = QgsProject.instance().layerTreeRoot()
        names: list[str] = []
        for layer_node in root.findLayers():
            if not isinstance(layer_node, QgsLayerTreeLayer):
                continue
            layer = layer_node.layer()
            if layer is None:
                continue
            names.append(layer.name())
        return names
    except Exception as exc:
        raise RuntimeError(f"レイヤ一覧の取得に失敗しました: {exc}") from exc


def get_map_items(layout: object) -> list[QgsLayoutItemMap]:
    """レイアウト内の地図アイテム一覧を取得する。

    概要:
        指定レイアウトから `QgsLayoutItemMap` のみ抽出する。

    引数:
        layout: 対象レイアウト。

    戻り値:
        list[QgsLayoutItemMap]: 地図アイテム一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> maps = get_map_items(layout)
    """
    try:
        items: list[QgsLayoutItemMap] = []
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                items.append(item)
        return items
    except Exception as exc:
        raise RuntimeError(f"地図アイテムの取得に失敗しました: {exc}") from exc


def get_layout_items(layout: object) -> list[QgsLayoutItem]:
    """レイアウト内の非ページアイテム一覧を取得する。

    概要:
        指定レイアウトから `QgsLayoutItemPage` を除く
        `QgsLayoutItem` 一覧を抽出する。

    引数:
        layout: 対象レイアウト。

    戻り値:
        list[QgsLayoutItem]: 非ページレイアウトアイテム一覧。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> items = get_layout_items(layout)
    """
    try:
        items: list[QgsLayoutItem] = []
        for item in layout.items():
            if not isinstance(item, QgsLayoutItem):
                continue
            if isinstance(item, QgsLayoutItemPage):
                continue
            items.append(item)
        return items
    except Exception as exc:
        raise RuntimeError(f"レイアウトアイテムの取得に失敗しました: {exc}") from exc


def build_map_item_selections(layout: object) -> list[MapItemSelection]:
    """レイアウト内地図アイテムの選択情報一覧を返す。

    概要:
        同一 `map_item_id` の重複に対応するため、
        出現順連番と表示レイヤ設定モード付きの表示名を持つ
        選択情報を生成する。

    引数:
        layout: 対象レイアウト。

    戻り値:
        list[MapItemSelection]: UI選択用の地図アイテム識別情報一覧。

    例外:
        RuntimeError: 地図アイテム取得に失敗した場合。

    使用例:
        >>> selections = build_map_item_selections(layout)
    """
    map_items = get_map_items(layout)
    id_counts: dict[str, int] = {}
    selections: list[MapItemSelection] = []
    for item in map_items:
        map_item_id = item.id() or ""
        occurrence_index = id_counts.get(map_item_id, 0) + 1
        id_counts[map_item_id] = occurrence_index
        layer_display_mode, layer_display_expression = get_map_item_layer_display_state(item)
        display_name = build_map_item_display_name(
            map_item_id=map_item_id,
            occurrence_index=occurrence_index,
            layer_display_mode=layer_display_mode,
            layer_display_expression=layer_display_expression,
        )
        selections.append(
            MapItemSelection(
                map_item_id=map_item_id,
                occurrence_index=occurrence_index,
                layer_display_mode=layer_display_mode,
                layer_display_expression=layer_display_expression,
                display_name=display_name,
            )
        )
    return selections


def build_map_item_display_name(
    map_item_id: str,
    occurrence_index: int,
    layer_display_mode: str,
    layer_display_expression: str,
) -> str:
    """地図アイテム選択候補の表示名を組み立てる。

    概要:
        識別用連番と表示レイヤ設定モードを含む表示名を返す。
        `式` モード時のみexpression内容を付加する。

    引数:
        map_item_id: 地図アイテムID。
        occurrence_index: 同一ID内での1始まり出現順。
        layer_display_mode: 表示レイヤ設定モード。
        layer_display_expression: `式` モード時に表示するexpression。

    戻り値:
        str: UI表示名。

    例外:
        なし。

    使用例:
        >>> build_map_item_display_name("map1", 1, "既定", "")
        'map1 (#1) [既定]'
    """
    base_name = f"{map_item_id} (#{occurrence_index})"
    if layer_display_mode == LAYER_DISPLAY_MODE_EXPRESSION and layer_display_expression:
        return f"{base_name} [{layer_display_mode}: {layer_display_expression}]"
    return f"{base_name} [{layer_display_mode}]"


def build_layout_item_selections(layout: object) -> list[LayoutItemSelection]:
    """レイアウト内非ページアイテムの選択情報一覧を返す。

    概要:
        各レイアウトアイテムのUUID、種別、item id、所属ページを
        UI選択用の `LayoutItemSelection` として返す。

    引数:
        layout: 対象レイアウト。

    戻り値:
        list[LayoutItemSelection]: UI選択用の識別情報一覧。

    例外:
        RuntimeError: レイアウトアイテム取得や表示情報生成に失敗した場合。

    使用例:
        >>> selections = build_layout_item_selections(layout)
    """
    selections: list[LayoutItemSelection] = []
    for item in get_layout_items(layout):
        item_id = ""
        item_id_method = getattr(item, "id", None)
        if callable(item_id_method):
            item_id = item_id_method() or ""
        item_uuid_method = getattr(item, "uuid", None)
        item_uuid = item_uuid_method() if callable(item_uuid_method) else ""
        item_type_name = get_layout_item_type_name(item)
        page_name = get_layout_item_page_name(item)
        display_id = item_id or "(IDなし)"
        display_name = f"{item_type_name} / {display_id} / {page_name}"
        selections.append(
            LayoutItemSelection(
                item_uuid=item_uuid,
                item_id=item_id,
                item_type_name=item_type_name,
                page_name=page_name,
                display_name=display_name,
            )
        )
    return selections


def get_layout_map_item_selections(layout_name: str) -> list[MapItemSelection]:
    """指定レイアウト名の地図アイテム選択情報一覧を返す。

    概要:
        レイアウト名でレイアウトを取得し、選択情報一覧を生成する。

    引数:
        layout_name: 対象レイアウト名。

    戻り値:
        list[MapItemSelection]: 選択情報一覧。対象レイアウトが無い場合は空。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> selections = get_layout_map_item_selections("LayoutA")
    """
    layout = find_layout_by_name(layout_name)
    if layout is None:
        return []
    return build_map_item_selections(layout)


def get_layout_item_selections(layout_name: str) -> list[LayoutItemSelection]:
    """指定レイアウト名の非ページアイテム選択情報一覧を返す。

    概要:
        レイアウト名で対象レイアウトを取得し、
        `LayoutItemSelection` 一覧を生成する。

    引数:
        layout_name: 対象レイアウト名。

    戻り値:
        list[LayoutItemSelection]: 選択情報一覧。対象レイアウトが無い場合は空。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> selections = get_layout_item_selections("LayoutA")
    """
    layout = find_layout_by_name(layout_name)
    if layout is None:
        return []
    return build_layout_item_selections(layout)


def find_map_item_by_selection(layout: object, selection: MapItemSelection) -> QgsLayoutItemMap | None:
    """選択情報からレイアウト内地図アイテムを解決する。

    概要:
        `map_item_id` と同一ID内出現順を使って対象地図アイテムを特定する。

    引数:
        layout: 対象レイアウト。
        selection: 解決対象の選択情報。

    戻り値:
        QgsLayoutItemMap | None: 一致地図アイテム。見つからない場合はNone。

    例外:
        RuntimeError: 地図アイテム取得に失敗した場合。

    使用例:
        >>> item = find_map_item_by_selection(layout, selection)
    """
    matched_count = 0
    for item in get_map_items(layout):
        map_item_id = item.id() or ""
        if map_item_id != selection.map_item_id:
            continue
        matched_count += 1
        if matched_count == selection.occurrence_index:
            return item
    return None


def find_layout_item_by_uuid(layout: object, item_uuid: str) -> QgsLayoutItem | None:
    """UUIDでレイアウトアイテムを解決する。

    概要:
        非ページレイアウトアイテム一覧を走査し、
        UUIDが一致するアイテムを返す。

    引数:
        layout: 対象レイアウト。
        item_uuid: 検索対象UUID。

    戻り値:
        QgsLayoutItem | None: 一致アイテム。見つからない場合はNone。

    例外:
        RuntimeError: レイアウトアイテム取得に失敗した場合。

    使用例:
        >>> item = find_layout_item_by_uuid(layout, "uuid-1")
    """
    for item in get_layout_items(layout):
        item_uuid_method = getattr(item, "uuid", None)
        current_uuid = item_uuid_method() if callable(item_uuid_method) else ""
        if current_uuid == item_uuid:
            return item
    return None


def get_item_expression(map_item: QgsLayoutItemMap) -> str:
    """地図アイテムのexpressionを取得する。

    概要:
        `dataDefinedMapLayers` の式文字列を返す。未設定時は空文字を返す。

    引数:
        map_item: 対象地図アイテム。

    戻り値:
        str: expression文字列。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> expr = get_item_expression(map_item)
    """
    try:
        prop = map_item.dataDefinedProperties().property(QgsLayoutObject.DataDefinedProperty.MapLayers)
        if not prop:
            return ""
        return prop.expressionString() or ""
    except Exception as exc:
        raise RuntimeError(f"expression取得に失敗しました: {exc}") from exc


def get_map_item_layer_display_state(map_item: QgsLayoutItemMap) -> tuple[str, str]:
    """地図アイテムの表示レイヤ設定モードを返す。

    概要:
        data-defined expression とレイヤ固定設定を判定し、
        UI表示用のモード名と必要に応じたexpressionを返す。

    引数:
        map_item: 対象地図アイテム。

    戻り値:
        tuple[str, str]:
            `(layer_display_mode, layer_display_expression)`。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> mode, expression = get_map_item_layer_display_state(map_item)
    """
    try:
        expression = get_item_expression(map_item)
        if expression:
            return (LAYER_DISPLAY_MODE_EXPRESSION, expression)

        keep_layer_set_method = getattr(map_item, "keepLayerSet", None)
        if callable(keep_layer_set_method) and bool(keep_layer_set_method()):
            return (LAYER_DISPLAY_MODE_FIXED, "")

        return (LAYER_DISPLAY_MODE_DEFAULT, "")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"表示レイヤ設定モードの取得に失敗しました: {exc}") from exc


def get_layout_item_type_name(item: QgsLayoutItem) -> str:
    """レイアウトアイテムの表示用種別名を返す。

    概要:
        Qtメタオブジェクトのクラス名から、日本語の種別表示名を返す。

    引数:
        item: 対象レイアウトアイテム。

    戻り値:
        str: 表示用種別名。

    例外:
        なし。

    使用例:
        >>> type_name = get_layout_item_type_name(item)
    """
    class_name = item.metaObject().className() if item.metaObject() is not None else item.__class__.__name__
    type_map: list[tuple[str, str]] = [
        ("QgsLayoutItemMap", "地図"),
        ("QgsLayoutItemLabel", "ラベル"),
        ("QgsLayoutItemPicture", "画像"),
        ("QgsLayoutItemLegend", "凡例"),
        ("QgsLayoutItemScaleBar", "スケールバー"),
        ("QgsLayoutItemShape", "図形"),
        ("QgsLayoutItemPolyline", "図形"),
        ("QgsLayoutItemPolygon", "図形"),
        ("QgsLayoutItemRect", "図形"),
        ("QgsLayoutItemEllipse", "図形"),
        ("QgsLayoutItemTriangle", "図形"),
        ("QgsLayoutItemHtml", "HTML"),
        ("QgsLayoutItemAttributeTable", "属性テーブル"),
        ("QgsLayoutItemManualTable", "表"),
        ("QgsLayoutItemTextTable", "表"),
        ("QgsLayoutItemFrame", "フレーム"),
    ]
    for prefix, display_name in type_map:
        if class_name.startswith(prefix):
            return display_name
    return class_name.replace("QgsLayoutItem", "") or class_name


def get_layout_item_page_name(item: QgsLayoutItem) -> str:
    """レイアウトアイテムの所属ページ名を返す。

    概要:
        シーン矩形中心点から所属ページを判定し、
        `1ページ目` 形式または `ページ外` を返す。

    引数:
        item: 対象レイアウトアイテム。

    戻り値:
        str: 所属ページ名。

    例外:
        RuntimeError: ページ情報取得に失敗した場合。

    使用例:
        >>> page_name = get_layout_item_page_name(item)
    """
    try:
        layout = item.layout()
        if layout is None:
            return "ページ外"
        page_rects = get_layout_page_rects(layout)
        item_rect = item.sceneBoundingRect()
        page_index = resolve_page_index(item_rect.center(), page_rects)
        if page_index is None:
            return "ページ外"
        return f"{page_index + 1}ページ目"
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"所属ページ判定に失敗しました: {exc}") from exc


def get_layout_page_rects(layout: object) -> list[QRectF]:
    """レイアウトのページ矩形一覧を取得する。

    概要:
        ページコレクションからシーン矩形をページ順で返す。

    引数:
        layout: 対象レイアウト。

    戻り値:
        list[QRectF]: ページ矩形一覧。

    例外:
        RuntimeError: ページ情報取得に失敗した場合。

    使用例:
        >>> rects = get_layout_page_rects(layout)
    """
    try:
        page_collection = layout.pageCollection()
        pages = page_collection.pages()
        rects: list[QRectF] = []
        for page in pages:
            rects.append(page.sceneBoundingRect())
        return rects
    except Exception as exc:
        raise RuntimeError(f"ページ情報取得に失敗しました: {exc}") from exc


def resolve_page_index(center_point: QPointF, page_rects: list[QRectF]) -> int | None:
    """中心点から所属ページ番号を返す。

    概要:
        中心点を含む最初のページ矩形を探索し、
        0始まりのページ番号を返す。

    引数:
        center_point: 判定対象中心点。
        page_rects: ページ矩形一覧。

    戻り値:
        int | None: 所属ページ番号。ページ外はNone。

    例外:
        なし。

    使用例:
        >>> page_index = resolve_page_index(point, rects)
    """
    for page_index, page_rect in enumerate(page_rects):
        if page_rect.contains(center_point):
            return page_index
    return None


def serialize_layout_items_to_xml(items: list[QgsLayoutItem]) -> QDomDocument:
    """レイアウトアイテム群を複製用XMLへ変換する。

    概要:
        `writeXml()` を使って、複数のレイアウトアイテムを
        `QDomDocument` へシリアライズする。

    引数:
        items: シリアライズ対象アイテム一覧。

    戻り値:
        QDomDocument: 複製用XMLドキュメント。

    例外:
        RuntimeError: XML生成に失敗した場合。

    使用例:
        >>> dom = serialize_layout_items_to_xml(items)
    """
    if not items:
        raise RuntimeError("複製対象アイテムがありません")

    try:
        document = QDomDocument("LayoutLaboDuplicateItems")
        root = document.createElement("LayoutLaboDuplicateItems")
        document.appendChild(root)
        context = QgsReadWriteContext()
        for item in items:
            if not item.writeXml(root, document, context):
                item_id = item.id() if callable(getattr(item, "id", None)) else ""
                raise RuntimeError(f"レイアウトアイテムのシリアライズに失敗しました: {item_id or 'item'}")
        return document
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"レイアウトアイテムのシリアライズに失敗しました: {exc}") from exc


def duplicate_layout_items_to_layout(target_layout: object, source_dom: QDomDocument) -> list[QgsLayoutItem]:
    """XML化済みアイテム群を対象レイアウトへ複製追加する。

    概要:
        `QgsPrintLayout.addItemsFromXml()` を使い、
        既存レイアウトへ新規アイテムとして追加する。

    引数:
        target_layout: コピー先レイアウト。
        source_dom: 複製元XMLドキュメント。

    戻り値:
        list[QgsLayoutItem]: 追加されたレイアウトアイテム一覧。

    例外:
        RuntimeError: 複製追加に失敗した場合。

    使用例:
        >>> copied = duplicate_layout_items_to_layout(layout, dom)
    """
    try:
        element = source_dom.documentElement()
        if element.isNull():
            raise RuntimeError("複製元XMLが空です")
        copied_items = target_layout.addItemsFromXml(element, source_dom, QgsReadWriteContext())
        if copied_items is None:
            raise RuntimeError("レイアウトアイテムの複製追加に失敗しました")
        return [item for item in copied_items if isinstance(item, QgsLayoutItem)]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"レイアウトアイテムの複製追加に失敗しました: {exc}") from exc


def set_item_extent(map_item: QgsLayoutItemMap, rectangle: QgsRectangle) -> None:
    """地図アイテムへExtentを設定する。

    概要:
        `QgsRectangle` を地図アイテムに反映する。

    引数:
        map_item: 対象地図アイテム。
        rectangle: 設定するExtent。

    戻り値:
        なし。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> set_item_extent(map_item, rect)
    """
    try:
        map_item.setExtent(rectangle)
    except Exception as exc:
        raise RuntimeError(f"Extent設定に失敗しました: {exc}") from exc


def set_item_expression(map_item: QgsLayoutItemMap, expression: str) -> None:
    """地図アイテムへexpressionを設定する。

    概要:
        `dataDefinedMapLayers.expression` に指定文字列を設定する。

    引数:
        map_item: 対象地図アイテム。
        expression: 設定するexpression文字列。

    戻り値:
        なし。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> set_item_expression(map_item, "'Road'")
    """
    try:
        prop = QgsProperty.fromExpression(expression)
        map_item.dataDefinedProperties().setProperty(QgsLayoutObject.DataDefinedProperty.MapLayers, prop)
    except Exception as exc:
        raise RuntimeError(f"expression設定に失敗しました: {exc}") from exc


def find_layout_by_name(layout_name: str) -> object | None:
    """レイアウト名でレイアウトを取得する。

    概要:
        プロジェクトレイアウトマネージャから完全一致で検索する。

    引数:
        layout_name: 検索対象レイアウト名。

    戻り値:
        QgsPrintLayout | None: 一致レイアウト。

    例外:
        RuntimeError: QGIS API呼び出しに失敗した場合。

    使用例:
        >>> layout = find_layout_by_name("LayoutA")
    """
    try:
        manager = QgsProject.instance().layoutManager()
        return manager.layoutByName(layout_name)
    except Exception as exc:
        raise RuntimeError(f"レイアウト検索に失敗しました: {exc}") from exc


def remove_layout_if_exists(layout_name: str) -> bool:
    """同名レイアウトが存在すれば削除する。

    概要:
        再作成前に既存レイアウトを削除する。

    引数:
        layout_name: 削除対象レイアウト名。

    戻り値:
        bool: 削除実行時にTrue、対象なしの場合False。

    例外:
        RuntimeError: 削除に失敗した場合。

    使用例:
        >>> removed = remove_layout_if_exists("LayoutA")
    """
    try:
        manager = QgsProject.instance().layoutManager()
        target = manager.layoutByName(layout_name)
        if target is None:
            return False
        if not manager.removeLayout(target):
            raise RuntimeError("レイアウトマネージャが削除を拒否しました")
        return True
    except Exception as exc:
        raise RuntimeError(f"既存レイアウト削除に失敗しました: {exc}") from exc
