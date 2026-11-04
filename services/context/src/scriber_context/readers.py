from collections.abc import Callable
from pathlib import Path

from scriber_context.models import FileKind
from scriber_context.office import read_docx, read_xlsx
from scriber_context.parsed import Line, Parsed
from scriber_context.pdf import read_pdf
from scriber_context.plain import read_csv, read_text, read_xml, read_yaml
from scriber_ir import ShapeDescriptor

Describe = Callable[[Path], ShapeDescriptor]

KINDS: dict[str, FileKind] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "md",
    ".markdown": "md",
    ".txt": "txt",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".step": "step",
    ".stp": "step",
    ".stl": "stl",
    ".obj": "obj",
}
CAD: set[FileKind] = {"step", "stl", "obj"}
READERS: dict[FileKind, Callable[[Path], Parsed]] = {
    "pdf": read_pdf,
    "docx": read_docx,
    "md": read_text,
    "txt": read_text,
    "csv": read_csv,
    "xlsx": read_xlsx,
    "xml": read_xml,
    "yaml": read_yaml,
    "image": lambda _path: Parsed(),
}


def kind_of(path: Path) -> FileKind:
    kind = KINDS.get(path.suffix.lower())
    if kind is None:
        raise ValueError(f"unsupported file type: {path.name}")
    return kind


def read(path: Path, kind: FileKind, describe: Describe | None) -> Parsed:
    if kind not in CAD:
        return READERS[kind](path)
    if describe is None:
        raise ValueError(f"{path.name}: CAD files need a shape describer")
    shape = describe(path)
    return Parsed(lines=(Line(1, 1, cad_summary(path.stem, kind, shape)),), descriptor=shape)


def cad_summary(name: str, kind: str, shape: ShapeDescriptor) -> str:
    size = " x ".join(f"{v:g}" for v in shape.bbox_sorted)
    holes = ", ".join(f"Ø{d:g}" for d in sorted(set(shape.hole_diameters)))
    return f"{name} {kind.upper()} part: bounding box {size} mm, volume {shape.volume:g} mm3, holes {holes or 'none'}"


def document_text(path: Path, describe: Describe | None = None) -> str:
    return "\n".join(line.text for line in read(path, kind_of(path), describe).lines)
