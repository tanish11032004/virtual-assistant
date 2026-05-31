import pytest
from app import create_app
from flask import Flask
from typing import Generator

@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create application for testing."""
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app: Flask) -> Generator[Flask, None, None]:
    """Create test client."""
    with app.test_client() as client:
        yield client
