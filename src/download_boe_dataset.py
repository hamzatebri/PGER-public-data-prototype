from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = (
    ROOT
    / "data"
    / "raw"
    / "boe_procurement"
    / "licitaciones_contrataciones_BOE_2014_2024.csv"
)
DOWNLOAD_URL = (
    "https://zenodo.org/api/records/18712463/files/"
    "licitaciones_contrataciones_BOE_2014_2024.csv/content"
)
EXPECTED_SIZE = 67_396_873
EXPECTED_MD5 = "32629d15d711fdd304e681431a5fe147"
EXPECTED_SHA256 = "d40c6d8318075b48a6aeba376a1b7300f5ac363aaeb8d314534bdd4918b5256e"


def digest(path: Path, algorithm: str) -> str:
    checksum = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def verify(path: Path) -> None:
    if path.stat().st_size != EXPECTED_SIZE:
        raise ValueError(f"Unexpected file size: {path.stat().st_size:,} bytes")
    if digest(path, "md5") != EXPECTED_MD5:
        raise ValueError("The MD5 checksum does not match the Zenodo record.")
    if digest(path, "sha256") != EXPECTED_SHA256:
        raise ValueError("The SHA-256 checksum does not match the source register.")


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        verify(TARGET)
        print(f"Verified existing source: {TARGET}")
        return 0

    temporary = TARGET.with_suffix(".csv.part")
    print("Downloading the frozen BOE public-procurement release from Zenodo...")
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, temporary)
        verify(temporary)
        temporary.replace(TARGET)
    finally:
        if temporary.exists():
            temporary.unlink()

    print(f"Downloaded and verified: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
