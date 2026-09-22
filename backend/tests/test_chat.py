from openai import APITimeoutError

from app.routers import chat

def test_chat(monkeypatch,client):
    def fake_ask(prompt:str)->str:
        return f"fake reply for: {prompt}"

    monkeypatch.setattr(chat, "ask_deepseek", fake_ask)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "fake reply for: hi"


def test_chat_history(monkeypatch,client):
    monkeypatch.setattr(chat,"ask_deepseek",lambda p:"fake reply")

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
    monkeypatch.setattr(chat,"ask_deepseek",fake_timeout)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 504
    history = client.get("/chat/history").json()
    assert history == []
