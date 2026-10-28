import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "CodeSentinel"}

def test_create_and_get_cpp_review(client):
    payload = {
        "language": "cpp",
        "code": "int main() { int arr[5]; arr[10] = 5; return 0; }",
        "filename": "test.cpp",
        "checks": ["memory_safety", "correctness"]
    }
    create_res = client.post("/api/reviews", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    assert "review_id" in data
    assert data["status"] == "completed"
    assert len(data["findings"]) > 0

    review_id = data["review_id"]
    get_res = client.get(f"/api/reviews/{review_id}")
    assert get_res.status_code == 200
    assert get_res.json()["review_id"] == review_id

def test_create_python_review(client):
    payload = {
        "language": "python",
        "code": "def add(x, items=[]):\n    eval(x)\n    return items",
        "filename": "main.py",
        "checks": ["correctness", "security"]
    }
    res = client.post("/api/reviews", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["findings"]) >= 2
    cats = [f["category"] for f in data["findings"]]
    assert "correctness" in cats
    assert "security" in cats

def test_create_java_review(client):
    payload = {
        "language": "java",
        "code": "public class A { public void test(String s) { if (s == \"admin\") {} } }",
        "filename": "A.java",
        "checks": ["correctness"]
    }
    res = client.post("/api/reviews", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["findings"]) >= 1
    assert data["findings"][0]["category"] == "correctness"

def test_unsupported_language_rejected(client):
    payload = {
        "language": "ruby",
        "code": "puts 'hello'",
        "filename": "script.rb"
    }
    res = client.post("/api/reviews", json=payload)
    assert res.status_code == 422

def test_get_nonexistent_review(client):
    res = client.get("/api/reviews/rev_does_not_exist_9999")
    assert res.status_code == 404

def test_list_reviews(client):
    res = client.get("/api/reviews")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_github_webhook_authenticated(client):
    payload = {
        "action": "opened",
        "pull_request": {"number": 10},
        "repository": {"full_name": "example/project"},
        "code": "int main() { char b[5]; gets(b); return 0; }"
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    sig = "sha256=" + hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/webhooks/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"

def test_github_webhook_unauthorized(client):
    res = client.post(
        "/api/webhooks/github",
        json={"action": "opened"},
        headers={"X-Hub-Signature-256": "sha256=invalid"}
    )
    assert res.status_code == 401
