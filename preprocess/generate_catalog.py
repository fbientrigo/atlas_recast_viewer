"""Regenerate public/data/catalog.json from validated datasets on disk.

Discovers H2 mass-control datasets by scanning ``public/data/h2-m*`` for a
built, valid ``manifest.json`` (Step 3A: never hardcode the mass list).
Preserves every non-H2 catalog entry byte-for-byte and appends H2 entries
sorted numerically by mass. Re-running this script after building more H2
masses is idempotent and safe.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

H2_DATASET_ID_RE = re.compile(r"^h2-m(\d+)$")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_h2_entries(data_dir: Path) -> list[dict[str, Any]]:
    found: list[tuple[int, dict[str, Any]]] = []
    for candidate in sorted(data_dir.glob("h2-m*")):
        match = H2_DATASET_ID_RE.match(candidate.name)
        if not match or not (candidate / "manifest.json").is_file():
            continue
        manifest = _load(candidate / "manifest.json")
        mass = manifest["sample"]["mass_GeV"]
        if mass != int(match.group(1)):
            raise ValueError(f"{candidate.name}: manifest mass {mass} does not match dataset_id")
        ctau = manifest["sample"]["ctau_response_mm"]
        entry = {
            "dataset_id": manifest["dataset_id"],
            "labels": {"es": f"H2 · {mass} GeV", "en": f"H2 · {mass} GeV"},
            "description": {
                "es": f"Control de masa H2 Trackless, m_H2={mass} GeV, τ_response={ctau:.3f} mm fijo, H2→b b̄.",
                "en": f"H2 Trackless mass control, m_H2={mass} GeV, fixed τ_response={ctau:.3f} mm, H2→b b̄.",
            },
        }
        found.append((mass, entry))
    found.sort(key=lambda item: item[0])
    return [entry for _, entry in found]


def regenerate(data_dir: Path) -> list[dict[str, Any]]:
    catalog_path = data_dir / "catalog.json"
    existing: list[dict[str, Any]] = _load(catalog_path) if catalog_path.is_file() else []
    non_h2 = [entry for entry in existing if not H2_DATASET_ID_RE.match(entry["dataset_id"])]
    h2_entries = discover_h2_entries(data_dir)
    catalog = non_h2 + h2_entries
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("public/data"))
    args = parser.parse_args()
    catalog = regenerate(args.data_dir)
    print(f"wrote {len(catalog)} catalog entries to {args.data_dir / 'catalog.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
