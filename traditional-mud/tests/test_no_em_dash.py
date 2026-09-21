from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = chr(0x2014)
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".lua", ".xml", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".html", ".htm", ".css", ".js",
    ".ts", ".tsx", ".jsx", ".sh", ".bat", ".ps1", ".sql",
}


def _find_forbidden_in_text_files():
    matches = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if FORBIDDEN in text:
            matches.append(str(path.relative_to(ROOT)))
    return matches


def _find_forbidden_in_mudlet_packages():
    matches = []
    for package in ROOT.rglob("*.mpackage"):
        try:
            with zipfile.ZipFile(package) as archive:
                for name in archive.namelist():
                    if Path(name).suffix.lower() not in TEXT_SUFFIXES:
                        continue
                    try:
                        text = archive.read(name).decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    if FORBIDDEN in text:
                        matches.append(f"{package.relative_to(ROOT)}::{name}")
        except zipfile.BadZipFile:
            continue
    return matches


def test_game_text_contains_no_em_dash():
    matches = _find_forbidden_in_text_files()
    matches.extend(_find_forbidden_in_mudlet_packages())
    assert not matches, "Forbidden U+2014 found in: " + ", ".join(sorted(matches))
