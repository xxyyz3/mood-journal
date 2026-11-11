"""鉴权越权修复的回归测试。

覆盖：
1. 聊天历史按 user_id 隔离；
2. RAG 历史问题按 user_id 隔离；
3. /chat 与 /ask 的用户身份以 JWT 为准，忽略请求体里的 user_id。
"""

from sqlmodel import SQLModel, Session, create_engine

from app.models import ChatMessage
from app.services.service_chat import get_history, messages_histories
from app.services.service_rag import get_recent_question


def _make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/security.db")
    SQLModel.metadata.create_all(engine)
    return engine


def test_chat_history_scoped_by_user(tmp_path):
    engine = _make_session(tmp_path)

    with Session(engine) as session:
        session.add_all(
            [
                ChatMessage(role="user", content="alice 的消息", session_id="s1", user_id="alice"),
                ChatMessage(role="assistant", content="alice 的回复", session_id="s1", user_id="alice"),
                ChatMessage(role="user", content="bob 的消息", session_id="s1", user_id="bob"),
            ]
        )
        session.commit()

        alice_history = messages_histories(session, "s1", "alice")
        assert [m.content for m in alice_history] == ["alice 的消息", "alice 的回复"]

        assert [m.content for m in get_history(session, "s1", "alice")] == [
            "alice 的消息",
            "alice 的回复",
        ]
        assert [m.content for m in get_history(session, "s1", "bob")] == ["bob 的消息"]


def test_rag_recent_questions_scoped_by_user(tmp_path):
    engine = _make_session(tmp_path)

    with Session(engine) as session:
        session.add_all(
            [
                ChatMessage(role="user", content="alice 的问题", session_id="s1", user_id="alice"),
                ChatMessage(role="user", content="bob 的问题", session_id="s1", user_id="bob"),
            ]
        )
        session.commit()

        assert get_recent_question(session, "s1", user_id="alice") == ["alice 的问题"]
        assert get_recent_question(session, "s1", user_id="bob") == ["bob 的问题"]


def test_chat_uses_jwt_user_not_body(monkeypatch, client):
    from app.routers import chat as chat_router

    captured = {}

    def fake_handle_message(session, user_message, session_id, user_id=None):
        captured["user_id"] = user_id
        return "ok"

    monkeypatch.setattr(chat_router, "handle_message", fake_handle_message)

    response = client.post(
        "/chat",
        json={"message": "hi", "session_id": "s1", "user_id": "victim"},
    )
    assert response.status_code == 200
    assert captured["user_id"] == "tester"


def test_ask_uses_jwt_user_not_body(monkeypatch, client):
    from app.routers import rag as rag_router

    captured = {}

    def fake_ask(question, session, session_id, user_id):
        captured["user_id"] = user_id
        return {"answer": "ok", "sources": []}

    monkeypatch.setattr(rag_router, "ask", fake_ask)

    response = client.post(
        "/ask",
        json={"question": "她住在哪", "session_id": "s1", "user_id": "victim"},
    )
    assert response.status_code == 200
    assert captured["user_id"] == "tester"


def test_ask_user_id_is_optional(monkeypatch, client):
    """旧客户端即使不传 user_id，也应正常工作（服务端从 JWT 取）。"""
    from app.routers import rag as rag_router

    monkeypatch.setattr(
        rag_router,
        "ask",
        lambda question, session, session_id, user_id: {
            "answer": "ok",
            "sources": [],
        },
    )

    response = client.post(
        "/ask",
        json={"question": "她住在哪", "session_id": "s1"},
    )
    assert response.status_code == 200
