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

def extract_title(passage:str):
    first_title = passage.split("\n",1)[0].strip()
    return first_title


def search(question: str, top_k: int = 3) ->list[dict]:

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
    return [
        {"title": extract_title(c), "content": c}
        for _, c in scored[:top_k]
    ]

def ask(question: str) -> dict:
    matched = search(question)
    if not matched:
        return {"answer":"文档中没有相关内容","sources":[]}
    title = [item["title"] for item in matched]
    context = "\n---\n".join(item["content"] for item in matched)
    prompt = (
        "你只能根据下面的资料回答问题。"
        "不要扩写，不要联想，不要使用你自己的知识。\n\n"
        f"资料：\n{context}\n\n"
        f"问题：{question}"
    )
    reply = ask_deepseek(prompt)
    return {"answer": reply,'sources':title}

if __name__ == "__main__":
    import json
    res = ask("今天天气")
    print(json.dumps(res, ensure_ascii=False, indent=2))