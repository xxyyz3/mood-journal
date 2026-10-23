import json

from app.scripts.split_test import BASE_DIR

chunks = json.loads(
    (BASE_DIR / "app" / "data" / "chunks.json").read_text(encoding="utf-8")
)

metadatas = [{"title": c.split("\n")[0]} for c in chunks]