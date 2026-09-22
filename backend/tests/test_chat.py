from openai import APITimeoutError

from app.routers import chat

def test_chat(monkeypatch,client):
    def fake_ask(message):
        return f"fake reply for"

    monkeypatch.setattr(chat, "ask_deepseek_messages", fake_ask)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "fake reply for"


def test_chat_history(monkeypatch,client):
    monkeypatch.setattr(chat,"ask_deepseek_messages",lambda p:"fake reply")

    client.post("/chat", json={"message": "hi"})
    response = client.get("/chat/history")
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
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 504
    history = client.get("/chat/history").json()
    assert history == []

def test_chat_include_history(monkeypatch,client):
    captures = {}
    def fake_fn(messages):
        captures["messages"] = messages
        return "fake reply"

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_fn)
    client.post("/chat", json={"message": "first"})
    client.post("/chat", json={"message": "second"})
    msgs = captures["messages"]
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "first"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "second"


def test_chat_uses_recent_history(monkeypatch, client):
    captures = {}
    def fake_fn(messages):
        captures["messages"] = messages
        return "fake reply"

    monkeypatch.setattr(chat,"ask_deepseek_messages",fake_fn)

    for i in range(15):
        client.post("/chat", json={"message": f"hi_{i}"})

    msgs = captures["messages"]
    assert len(msgs)<=11
    contents = [m["content"] for m in msgs]
    assert "hi_0" not in contents
