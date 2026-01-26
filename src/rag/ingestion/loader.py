from pathlib import Path
from typing import Iterable, List

SUPPORTED_EXTS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def iter_documents(root: Path) -> List[Path]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")
    files: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(p)
    return files


def validate_file(path: Path) -> Path:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTS:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    return path


def load_batch(paths: Iterable[Path]) -> List[Path]:
    validated: List[Path] = []
    for p in paths:
        path_obj = Path(p)
        try:
            validated.append(validate_file(path_obj))
        except FileNotFoundError as exc:
            # Normalize to ValueError for caller consistency
            raise ValueError(str(exc)) from exc
    return validated
