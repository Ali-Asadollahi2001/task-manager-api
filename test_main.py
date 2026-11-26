import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_state():
    with main.get_conn() as conn:
        conn.execute("TRUNCATE tasks RESTART IDENTITY")
    main.cache_clear()
    yield


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_create_and_list_tasks():
    created = client.post("/tasks", json={"title": "Buy bread"})
    assert created.status_code == 201
    assert created.json()["title"] == "Buy bread"
    assert created.json()["done"] is False

    listed = client.get("/tasks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_list_is_cached():
    client.post("/tasks", json={"title": "Task"})
    first = client.get("/tasks")
    second = client.get("/tasks")
    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"


def test_cache_cleared_after_create():
    client.get("/tasks")
    client.post("/tasks", json={"title": "New"})
    response = client.get("/tasks")
    assert response.headers["x-cache"] == "MISS"
    assert len(response.json()) == 1


def test_get_missing_task_returns_404():
    assert client.get("/tasks/999").status_code == 404


def test_update_task():
    task_id = client.post("/tasks", json={"title": "Task"}).json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"done": True})
    assert response.status_code == 200
    assert response.json()["done"] is True


def test_delete_task():
    task_id = client.post("/tasks", json={"title": "Task"}).json()["id"]
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404