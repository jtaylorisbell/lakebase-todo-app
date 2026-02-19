"""FastAPI application for Todo App."""

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from todo_app import __version__
from todo_app.api.schemas import (
    CreateTodoRequest,
    CurrentUserResponse,
    HealthResponse,
    TodoListResponse,
    TodoResponse,
    TodoStatsResponse,
    UpdateTodoRequest,
)
from todo_app.api.user import get_current_user
from todo_app.core.models import Priority
from todo_app.db.postgres import get_db

logger = structlog.get_logger()

app = FastAPI(
    title="Lakebase Todo App API",
    description="A beautiful To-Do list powered by Databricks Apps and Lakebase",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db = get_db()
    db_status = "connected" if db.health_check() else "disconnected"
    return HealthResponse(status="ok", version=__version__, database=db_status)


@app.get("/api/me", response_model=CurrentUserResponse)
async def get_me(request: Request) -> CurrentUserResponse:
    user = get_current_user(request)
    return CurrentUserResponse(
        email=user.email,
        name=user.name,
        display_name=user.display_name,
        is_authenticated=user.is_authenticated,
    )


@app.post("/api/todos", response_model=TodoResponse, status_code=201)
async def create_todo(body: CreateTodoRequest, request: Request) -> TodoResponse:
    user = get_current_user(request)
    db = get_db()
    todo = db.create_todo(
        title=body.title,
        description=body.description,
        priority=body.priority.value,
        user_email=user.email,
    )
    return TodoResponse(**todo)


@app.get("/api/todos", response_model=TodoListResponse)
async def list_todos(
    completed: bool | None = None,
    limit: int = 100,
    request: Request = None,
) -> TodoListResponse:
    user = get_current_user(request)
    db = get_db()
    todos = db.list_todos(user_email=user.email, completed=completed, limit=limit)
    return TodoListResponse(
        todos=[TodoResponse(**t) for t in todos],
        total=len(todos),
    )


@app.get("/api/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: str) -> TodoResponse:
    db = get_db()
    todo = db.get_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


@app.put("/api/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: str, body: UpdateTodoRequest) -> TodoResponse:
    db = get_db()
    todo = db.update_todo(
        todo_id=todo_id,
        title=body.title,
        description=body.description,
        completed=body.completed,
        priority=body.priority.value if body.priority else None,
    )
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse(**todo)


@app.patch("/api/todos/{todo_id}/toggle", response_model=TodoResponse)
async def toggle_todo(todo_id: str) -> TodoResponse:
    db = get_db()
    existing = db.get_todo(todo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo = db.update_todo(todo_id=todo_id, completed=not existing["completed"])
    return TodoResponse(**todo)


@app.delete("/api/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: str):
    db = get_db()
    if not db.delete_todo(todo_id):
        raise HTTPException(status_code=404, detail="Todo not found")


@app.get("/api/stats", response_model=TodoStatsResponse)
async def get_stats(request: Request) -> TodoStatsResponse:
    user = get_current_user(request)
    db = get_db()
    stats = db.get_stats(user_email=user.email)
    return TodoStatsResponse(**stats)


# Serve frontend static files
def _find_project_root() -> Path:
    from_main = Path(__file__).parent.parent.parent.parent
    if (from_main / "frontend").exists():
        return from_main
    from_cwd = Path.cwd()
    if (from_cwd / "frontend").exists():
        return from_cwd
    return from_main


PROJECT_ROOT = _find_project_root()

frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
