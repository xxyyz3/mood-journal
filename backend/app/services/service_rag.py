import json
import sys
from pathlib import Path
from sqlmodel import Session, select

from app.models import ChatMessage
from app.siliconflow_llm import get_embedding, cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

chunks = json.loads(
    (BASE_DIR / "app" / "data" / "chunks.json").read_text(encoding="utf-8")
)

print("正在生成文档向量...")
chunk_embeddings = [get_embedding(c) for c in chunks]
print("向量生成完毕。")

from app.llm import ask_deepseek

def extract_title(passage:str):
    first_title = passage.split("\n",1)[0].strip()
    return first_title


def get_recent_question(session:Session, session_id:str,limit:int=3):
    recent = session.exec(
        select(ChatMessage.content).
        where(ChatMessage.session_id == session_id,ChatMessage.role == 'user').
        order_by(ChatMessage.created_at.desc()).limit(limit)
    ).all()
    history = list(reversed(recent))
    return [h for h in history]


def rewrite_question(question:str, session:Session, session_id:str):
    history_questions = get_recent_question(session,session_id,limit=5)
    if not history_questions:
        return question
    history_question = " ".join(history_questions)
    prompt = (
        f"你是一个搜索词提取助手。结合历史问题的回答，复写一下用户的问题。"
        f"不要扩写，不要联想，不要使用你自己的知识。\n\n"
        f"例子：用户询问她的住址，根据历史问题和答案，找到了她的名字，问题扩充为:xxx住在哪里"
        f"不要输出问句，不要输出任何疑问词（如哪里、什么、怎么）。用空格隔开。\n"
        f"历史问题：{history_question}\n"
        f"当前问题：{question}\n"
    )
    new_question = ask_deepseek(prompt)
    return new_question


def search(question: str, top_k: int = 3) -> list[dict]:
    q_embedding = get_embedding(question)
    scored = []
    for i, c in enumerate(chunks):
        score = cosine_similarity(q_embedding, chunk_embeddings[i])
        if score<=0.4:
            continue
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    for s, c in scored[:top_k]:
        print(f"score: {s:.4f}, title: {c.split('\n')[0]}")

    return [
        {"title": extract_title(c), "content": c}
        for _, c in scored[:top_k]
    ]


def ask(question: str, session:Session, session_id:str) -> dict:

    new_question = rewrite_question(question, session, session_id)
    matched = search(new_question)

    if not matched:
        user_msg = ChatMessage(role="user", content=question, session_id=session_id)
        ai_msg = ChatMessage(role="assistant", content="文档中没有相关内容", session_id=session_id)
        session.add(user_msg)
        session.add(ai_msg)
        session.commit()
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
    user_msg = ChatMessage(role="user",content=question,session_id=session_id)
    ai_msg = ChatMessage(role="assistant",content=reply,session_id=session_id)
    session.add(user_msg)
    session.add(ai_msg)
    session.commit()

    return {"answer": reply,'sources':title}
