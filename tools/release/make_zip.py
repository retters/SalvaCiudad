"""The delivery ZIP (section 12 of the specification, phase 128).

    python -I tools/release/make_zip.py [build dir] [output dir]

Takes the release build (build/pros by default) and writes
SalvasProsperia-<version>-windows-x64.zip in the output dir (build/release by
default): the game, its data, README.md, LICENSE, the licenses of the
third-party code (licenses/) and SHA256SUMS.txt with the executable's
SHA-256. No PDB, no tests, no tools. Uses only the standard library; the ZIP
is written to a temporary name and renamed when complete.
"""

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXE = "SalvasProsperia.exe"
# What the data folder must not carry.
SKIP_SUFFIXES = {".pdb", ".ilk", ".tmp"}


def version() -> str:
    text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    m = re.search(r"project\(\s*\w+\s+VERSION\s+([0-9]+\.[0-9]+\.[0-9]+)", text)
    if not m:
        sys.exit("make_zip: no project version in CMakeLists.txt")
    return m.group(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    build = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "pros"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build" / "release"
    bin_dir = build / "bin"
    exe = bin_dir / EXE
    data = bin_dir / "data"
    if not exe.is_file() or not data.is_dir():
        sys.exit(f"make_zip: no {EXE} or data/ in {bin_dir} (build the release first)")
    name = f"SalvasProsperia-{version()}-windows-x64"
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{name}.zip"
    temp = out_dir / f"{name}.zip.tmp"
    if temp.exists():
        temp.unlink()

    files = 0
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        def add(source: Path, arc: str) -> None:
            nonlocal files
            z.write(source, f"{name}/{arc}")
            files += 1

        add(exe, EXE)
        for path in sorted(data.rglob("*")):
            if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES and not path.is_symlink():
                add(path, "data/" + path.relative_to(data).as_posix())
        add(ROOT / "README.md", "README.md")
        add(ROOT / "LICENSE", "LICENSE")
        # The third-party code's licenses (third_party/README.md lists them).
        third = ROOT / "third_party"
        for lib in sorted(p for p in third.iterdir() if p.is_dir()):
            for candidate in ("LICENSE", "LICENSE.txt", "COPYING", "COPYING.txt"):
                lic = lib / candidate
                if lic.is_file():
                    add(lic, f"licenses/{lib.name}-LICENSE.txt")
                    break
            else:
                sys.exit(f"make_zip: no license file in {lib}")
        add(third / "README.md", "licenses/README.md")
        z.writestr(f"{name}/SHA256SUMS.txt", f"{sha256(exe)}  {EXE}\n")
        files += 1
    os.replace(temp, final)
    print(f"{final} ({files} files, {final.stat().st_size / 1e6:.1f} MB)")
    print(f"SHA-256 {EXE}: {sha256(exe)}")
    print(f"SHA-256 zip: {sha256(final)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
