from enum import StrEnum


class Converter(StrEnum):
    S2T = "s2t"
    S2TW = "s2tw"
    S2TWP = "s2twp"
    T2S = "t2s"
    TW2S = "tw2s"
    TW2SP = "tw2sp"


class OpenCCConverter(StrEnum):
    S2T = "s2t"
    S2TW = "s2tw"
    S2TWP = "s2twp"
    T2S = "t2s"
    TW2S = "tw2s"
    TW2SP = "tw2sp"


FANHUAJI_CONVERTERS: dict[str, str] = {
    Converter.S2T: "Traditional",
    Converter.S2TW: "Traditional",
    Converter.S2TWP: "Taiwan",
    Converter.T2S: "Simplified",
    Converter.TW2S: "Simplified",
    Converter.TW2SP: "China",
}

FILENAME_CONVERTERS: dict[str, str] = {
    Converter.S2T: OpenCCConverter.S2T,
    Converter.S2TW: OpenCCConverter.S2T,
    Converter.S2TWP: OpenCCConverter.S2T,
    Converter.T2S: OpenCCConverter.T2S,
    Converter.TW2S: OpenCCConverter.T2S,
    Converter.TW2SP: OpenCCConverter.T2S,
}
