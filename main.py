import os

import psycopg
from fastapi import FastAPI, HTTPException, Response
from psycopg.rows import dict_row
from pydantic import BaseModel

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://demo:demo@localhost:5432/tasks"
)

app = FastAPI(title="Task Manager API")


class TaskCreate(BaseModel):
    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    done: bool


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", "database": "ok"}


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING *",
            (task.title, task.description),
        ).fetchone()
    return row


@app.get("/tasks")
def list_tasks():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


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
    return row


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=204)