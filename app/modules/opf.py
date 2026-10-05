from pathlib import Path

from lxml import etree

from app.enums.converter import Converter

_LANGUAGES = {
    Converter.S2T: "zh-Hant-TW",
    Converter.S2TW: "zh-Hant-TW",
    Converter.S2TWP: "zh-Hant-TW",
    Converter.T2S: "zh-Hans-CN",
    Converter.TW2S: "zh-Hans-CN",
    Converter.TW2SP: "zh-Hans-CN",
}


def update_language(opf_path: str | Path, converter: str) -> None:
    """Update every Dublin Core language element in an OPF document."""
    try:
        language = _LANGUAGES[Converter(converter)]
    except ValueError as error:
        raise ValueError(f"unsupported converter: {converter!r}") from error

    path = Path(opf_path)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    tree = etree.parse(path, parser)
    language_nodes = tree.xpath("//*[local-name()='language']")
    if not language_nodes:
        raise ValueError(f"OPF document has no language element: {path}")
    for node in language_nodes:
        node.text = language
    tree.write(path, encoding="utf-8", xml_declaration=True)
