import pytest
from sqlmodel import SQLModel, create_engine, Session
from starlette.testclient import TestClient

from app.main import app
from app.deps import get_session
from app.models import User
from app.services.service_auth import get_password_hash

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-password"


@pytest.fixture(name="client")
def client_fixture(tmp_path):
    # 建表
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    # 建一个可登录的测试用户
    with Session(engine) as session:
        session.add(
            User(
                username=TEST_USERNAME,
                hashed_password=get_password_hash(TEST_PASSWORD),
                disabled=False,
            )
        )
        session.commit()

    def test_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_get_session
    test_client = TestClient(app)

    # 登录拿 JWT，之后所有请求自动带 Bearer Token
    login = test_client.post(
        "/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    yield test_client
    app.dependency_overrides.clear()
