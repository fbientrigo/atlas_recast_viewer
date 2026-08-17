"""Restore the documented strong-bm1 neutralino width in an MG5 LHE header.

MG5 3.5.3 preserves the four RPV decay channels but serializes the tiny width
as zero. This narrowly checked transform changes only that DECAY header and
writes deterministic gzip output. It is part of the local-sample provenance.
"""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

OLD = "DECAY 1000022 0.000000e+00 #"
NEW = "DECAY 1000022 6.582120e-14 # reconstructed strong-bm1: 0.01 ns"


def fix_width(source: Path, output: Path) -> None:
    with gzip.open(source, "rt", encoding="utf-8") as stream:
        text = stream.read()
    if text.count(OLD) != 1:
        raise ValueError(f"expected exactly one {OLD!r}, found {text.count(OLD)}")
    updated = text.replace(OLD, NEW)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(updated.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    fix_width(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
