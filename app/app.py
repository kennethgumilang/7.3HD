"""
Task Manager API
A small Flask REST API with CRUD endpoints, a health check, and a
Prometheus-compatible /metrics endpoint — deliberately simple, but with
enough real logic (validation, error handling, persistence) to be worth
building, testing, scanning and deploying through a CI/CD pipeline.
"""
import os
import time
import sqlite3
from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

APP_START_TIME = time.time()
DB_PATH = os.environ.get("TASKAPI_DB", "/data/tasks.db")

app = Flask(__name__)

REQUEST_COUNT = Counter(
    "taskapi_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "taskapi_request_latency_seconds", "Request latency", ["endpoint"]
)


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


@app.before_request
def _start_timer():
    request._start_time = time.time()


@app.after_request
def _record_metrics(response):
    if hasattr(request, "_start_time"):
        REQUEST_LATENCY.labels(endpoint=request.path).observe(
            time.time() - request._start_time
        )
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.path, status=response.status_code
    ).inc()
    return response


@app.route("/health", methods=["GET"])
def health():
    """Liveness/readiness probe used by the Deploy, Release and Monitoring stages."""
    try:
        get_db().execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    uptime = round(time.time() - APP_START_TIME, 2)
    status = "healthy" if db_ok else "unhealthy"
    code = 200 if db_ok else 503
    return jsonify(status=status, uptime_seconds=uptime, db_ok=db_ok), code


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/tasks", methods=["GET"])
def list_tasks():
    rows = get_db().execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    cur = get_db().execute("INSERT INTO tasks (title, done) VALUES (?, 0)", (title,))
    get_db().commit()
    return jsonify(id=cur.lastrowid, title=title, done=0), 201


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    row = get_db().execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        return jsonify(error="task not found"), 404
    return jsonify(dict(row))


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    row = get_db().execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify(error="task not found"), 404
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    done = data.get("done")
    if title is not None:
        get_db().execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
    if done is not None:
        get_db().execute(
            "UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, task_id)
        )
    get_db().commit()
    row = get_db().execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return jsonify(dict(row))


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    row = get_db().execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify(error="task not found"), 404
    get_db().execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    get_db().commit()
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
