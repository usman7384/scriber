import json
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path


def models(root: Path) -> dict[str, Path]:
    found = {glb.parent.relative_to(root).as_posix(): glb for glb in root.glob("*/v*/model.glb")}
    return dict(sorted(found.items(), key=lambda kv: (kv[0].rsplit("/v", 1)[0], -int(kv[0].rsplit("/v", 1)[1]))))


class Handler(BaseHTTPRequestHandler):
    def __init__(self, root: Path, *args: object) -> None:
        self.root = root
        super().__init__(*args)  # type: ignore[arg-type]

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(files("scriber_cli").joinpath("viewer.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/models.json":
            self._send(json.dumps(list(models(self.root))).encode(), "application/json")
        elif path.startswith("/model/") and (glb := models(self.root).get(path.removeprefix("/model/"))):
            self._send(glb.read_bytes(), "model/gltf-binary")
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve(root: Path, port: int, open_browser: bool) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, root))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"viewing {len(models(root))} model versions from {root} at {url} (Ctrl+C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
