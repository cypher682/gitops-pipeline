from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_and_get_widget():
    resp = client.post("/widgets", json={"name": "test-widget", "value": 42})
    assert resp.status_code == 201
    widget_id = resp.json()["id"]

    resp = client.get(f"/widgets/{widget_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-widget"


def test_get_missing_widget_404():
    resp = client.get("/widgets/does-not-exist")
    assert resp.status_code == 404


def test_delete_widget():
    resp = client.post("/widgets", json={"name": "to-delete", "value": 1})
    widget_id = resp.json()["id"]

    resp = client.delete(f"/widgets/{widget_id}")
    assert resp.status_code == 204

    resp = client.get(f"/widgets/{widget_id}")
    assert resp.status_code == 404


def test_metrics_endpoint():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "app_requests_total" in resp.text
    assert "app_error_rate" in resp.text
