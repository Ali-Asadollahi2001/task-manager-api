import json
import os

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from psycopg.rows import dict_row
from pydantic import BaseModel

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://demo:demo@localhost:5432/tasks"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_KEY = "tasks:all"
CACHE_TTL_SECONDS = 30

cache = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

app = FastAPI(title="Task Manager API")


class TaskCreate(BaseModel):
    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    done: bool


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def cache_get():
    try:
        return cache.get(CACHE_KEY)
    except redis.RedisError:
        return None


def cache_set(value: str):
    try:
        cache.setex(CACHE_KEY, CACHE_TTL_SECONDS, value)
    except redis.RedisError:
        pass


def cache_clear():
    try:
        cache.delete(CACHE_KEY)
    except redis.RedisError:
        pass


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="database unavailable")

    redis_status = "ok"
    try:
        cache.ping()
    except redis.RedisError:
        redis_status = "unavailable"

    return {"status": "ok", "database": "ok", "redis": redis_status}


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING *",
            (task.title, task.description),
        ).fetchone()
    cache_clear()
    return row


@app.get("/tasks")
def list_tasks(response: Response):
    cached = cache_get()
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return json.loads(cached)

    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    data = jsonable_encoder(rows)
    cache_set(json.dumps(data))
    response.headers["X-Cache"] = "MISS"
    return data


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    return row


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE tasks SET done = %s WHERE id = %s RETURNING *",
            (update.done, task_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    cache_clear()
    return row


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    cache_clear()
    return Response(status_code=204)