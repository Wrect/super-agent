"""
FastAPI HTTP server for Omni Browser Agent.
Provides REST API and WebSocket endpoints for task execution and monitoring.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.logger import get_component_logger
from core.config import get_settings
from models.schemas import BrowserTask, TaskResult, TaskStatus, SessionHistory
from agents.crew import get_omni_browser_agent
from engine.debate import get_debate_engine
from engine.memory import get_session_memory
from auth.manager import get_auth_manager


app = FastAPI(
    title="Omni Browser Agent",
    description="Autonomous browser agent with social media integration",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_component_logger("api")


class TaskRequest(BaseModel):
    description: str
    url: Optional[str] = None
    headless: bool = True
    max_steps: int = 20


class DebateRequest(BaseModel):
    prompt_a: str
    prompt_b: str


class TaskManager:
    """Manages task execution and WebSocket connections."""

    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.websockets: Dict[str, list] = {}

    async def submit_task(self, task_request: TaskRequest) -> str:
        """Submit a new task for execution."""
        task_id = str(uuid.uuid4())

        # Create task
        task = BrowserTask(
            id=task_id,
            description=task_request.description,
            url=task_request.url,
            headless=task_request.headless,
            max_steps=task_request.max_steps,
        )

        # Initialize task state
        self.active_tasks[task_id] = {
            "task": task,
            "status": TaskStatus.PENDING,
            "start_time": datetime.utcnow(),
            "output": None,
            "error": None,
        }

        # Start task execution
        asyncio.create_task(self._execute_task(task_id))

        return task_id

    async def _execute_task(self, task_id: str) -> None:
        """Execute a task and stream results via WebSocket."""
        task_state = self.active_tasks.get(task_id)
        if not task_state:
            return

        try:
            # Update status to running
            task_state["status"] = TaskStatus.RUNNING
            await self._broadcast(task_id, {"status": "running"})

            # Get agent and execute
            agent = get_omni_browser_agent()
            result = await agent.execute_task(
                task_state["task"].description, url=task_state["task"].url
            )

            # Update task result
            task_state["status"] = TaskStatus.COMPLETED
            task_state["output"] = result

            await self._broadcast(task_id, {"status": "completed", "output": result})

            # Save to session history
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                start_time=task_state["start_time"],
                end_time=datetime.utcnow(),
                output=result,
            )

            session = get_session_memory()
            history_entry = SessionHistory(
                id=task_id,
                timestamp=datetime.utcnow(),
                task=task_state["task"],
                result=task_result,
            )
            await session.add(history_entry)

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task_state["status"] = TaskStatus.FAILED
            task_state["error"] = str(e)

            await self._broadcast(task_id, {"status": "failed", "error": str(e)})

    async def _broadcast(self, task_id: str, message: Dict[str, Any]) -> None:
        """Broadcast message to all WebSocket clients for a task."""
        if task_id in self.websockets:
            for ws in self.websockets[task_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        if task_id in self.active_tasks:
            task_state = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": task_state["status"].value,
                "start_time": task_state["start_time"].isoformat(),
                "output": task_state["output"],
                "error": task_state["error"],
            }
        return None

    async def connect_websocket(self, task_id: str, websocket: WebSocket) -> None:
        """Connect WebSocket client."""
        await websocket.accept()

        if task_id not in self.websockets:
            self.websockets[task_id] = []
        self.websockets[task_id].append(websocket)

    def disconnect_websocket(self, task_id: str, websocket: WebSocket) -> None:
        """Disconnect WebSocket client."""
        if task_id in self.websockets and websocket in self.websockets[task_id]:
            self.websockets[task_id].remove(websocket)


task_manager = TaskManager()


# API Routes
@app.get("/")
async def root():
    """Serve the dashboard."""
    return FileResponse("ui/dashboard.html")


@app.get("/static/{filename}")
async def static_files(filename: str):
    """Serve static files."""
    static_path = Path("ui") / filename
    if static_path.exists():
        return FileResponse(static_path)
    raise HTTPException(status_code=404, detail="File not found")


@app.post("/task")
async def submit_task(request: TaskRequest) -> Dict[str, Any]:
    """Submit a new browser task."""
    try:
        task_id = await task_manager.submit_task(request)
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """Get task status and results."""
    task_status = task_manager.get_task_status(task_id)

    if task_status:
        return task_status

    raise HTTPException(status_code=404, detail="Task not found")


@app.websocket("/ws/tasks/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for live task updates."""
    await task_manager.connect_websocket(task_id, websocket)

    try:
        # Send current status
        task_status = task_manager.get_task_status(task_id)
        if task_status:
            await websocket.send_json(task_status)

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    finally:
        task_manager.disconnect_websocket(task_id, websocket)


@app.get("/history")
async def get_history(limit: int = 10) -> Dict[str, Any]:
    """Get session history."""
    try:
        session = get_session_memory()
        history = await session.get_recent(limit)
        return {"history": [h.model_dump() for h in history]}
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debate")
async def synthesize_prompts(request: DebateRequest) -> Dict[str, Any]:
    """Synthesize two prompts using the debate engine."""
    try:
        debate_engine = get_debate_engine()
        result = await debate_engine.synthesize(
            prompt_a=request.prompt_a, prompt_b=request.prompt_b
        )

        return result.model_dump()
    except Exception as e:
        logger.error(f"Debate synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/status")
async def get_auth_status() -> Dict[str, Any]:
    """Get authentication status for all platforms."""
    try:
        auth_manager = get_auth_manager()
        status = await auth_manager.get_auth_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get auth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve UI at root
@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard."""
    return FileResponse("ui/dashboard.html")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
