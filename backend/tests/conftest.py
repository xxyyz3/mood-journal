import pytest
from sqlmodel import SQLModel, create_engine, Session
from starlette.testclient import TestClient

from app.main import app
from app import models
from app.deps import get_session

@pytest.fixture(name = "client")
def client_fixture(tmp_path):
    #建表
    engine = create_engine(f"sqlite:///{tmp_path}/test.db",connect_args={"check_same_thread":False})
    SQLModel.metadata.create_all(engine)
    def test_get_session():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_session] = test_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


