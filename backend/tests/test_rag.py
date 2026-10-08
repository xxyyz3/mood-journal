from openai import APIConnectionError

from app.services import service_rag


def test_ask_answer(monkeypatch, client):
    def fake_fn(prompt:str):
        return "这是该模型的内容"
    monkeypatch.setattr(service_rag, "ask_deepseek", fake_fn)
    response = client.post("/ask", json={"question":"介绍一下她"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "这是该模型的内容"


def test_ask_no__answer(monkeypatch, client):
    def fake_fn(prompt:str):
        raise APIConnectionError("不调用该模型")
    monkeypatch.setattr(service_rag, "ask_deepseek", fake_fn)
    response = client.post("/ask", json={"question":"今天天气"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "文档中没有相关内容"
