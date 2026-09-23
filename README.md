# Task Manager API

A small Flask REST API (SQLite-backed CRUD for tasks) built to demonstrate a
full DevOps pipeline for SIT223/SIT753. See **SETUP_GUIDE.md** for how to
stand up Jenkins and run the pipeline end to end.

## Endpoints
- `GET /health` — liveness/readiness probe (used by Deploy/Release/Monitoring)
- `GET /metrics` — Prometheus-format metrics
- `GET /tasks`, `POST /tasks`
- `GET|PUT|DELETE /tasks/<id>`

## Run locally without Docker
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
python app/app.py
```

## Run with Docker
```bash
docker build -t taskapi .
docker run -p 5000:5000 taskapi
```

## Run tests
```bash
pip install -r requirements-dev.txt
pytest tests/
```

## Pipeline
See `Jenkinsfile` for the 7-stage pipeline (Build, Test, Code Quality,
Security, Deploy, Release, Monitoring) and `SETUP_GUIDE.md` for setup.
