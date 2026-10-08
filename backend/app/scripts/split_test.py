import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
text = (BASE_DIR / "data" / "character.md").read_text(encoding="utf-8")

parts = re.split(r"\n(?=## )", text)
parts = [p.strip() for p in parts if p.strip() and p.strip().startswith("## ")]

for i, p in enumerate(parts):
    print(f"--- chunk {i} ({len(p)} chars) ---")
    print(p[:400])

out = BASE_DIR / "data" / "chunks.json"
out.write_text(json.dumps(parts, ensure_ascii=False, indent=2), encoding="utf-8")
print("total chunks:", len(parts))