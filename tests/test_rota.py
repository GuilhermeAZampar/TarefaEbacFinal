from fastapi.testclient import TestClient
from main import app

import pytest

client=TestClient(app)

def test_rota():
    response=client.get("/")
    assert response.status_code==200
    assert response.json()=={"message":"Hello"}