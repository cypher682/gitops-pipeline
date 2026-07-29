"""
gitops-pipeline sample application.

Deliberately minimal — this app exists to exercise the pipeline
(build, test, scan, sign, deploy, canary) not to be a product.

Endpoints:
  GET  /health        -> liveness/readiness probe target, used by deploy-dev smoke test
  GET  /widgets        -> list widgets (in-memory)
  POST /widgets        -> create a widget
  GET  /widgets/{id}   -> get one widget
  DELETE /widgets/{id} -> delete a widget
  GET  /metrics         -> Prometheus-format counters, used by Argo Rollouts AnalysisTemplate
"""
from __future__ import annotations

import time
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="gitops-pipeline-app", version="0.1.0")

START_TIME = time.time()

# --- naive in-memory metrics, enough for the AnalysisTemplate error-rate query ---
REQUEST_COUNT = 0
ERROR_COUNT = 0


class Widget(BaseModel):
    id: str | None = None
    name: str
    value: int = 0


DB: Dict[str, Widget] = {}


@app.middleware("http")
async def count_requests(request, call_next):
    global REQUEST_COUNT, ERROR_COUNT
    REQUEST_COUNT += 1
    response = await call_next(request)
    if response.status_code >= 500:
        ERROR_COUNT += 1
    return response


@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 2)}


@app.get("/widgets")
def list_widgets():
    return list(DB.values())


@app.post("/widgets", status_code=201)
def create_widget(widget: Widget):
    widget.id = str(uuid.uuid4())
    DB[widget.id] = widget
    return widget


@app.get("/widgets/{widget_id}")
def get_widget(widget_id: str):
    if widget_id not in DB:
        raise HTTPException(status_code=404, detail="widget not found")
    return DB[widget_id]


@app.delete("/widgets/{widget_id}", status_code=204)
def delete_widget(widget_id: str):
    if widget_id not in DB:
        raise HTTPException(status_code=404, detail="widget not found")
    del DB[widget_id]


@app.get("/metrics")
def metrics():
    """
    Minimal Prometheus text-format exposition.
    Scraped by the D1 observability-platform Prometheus instance.
    Argo Rollouts AnalysisTemplate queries the derived error-rate metric.
    """
    error_rate = (ERROR_COUNT / REQUEST_COUNT) if REQUEST_COUNT else 0.0
    body = (
        f"# HELP app_requests_total Total HTTP requests\n"
        f"# TYPE app_requests_total counter\n"
        f"app_requests_total {REQUEST_COUNT}\n"
        f"# HELP app_errors_total Total HTTP 5xx responses\n"
        f"# TYPE app_errors_total counter\n"
        f"app_errors_total {ERROR_COUNT}\n"
        f"# HELP app_error_rate Ratio of 5xx responses to total requests\n"
        f"# TYPE app_error_rate gauge\n"
        f"app_error_rate {error_rate}\n"
    )
    return Response(content=body, media_type="text/plain")
