from collections.abc import Callable
from pathlib import Path

from scriber_context import LocalContext, archive_files, ingest_all


def test_archive_reports_each_file_and_keeps_going(
    ctx: LocalContext, tmp_path: Path, write_pdf: Callable[[str, list[list[str]], list[list[str]] | None], Path]
) -> None:
    archive = tmp_path / "archive"
    (archive / "drawings").mkdir(parents=True)
    write_pdf("spec.pdf", [["Plate 120 x 80 x 5 mm"]], None).rename(archive / "drawings" / "spec.pdf")
    (archive / "notes.md").write_text("Hole diameter 6.6 mm", encoding="utf-8")
    (archive / "broken.pdf").write_bytes(b"not a pdf")
    (archive / "photo.heic").write_bytes(b"\x00")
    outcomes = {o.name: o for o in ingest_all(ctx, "p", archive_files([archive]))}
    assert sorted(n for n, o in outcomes.items() if o.status == "parsed") == ["notes.md", "spec.pdf"]
    assert outcomes["notes.md"].kind == "md" and outcomes["notes.md"].facts >= 1
    assert outcomes["broken.pdf"].error and outcomes["photo.heic"].error == "ValueError: unsupported file type: photo.heic"
    assert len(ctx.documents("p")) == 2
