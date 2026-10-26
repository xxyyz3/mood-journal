import json
import sys
from pathlib import Path
from sqlmodel import Session, select
import chromadb
import requests
import os

from app.llm import ask_deepseek, ask_deepseek_messages_stream
from app.models import ChatMessage
from app.siliconflow_llm import get_embedding

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

chunks = json.loads(
    (BASE_DIR / "app" / "data" / "chunks.json").read_text(encoding="utf-8")
)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="character_knowledge_base")

def extract_title(passage:str):
    first_title = passage.split("\n",1)[0].strip()
    return first_title

if collection.count() == 0:
    print("首次启动，正在生成文档向量并存入 ChromaDB...")
    chunk_embeddings = [get_embedding(c) for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas =  [{"title": extract_title(c)} for c in chunks]

    collection.add(
        documents=chunks,
        embeddings=chunk_embeddings,
        metadatas=metadatas,
        ids=ids
    )
    print("入库完毕！")
else:
    print(f"已有 {collection.count()} 条数据，无需重新生成。")

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


def search(question: str, top_k: int = 5) -> list[dict]:
    q_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[q_embedding],
        n_results=top_k
    )

    matched = []

    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"])):
            content = results["documents"][0][i]
            title = results["metadatas"][0][i]["title"]
            matched.append({"title":title,"content":content})

    return matched


def rerank(question, content_list):
    if not content_list:
        return []

    url = "https://api.siliconflow.cn/v1/rerank"
    headers = {
        "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "BAAI/bge-reranker-v2-m3",
        "query": question,
        "documents": content_list
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Rerank 接口报错: {response.text}")
        return [{"content": c, "score": 0} for c in content_list[:3]]

    results = response.json()

    reranked_docs = []
    for item in results["results"]:
        original_index = item["index"]
        score = item["relevance_score"]
        reranked_docs.append({
            "content": content_list[original_index],
            "score": score
        })

    return reranked_docs[:3]


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



def ask_stream(question: str, session:Session, session_id:str):

    new_question = rewrite_question(question, session, session_id)
    matched = search(new_question)
    if not matched:
        yield "文档中没有相关内容"
        return
    content = [c["content"] for c in matched]
    docs = rerank(new_question, content)
    context = "\n---\n".join(item["content"] for item in docs)

    prompt = (
        "你只能根据下面的资料回答问题。"
        "不要扩写，不要联想，不要使用你自己的知识。\n\n"
        f"资料：\n{context}\n\n"
        f"问题：{question}"
    )
    message = [{"role":"user","content":prompt}]

    full_reply = ""
    for chunk in ask_deepseek_messages_stream(message):
        full_reply += chunk
        yield chunk

    user_msg = ChatMessage(role="user", content=question, session_id=session_id)
    ai_msg = ChatMessage(role="assistant", content=full_reply, session_id=session_id)
    session.add(user_msg)
    session.add(ai_msg)
    session.commit()

















