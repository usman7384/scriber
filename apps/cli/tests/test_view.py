import json
import threading
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from partwright_cli.view import Handler, models


def tree(root: Path) -> None:
    for version in ("plate/v1", "plate/v2", "box/v1"):
        (root / version).mkdir(parents=True)
        (root / version / "model.glb").write_bytes(b"glTF" + version.encode())
    (root / "box" / "v2").mkdir()


def test_models_lists_built_versions_newest_first(tmp_path: Path) -> None:
    tree(tmp_path)
    assert list(models(tmp_path)) == ["box/v1", "plate/v2", "plate/v1"]


def test_server_serves_page_index_and_glb(tmp_path: Path) -> None:
    tree(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, tmp_path))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        assert b"GLTFLoader" in urllib.request.urlopen(base + "/").read()
        assert json.loads(urllib.request.urlopen(base + "/models.json").read()) == ["box/v1", "plate/v2", "plate/v1"]
        assert urllib.request.urlopen(base + "/model/plate/v2").read() == b"glTFplate/v2"
    finally:
        server.shutdown()
        server.server_close()
