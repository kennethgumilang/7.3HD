import os
import tempfile
import pytest

os.environ["TASKAPI_DB"] = os.path.join(tempfile.mkdtemp(), "test_tasks.db")

from app.app import app, init_db  # noqa: E402


@pytest.fixture
def client():
    init_db()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "healthy"
    assert body["db_ok"] is True


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"taskapi_requests_total" in resp.data


def test_list_tasks_empty(client):
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_task(client):
    resp = client.post("/tasks", json={"title": "Finish SIT223 HD task"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Finish SIT223 HD task"
    assert body["done"] == 0
    assert "id" in body


def test_create_task_requires_title(client):
    resp = client.post("/tasks", json={})
    assert resp.status_code == 400


def test_get_task_not_found(client):
    resp = client.get("/tasks/9999")
    assert resp.status_code == 404


def test_full_task_lifecycle(client):
    create_resp = client.post("/tasks", json={"title": "Write report"})
    task_id = create_resp.get_json()["id"]

    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["title"] == "Write report"

    update_resp = client.put(f"/tasks/{task_id}", json={"done": True})
    assert update_resp.status_code == 200
    assert update_resp.get_json()["done"] == 1

    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 204

    missing_resp = client.get(f"/tasks/{task_id}")
    assert missing_resp.status_code == 404


def test_update_task_not_found(client):
    resp = client.put("/tasks/9999", json={"title": "nope"})
    assert resp.status_code == 404


def test_delete_task_not_found(client):
    resp = client.delete("/tasks/9999")
    assert resp.status_code == 404
