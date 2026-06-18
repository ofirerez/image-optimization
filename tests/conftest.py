import pytest
from src.image_optimizer import create_app


@pytest.fixture
def app():
    app = create_app("development")
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
