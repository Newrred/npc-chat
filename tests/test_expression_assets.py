import json
from pathlib import Path
import re
import struct
import zlib

from app.decision import LLMDecision, normalize_face


def test_canonical_faces_have_decodable_png_fallback():
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    script = (frontend / "app.js").read_text(encoding="utf-8")
    mapping = re.search(r"const FACE_FALLBACK_SLUGS = (\{.*?\});", script, re.S)[1]
    mapping = re.sub(r"(\w+):", r'"\1":', mapping)
    mapping = re.sub(r",\s*}", "}", mapping)
    fallback = json.loads(mapping)
    for face in LLMDecision.model_json_schema()["properties"]["face"]["enum"]:
        candidates = [face, *fallback.get(face, []), "neutral"]
        chosen = next(frontend / "faces" / (name + ".png") for name in candidates
                      if (frontend / "faces" / (name + ".png")).is_file())
        raw = chosen.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        cursor, compressed = 8, b""
        while cursor < len(raw):
            length = struct.unpack(">I", raw[cursor:cursor + 4])[0]
            kind = raw[cursor + 4:cursor + 8]
            content = raw[cursor + 8:cursor + 8 + length]
            crc = struct.unpack(">I", raw[cursor + 8 + length:cursor + 12 + length])[0]
            assert zlib.crc32(kind + content) == crc
            if kind == b"IHDR":
                width, height = struct.unpack(">II", content[:8])
                assert width > 0 and height > 0
            if kind == b"IDAT":
                compressed += content
            cursor += length + 12
        assert zlib.decompress(compressed)
    assert normalize_face("suprised") == "surprised"
    assert normalize_face("shy smile") == "shy_smile"
