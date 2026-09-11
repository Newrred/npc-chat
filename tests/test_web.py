import pytest


@pytest.mark.parametrize("path,kind", [
    ("/", "text/html"), ("/index.html", "text/html"), ("/app.js", "javascript"),
    ("/config.js", "javascript"), ("/styles.css", "text/css"), ("/faces/neutral.png", "image/png"),
    ("/characters/cartethyia/faces/neutral.png", "image/png"),
])
def test_public_files(backend, path, kind):
    response = backend[0].get(path)
    assert response.status_code == 200
    assert kind in response.headers["content-type"]


@pytest.mark.parametrize("path", [
    "/api/unknown", "/missing.png", "/.env", "/app/config.py", "/data/chat.sqlite3",
    "/.git/config", "/faces/%2e%2e%2f.env", "/faces/%2e%2e%5c.env", "/faces/.env",
    "/characters/cartethyia/faces/%2e%2e%2fneutral.png", "/characters/%2e%2e/faces/neutral.png",
    "/%2e%2e/.env", "/logs/app.log", "/models/example.gguf",
])
def test_private_and_unknown_paths_stay_errors(backend, path):
    response = backend[0].get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_web_does_not_shadow_api_methods(backend):
    assert backend[0].get("/api/chat").status_code == 405
    assert backend[0].post("/api/chat", json={"message": ""}).status_code == 422
    assert backend[0].head("/").status_code == 200
