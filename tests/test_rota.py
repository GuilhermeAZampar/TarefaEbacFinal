import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_rota():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}
