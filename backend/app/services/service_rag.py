import json
import sys
from pathlib import Path

from fastapi import BackgroundTasks
from sqlmodel import Session, select
import chromadb
import requests
import os

from app.llm import ask_deepseek, ask_deepseek_messages_stream
from app.models import ChatMessage, UserMemory
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
    return history


def get_user_memory(session:Session, user_id:str):
    memories = session.exec(select(UserMemory).where(UserMemory.user_id == user_id)).all()
    if not memories:
        return "无"
    return "\n".join([m.fact_content for m in memories])



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
        for i in range(len(results["documents"][0])):
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

def extract_memory(session:Session, user_id, chat_history):
    prompt = (
        "请从下面的对话中提取用户的长期个人信息（如姓名、职业、喜好）。"
        "如果没有提取到任何信息，请严格只输出一个字：无。不要输出其他任何解释。\n\n"
        f"对话内容：\n{chat_history}"
    )
    reply = ask_deepseek(prompt)
    if reply and "无" not in reply:
        content = UserMemory(user_id=user_id, fact_content=reply)
        session.add(content)
        session.commit()
        print(f"提取成功")
        return content
    else:
        print("提取失败")
        return None


def ask(question: str, session:Session, session_id:str, user_id:str) -> dict:

    new_question = rewrite_question(question, session, session_id)
    matched = search(new_question)

    title = [item["title"] for item in matched]
    context = "\n---\n".join(item["content"] for item in matched)

    chat_history = get_recent_question(session, session_id)
    chat_history_str = "\n".join([f"用户: {h}" for h in chat_history])

    if not matched:
        extract_memory(session,user_id,chat_history_str+f"\nuser:{question}")
        return {"answer":"文档中没有相关内容","sources":[]}

    memory_context = get_user_memory(session,user_id)

    prompt = (
        f"已知用户的背景信息：{memory_context}"
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

    extract_memory(session, user_id, chat_history_str + f"\nuser:{question}" + f"\nassistant:{reply}")
    return {"answer": reply,'sources':title}


def ask_stream(question: str, session:Session, session_id:str, user_id:str, background_task:BackgroundTasks):

    new_question = rewrite_question(question, session, session_id)
    matched = search(new_question)

    #获取用户的历史问题
    chat_history = get_recent_question(session,session_id,5)
    chat_history_str = "\n".join([f"user:{h}" for h in chat_history])

    if not matched:
        extract_memory(session,user_id,chat_history_str+f"\nuser:{question}")
        yield "文档中没有相关内容"
        return

    memory_context = get_user_memory(session,user_id)

    content = [c["content"] for c in matched]
    docs = rerank(new_question, content)
    context = "\n---\n".join(item["content"] for item in docs)

    prompt = (
        f"已知用户的背景信息：{memory_context}"
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

    def process_after_chat():
        user_msg = ChatMessage(role="user", content=question, session_id=session_id)
        ai_msg = ChatMessage(role="assistant", content=full_reply, session_id=session_id)
        session.add(user_msg)
        session.add(ai_msg)
        session.commit()
        extract_memory(session, user_id, chat_history_str + f"\nuser:{question}" + f"\nassistant:{full_reply}")

    background_task.add_task(process_after_chat)

















