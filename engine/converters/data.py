"""Tablo / veri dönüştürücü (pandas).

csv, tsv, xlsx, xls, json, xml, yaml, parquet, ods, html tabloları arası.
"""
from __future__ import annotations

from i18n import Message

CATEGORY = "data"

OUTPUTS = ["csv", "tsv", "xlsx", "json", "xml", "html", "md", "parquet"]


def available():
    try:
        import pandas  # noqa: F401
        return True, ""
    except ImportError:
        return False, Message("{component} is missing. Install {package}.", component="pandas", package="pandas")


def _read(src: str, fmt: str):
    import pandas as pd
    if fmt in ("csv",):
        return pd.read_csv(src)
    if fmt in ("tsv",):
        return pd.read_csv(src, sep="\t")
    if fmt in ("xlsx", "xls", "ods"):
        return pd.read_excel(src)
    if fmt == "json":
        try:
            return pd.read_json(src)
        except ValueError:
            return pd.read_json(src, lines=True)
    if fmt == "xml":
        return pd.read_xml(src)
    if fmt == "parquet":
        return pd.read_parquet(src)
    if fmt in ("yaml",):
        import yaml
        with open(src, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return pd.json_normalize(data)
    if fmt == "html":
        return pd.read_html(src)[0]
    raise ValueError(Message("Unsupported source format · {format}", format=fmt))


def _write(df, dst: str, fmt: str) -> None:
    if fmt == "csv":
        df.to_csv(dst, index=False)
    elif fmt == "tsv":
        df.to_csv(dst, sep="\t", index=False)
    elif fmt == "xlsx":
        df.to_excel(dst, index=False)
    elif fmt == "json":
        df.to_json(dst, orient="records", force_ascii=False, indent=2)
    elif fmt == "xml":
        df.to_xml(dst, index=False)
    elif fmt == "html":
        df.to_html(dst, index=False)
    elif fmt == "md":
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(df.to_markdown(index=False))
    elif fmt == "parquet":
        df.to_parquet(dst, index=False)
    else:
        raise ValueError(Message("Unsupported target format · {format}", format=fmt))


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str) -> None:
    df = _read(src, src_fmt)
    _write(df, dst, dst_fmt)


def preview(src: str, fmt: str) -> str:
    import pandas as pd

    if fmt in {"xlsx", "xls", "ods"}:
        table = pd.read_excel(src, nrows=60)
    else:
        table = _read(src, fmt).head(60)
    return table.iloc[:, :16].to_string(index=False)
