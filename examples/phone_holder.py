import argparse
from pathlib import Path
from typing import Any

import httpx

from scriber_cli.pipe import Http, ok, wait

INNER = "(phone_width + clearance) / 2"
OUTER = f"{INNER} + wall"
TOP = "base + lip_height"


def holder_design(phone_width: float, clearance: float = 0.5, depth: float = 60.0) -> dict[str, Any]:
    given = {"source": "prompt", "quote": f"phone width {phone_width:g} mm"}
    return {
        "title": f"Phone holder for a {phone_width:g} mm phone",
        "params": [
            {"name": "phone_width", "value": phone_width, "unit": "mm", "min": 40, "max": 120, "provenance": given},
            {"name": "clearance", "value": clearance, "unit": "mm", "min": 0, "max": 3, "description": "total side play"},
            {"name": "wall", "value": 4, "unit": "mm"},
            {"name": "base", "value": 5, "unit": "mm"},
            {"name": "lip_height", "value": 15, "unit": "mm"},
            {"name": "depth", "value": depth, "unit": "mm"},
        ],
        "parts": [
            {
                "id": "cradle",
                "name": "Cradle",
                "sketches": [
                    {
                        "id": "profile",
                        "plane": {"ref": "XZ"},
                        "entities": [
                            {
                                "kind": "polygon",
                                "points": [
                                    [f"-({OUTER})", 0],
                                    [OUTER, 0],
                                    [OUTER, TOP],
                                    [INNER, TOP],
                                    [INNER, "base"],
                                    [f"-({INNER})", "base"],
                                    [f"-({INNER})", TOP],
                                    [f"-({OUTER})", TOP],
                                ],
                            }
                        ],
                    }
                ],
                "features": [
                    {
                        "kind": "extrude",
                        "id": "body",
                        "name": "Cradle",
                        "intent": "U channel: inner width is the phone width plus the clearance",
                        "sketch": "profile",
                        "extent": "symmetric",
                        "distance": "depth",
                    }
                ],
            }
        ],
    }


def submit(http: Http, project: str, phone_width: float) -> dict[str, Any]:
    body = {"design": holder_design(phone_width), "prompt": f"phone holder, phone width {phone_width:g} mm"}
    return wait(http, ok(http.post(f"/projects/{project}/designs", json=body)))


def main() -> None:
    p = argparse.ArgumentParser(description="Personalised phone holder from the phone's width")
    p.add_argument("phone_width", type=float, help="mm")
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--token")
    p.add_argument("--project", required=True)
    p.add_argument("--out", type=Path, default=Path("phone_holder.stl"))
    args = p.parse_args()
    headers = {"X-API-Token": args.token} if args.token else {}
    with httpx.Client(base_url=args.api, headers=headers, timeout=30) as http:
        job = submit(http, args.project, args.phone_width)
        if job["status"] != "done":
            raise SystemExit(f"build failed: {job['error']}")
        stl = http.get(f"/models/{job['model_id']}/export", params={"fmt": "stl"}).raise_for_status()
        args.out.write_bytes(stl.content)
    print(f"model {job['model_id']}: {args.out}")


if __name__ == "__main__":
    main()
