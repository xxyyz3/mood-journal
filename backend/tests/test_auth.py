from starlette.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD, TEST_USERNAME
from datetime import datetime, timedelta, timezone
import jwt
import os

def test_login_success(client):
    response = client.post(
        "/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password(client):
    response = client.post(
        "/auth/token",
        data={"username": TEST_USERNAME, "password": "wrong"},
    )
    assert response.status_code == 401


def test_protected_route_without_token():
    raw_client = TestClient(app)
    response = raw_client.get("/entries")
    assert response.status_code == 401


def test_protected_route_with_invalid_token():
    raw_client = TestClient(app)
    raw_client.headers.update({"Authorization": "Bearer not-a-jwt"})
    response = raw_client.get("/entries")
    assert response.status_code == 401


def test_jwt_from_login_grants_access(client):
    assert client.get("/entries").status_code == 200


# 测试 1：伪造一个已经过期的 Token
def test_expired_token():
    # 签发一个 1 分钟前就过期的 Token
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired_token = jwt.encode({"sub": TEST_USERNAME, "exp": expire}, os.getenv("SECRET_KEY"),
                               algorithm=os.getenv("ALGORITHM"))

    raw_client = TestClient(app)
    raw_client.headers.update({"Authorization": f"Bearer {expired_token}"})
    response = raw_client.get("/entries")
    assert response.status_code == 401  # 过期的 Token 必须被拒绝


# 测试 2：用合法 Token，但去查一个已经被删除的用户
def test_valid_token_but_user_deleted():
    # 签发一个给 "ghost" 用户的合法 Token（但他不在数据库里）
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    ghost_token = jwt.encode({"sub": "ghost_user"}, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))

    raw_client = TestClient(app)
    raw_client.headers.update({"Authorization": f"Bearer {ghost_token}"})
    response = raw_client.get("/entries")
    assert response.status_code == 401  # 查不到用户，必须被拒绝