from app.routers import entries


def test_get_stats(client):
    response = client.get("/entries/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_mood" in data
    assert data["total"] == sum(data["by_mood"].values())


def test_stats_sorted_by_count(client):
    for _ in range(3):
        client.post("/entries", json={"mood": "happy", "content": "x"})
    client.post("/entries", json={"mood": "calm", "content": "y"})

    response = client.get("/entries/stats")
    assert response.status_code == 200
    stats = response.json()
    assert list(stats["by_mood"].keys())[0] == "happy"


def test_create_entry_content_too_long(client):
    response = client.post("/entries", json={"mood": "happy", "content": "x"*201})
    assert response.status_code == 422


def test_create_entry(client):
    response = client.post("/entries",json={"mood":"happy","content":"test content"})

    assert response.status_code == 200
    data = response.json()
    assert data["mood"] == "happy"
    assert data["content"] == "test content"
    assert "id" in data
    assert "created_at" in data


def test_read_entries(client):
    client.post("/entries",json={"mood":"happy","content":"test content"})

    response = client.get("/entries")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(item["mood"] == "happy" and "id" in item and "created_at" in item for item in data)
    response = client.get("/entries?mood=happy")
    assert response.status_code == 200
    data = response.json()
    assert all(item["mood"] == "happy" for item in data)


def test_get_entry_by_id(client):
    create_resp = client.post("/entries",json={"mood": "calm", "content": "reading"})

    assert create_resp.status_code == 200
    new_id = create_resp.json()["id"]
    get_resp = client.get(f"/entries/{new_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["mood"] == "calm"
    assert data["id"] == new_id
    assert data["content"] == "reading"
    missing_resp = client.get("/entries/999999")
    assert missing_resp.status_code == 404


def test_delete_entry(client):
    create_entry = client.post("/entries",json={"mood":"happy","content":"test content"})

    assert create_entry.status_code == 200
    new_id = create_entry.json()["id"]
    delete_resp = client.delete(f"/entries/{new_id}")
    assert delete_resp.status_code == 204
    delete_resp = client.get(f"/entries/{new_id}")
    assert delete_resp.status_code == 404
    missing_resp = client.delete("/entries/999999")
    assert missing_resp.status_code == 404


def test_filter_by_mood(client):
    client.post("/entries", json={"mood": "happy", "content": "test content"})

    list_resp = client.get("/entries?mood=happy")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) > 0
    assert all(item["mood"] == "happy" for item in data)

    stats_resp = client.get("/entries/stats?mood=happy")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total"] > 0
    assert list(stats["by_mood"].keys()) == ["happy"]

def test_entries_summary(monkeypatch,client):
    captures = {}
    def fake_fn(messages):
        captures["messages"] = messages
        return "fake reply"

    monkeypatch.setattr(entries,"ask_deepseek_messages",fake_fn)

    client.post("/entries", json={"mood":"happy","content":"早上好！！！"})
    client.post("/entries", json={"mood":"angry","content":"呜呜呜 ！！！"})
    response = client.get("/entries/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == "fake reply"
    msgs = captures["messages"]
    assert len(msgs) == 2
    assert msgs[1]["role"] == "user"
    assert "happy" in msgs[1]["content"]
    assert "angry" in msgs[1]["content"]


def test_entries_summary_empty(monkeypatch,client):
    def fail_fn(messages):
        raise AssertionError("空数据时不该调用模型")

    monkeypatch.setattr(entries, "ask_deepseek_messages", fail_fn)

    response = client.get("/entries/summary")
    data = response.json()
    assert response.status_code == 200
    assert data["summary"] == "还没有心情记录喵~"




















