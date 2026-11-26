# Task Manager API

![CI](https://github.com/Ali-Asadollahi2001/task-manager-api/actions/workflows/ci.yml/badge.svg)

A REST API for managing tasks, built with FastAPI. Data is stored in PostgreSQL, the task list is cached in Redis, and the whole stack runs with Docker Compose.

## Features

- CRUD endpoints for tasks (`/tasks`)
- Plain SQL queries with parameterized statements (no ORM)
- Cache-aside caching of `GET /tasks` in Redis with a 30 second TTL; the cache is cleared on every write
- Graceful degradation: the API keeps working if Redis is down
- `/health` endpoint that checks PostgreSQL and Redis
- Automated tests (pytest) against real PostgreSQL and Redis in CI

## Tech stack

Python, FastAPI, PostgreSQL, Redis, Docker, Docker Compose, pytest, GitHub Actions

## Run with Docker Compose

```bash
docker compose up -d --build
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service and dependency status |
| POST | `/tasks` | Create a task |
| GET | `/tasks` | List tasks (cached) |
| GET | `/tasks/{id}` | Get one task |
| PATCH | `/tasks/{id}` | Mark a task done or not done |
| DELETE | `/tasks/{id}` | Delete a task |

## Run tests

Start the database and Redis, then run pytest (tests clear the `tasks` table):

```bash
docker compose up -d db redis
pip install -r requirements.txt
pytest
```

## CI

On every push and pull request, GitHub Actions starts PostgreSQL and Redis, creates the schema, runs the tests, and checks that the Docker image builds.