from html.parser import HTMLParser
from pathlib import Path

from app.config import Settings, _parse_cors_origins

ROOT = Path(__file__).resolve().parents[1]


def test_safe_reference_configuration():
    config = Settings()
    assert config.llm_base_url == "http://127.0.0.1:8001/v1"
    assert config.llm_backend == "llama_cpp"
    assert config.llm_max_tokens == 256
    assert not config.comfy_enabled and not config.comfy_connect
    assert _parse_cors_origins("") == ["http://127.0.0.1:5500", "http://localhost:5500"]
    assert _parse_cors_origins(" https://one.example , https://two.example ") == [
        "https://one.example", "https://two.example"
    ]
    for relative in ["app/config.py", ".env.example", "frontend/config.js", "frontend/config.example.js"]:
        text = (ROOT / relative).read_text(encoding="utf-8-sig")
        assert "trycloudflare.com" not in text


def test_frontend_loads_one_canonical_script_and_existing_assets():
    class Page(HTMLParser):
        scripts = []

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.scripts.append(dict(attrs)["src"])

    page = Page()
    page.feed((ROOT / "frontend/index.html").read_text(encoding="utf-8"))
    assert page.scripts == ["./config.js", "./app.js"]
    for script in page.scripts:
        content = (ROOT / "frontend" / script).read_text(encoding="utf-8-sig")
        assert "\ufffd" not in content
    assert (ROOT / "frontend/faces/neutral.png").is_file()
    assert not (ROOT / "frontend/app.fixed.js").exists()
