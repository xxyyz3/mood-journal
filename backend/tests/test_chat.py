from unittest.mock import MagicMock

from openai import APITimeoutError, APIError, APIConnectionError

from app.routers import chat

def test_chat(monkeypatch,client):
    def fake_ask(message):
        return f"fake reply for"

    monkeypatch.setattr(chat, "ask_deepseek_messages", fake_ask)
    response = client.post("/chat", json={"message": "hi", "session_id": "test-session"})
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "fake reply for"


def test_chat_history(monkeypatch,client):
    monkeypatch.setattr(chat,"ask_deepseek_messages",lambda p:"fake reply")

    client.post("/chat", json={"message": "hi", "session_id": "test-session"})
    response = client.get("/chat/history?session_id=test-session")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "hi"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "fake reply"


def test_timeout(monkeypatch,client):
    def fake_timeout(prompt):
        raise APITimeoutError("timeout")

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_timeout)
    response = client.post("/chat", json={"message": "hi", "session_id": "test-session"})
    assert response.status_code == 504
    history = client.get("/chat/history?session_id=test-session")

    assert history.status_code == 200
    assert history.json() == []

def test_chat_include_history(monkeypatch,client):
    captures = {}
    def fake_fn(messages):
        captures["messages"] = messages
        return "fake reply"

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_fn)
    client.post("/chat", json={"message": "first", "session_id": "test-session"})
    client.post("/chat", json={"message": "second", "session_id": "test-session"})
    msgs = captures["messages"]
    assert len(msgs) == 4
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "first"
    assert msgs[2]["role"] == "assistant"
    assert msgs[3]["role"] == "user"
    assert msgs[3]["content"] == "second"


def test_chat_uses_recent_history(monkeypatch, client):
    captures = {}
    def fake_fn(messages):
        captures["messages"] = messages
        return "fake reply"

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_fn)

    for i in range(15):
        client.post("/chat", json={"message": f"hi_{i}", "session_id": "test-session"})

    msgs = captures["messages"]
    assert len(msgs)<=12
    contents = [m["content"] for m in msgs]
    assert "hi_0" not in contents


def test_chat_stream(monkeypatch,client):
    def fake_fn(messages):
        for i in "fake reply":
            yield  i
    monkeypatch.setattr(chat,"ask_deepseek_messages_stream",fake_fn)

    response = client.post("/chat/stream", json={"message": "hi", "session_id": "test-session"})
    assert response.status_code == 200
    data = "".join(response.iter_text())
    assert data == 'fake reply'

    history = client.get("/chat/history?session_id=test-session")
    assert history.status_code == 200
    data = history.json()
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "fake reply"


def test_chat_stream_timeout(monkeypatch,client):
    def fake_fn(messages):
        raise APITimeoutError("timeout")
        yield
    monkeypatch.setattr(chat,"ask_deepseek_messages_stream",fake_fn)

    response = client.post("/chat/stream", json={"message": "hi", "session_id": "test-session"})
    content = "".join(response.iter_text())
    assert "API响应超时" in content

    history = client.get("/chat/history?session_id=test-session")
    assert history.status_code == 200
    data = history.json()
    assert data == []

def test_chat_stream_api_error(monkeypatch,client):
    def fake_fn(messages):
        raise APIConnectionError(request=MagicMock())
        yield

    monkeypatch.setattr(chat,"ask_deepseek_messages_stream",fake_fn)

    response = client.post("/chat/stream", json={"message": "hi", "session_id": "test-session"})
    content = "".join(response.iter_text())
    assert "API错误" in content

    history = client.get("/chat/history?session_id=test-session")
    assert history.status_code == 200
    data = history.json()
    assert data == []


def test_chat_sessions_isolated(monkeypatch,client):
    def fake_fn(messages):
        return f"reply to {messages[-1]['content']}"

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_fn)

    client.post("/chat", json={"message": "我是a", "session_id": "a"})
    client.post("/chat", json={"message": "我是b", "session_id": "b"})

    history_a = client.get("/chat/history?session_id=a")
    history_b = client.get("/chat/history?session_id=b")
    assert history_a.status_code == 200
    assert history_b.status_code == 200

    data_a = history_a.json()
    data_b = history_b.json()
    assert len(data_a) == 2
    assert len(data_b) == 2
    assert data_a[0]["content"] == "我是a"
    assert data_b[0]["content"] == "我是b"












