import json
import sys
from datetime import datetime
from pathlib import Path


def migrate_sidecar(data: dict, source_path: str) -> dict:
    if data.get("version") == 2:
        return data
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "version": 2,
        "book_name": data.get("book_name", Path(source_path).stem),
        "source_path": source_path,
        "created_at": now,
        "updated_at": now,
        "classification": data.get("classification", {}),
        "pipeline": {},
        "analysis": data.get("analysis", {}),
        "edit_history": [],
        "characters_path": None,
    }


def run(library_dir: str = "library") -> int:
    lib = Path(library_dir)
    sidecars = list(lib.glob("*.metadata.json"))
    migrated = 0
    for path in sidecars:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") == 2:
            continue
        txt_name = path.name.replace(".metadata.json", ".txt")
        source = str(lib / txt_name)
        updated = migrate_sidecar(data, source)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
        migrated += 1
        print(f"Migrated: {path.name}")
    print(f"Done. {migrated}/{len(sidecars)} sidecars migrated.")
    return migrated


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "library")
