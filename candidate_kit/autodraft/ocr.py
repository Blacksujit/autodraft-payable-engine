"""OCR wrapper: RapidOCR (ONNX, CPU, multilingual) -> Word objects.

The engine is created lazily and reused across the run. Output words keep
their bounding boxes at OCR-native scale (which is pixel/3 for RapidOCR —
irrelevant as long as we stay ratio-based, which all downstream code does).
"""
from __future__ import annotations

import os
import json
from typing import List, Optional

from autodraft.geom import Box, Word

_ENGINE = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_words(png_path: str) -> List[Word]:
    cache = _cache_path(png_path)
    if cache and cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            return [Word(Box(*w["box"]), w["text"], w["conf"]) for w in data]
        except Exception:
            pass
    engine = get_engine()
    result, _ = engine(png_path)
    words = []
    if result:
        for item in result:
            quad, txt, conf = item[0], item[1], item[2]
            words.append(Word(Box.from_quad(quad), str(txt).strip(), float(conf)))
    out = [w for w in words if w.text]
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps([{"box": [w.box.x0, w.box.y0, w.box.x1, w.box.y1],
                         "text": w.text, "conf": w.conf} for w in out]),
            encoding="utf-8",
        )
    return out


def _cache_path(png_path: str):
    try:
        import hashlib
        from pathlib import Path
        p = Path(png_path)
        st = p.stat()
        key = hashlib.sha1(
            ("%s|%d|%d" % (p.name, st.st_mtime_ns, st.st_size)).encode()
        ).hexdigest()[:16]
        return Path(__file__).resolve().parent.parent / ".work" / "words" / f"{key}.json"
    except Exception:
        return None


def ocr_text(png_path: str) -> str:
    from autodraft.geom import cluster_lines, reading_text

    ws = ocr_words(png_path)
    if not ws:
        return ""
    return reading_text(cluster_lines(ws))