"""
Automated Test Suite for REN-AI Mobile Web Client & FastAPI Endpoints
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
try:
    from fastapi.testclient import TestClient
    from api.server import app
    client = TestClient(app)
    FASTAPI_AVAILABLE = True
except ImportError:
    client = None
    FASTAPI_AVAILABLE = False


def test_health_endpoint():
    if not FASTAPI_AVAILABLE:
        print("  [SKIP] fastapi not installed, skipping test_health_endpoint")
        return
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama" in data
    assert data["name"] == "Ren"
    print("PASS: /api/health")


def test_status_endpoint():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "agent" in data
    assert "stats" in data
    assert "cpu_percent" in data["system"]
    assert "ram_percent" in data["system"]
    print("PASS: /api/status")


def test_skills_endpoint():
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"PASS: /api/skills (found {len(data)} skills)")


def test_conversations_crud():
    # 1. Create conversation
    create_res = client.post("/api/conversations", json={"title": "Test Chat Session"})
    assert create_res.status_code == 200
    created = create_res.json()
    sess_id = created["session_id"]
    assert sess_id is not None
    assert created["title"] == "Test Chat Session"

    # 2. Get conversation
    get_res = client.get(f"/api/conversations/{sess_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["session_id"] == sess_id

    # 3. List conversations
    list_res = client.get("/api/conversations")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["session_id"] == sess_id for s in sessions)

    # 4. Activate conversation
    act_res = client.post(f"/api/conversations/{sess_id}/activate")
    assert act_res.status_code == 200

    # 5. Delete conversation
    del_res = client.delete(f"/api/conversations/{sess_id}")
    assert del_res.status_code == 200

    print("PASS: /api/conversations CRUD")


def test_chat_non_stream():
    res = client.post("/api/chat", json={"message": "who are you", "stream": False})
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "Ren" in data["response"]
    print(f"PASS: /api/chat non-stream -> {data['response']}")


def test_chat_stream_sse():
    with client.stream("POST", "/api/chat", json={"message": "who are you", "stream": True}) as response:
        assert response.status_code == 200
        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)
        assert len(lines) > 0
        assert any("done" in l or "start" in l for l in lines)
        print(f"PASS: /api/chat SSE streaming (received {len(lines)} event chunks)")


def test_chat_stop():
    res = client.post("/api/chat/stop")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "stopped"
    print("PASS: /api/chat/stop")


def test_static_files():
    # 1. Root index
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "REN AI" in root_res.text

    # 2. CSS
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert "--bg-base" in css_res.text

    # 3. JS
    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "sendMessage" in js_res.text

def test_tts_endpoint():
    res = client.post("/api/tts", json={"text": "Hello Sadiq"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 0
    print(f"PASS: /api/tts (generated {len(res.content)} audio bytes)")


def test_error_handling():
    # 1. Empty message error
    empty_res = client.post("/api/chat", json={"message": "", "stream": False})
    assert empty_res.status_code == 400

    # 2. Non-existent conversation
    missing_res = client.get("/api/conversations/non_existent_id_9999")
    assert missing_res.status_code == 404

    # 3. Empty TTS error
    empty_tts = client.post("/api/tts", json={"text": ""})
    assert empty_tts.status_code == 400

    print("PASS: Error handling & validation tests")


def run_all_tests():
    print("\n" + "=" * 50)
    print(" RUNNING MOBILE API TEST SUITE")
    print("=" * 50)
    test_health_endpoint()
    test_status_endpoint()
    test_skills_endpoint()
    test_conversations_crud()
    test_chat_non_stream()
    test_chat_stream_sse()
    test_chat_stop()
    test_tts_endpoint()
    test_error_handling()
    test_static_files()
    print("=" * 50)
    print(" ALL 10 TEST SUITES PASSED (100% HEALTHY)\n")


if __name__ == "__main__":
    run_all_tests()
