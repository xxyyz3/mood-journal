import json
import jieba
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

chunks = json.loads(
    (BASE_DIR / "app" / "data" / "chunks.json").read_text(encoding="utf-8")
)

from app.llm import ask_deepseek

def search(question: str, top_k: int = 3) -> list[tuple[int, str]]:

    stop_chars = set("怎么 办 如何 的 是 吗 呢 了 算 一下".split())
    query_chars = {w for w in jieba.cut(question) if len(w) > 1} - stop_chars
    if not query_chars:
        return []
    scored = []
    for c in chunks:
        hit = sum(1 for ch in query_chars if ch in c)
        ratio = hit / len(query_chars) if query_chars else 0
        if ratio>=0.6:
            scored.append((hit, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [r for r in scored]
    return results[:top_k]

def ask(question: str) -> str:
    matched = ""
    for score,c in search(question):
        matched = matched+c

    if not matched:
        return "文档中没有相关内容"
    question+=matched
    reply = ask_deepseek(question)
    return reply
