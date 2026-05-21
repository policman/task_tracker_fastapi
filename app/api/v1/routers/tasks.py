from fastapi import APIRouter
from celery.result import AsyncResult

from app.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        # "task_id": task_id,
        "status": task_result.status,
    }

    if task_result.status == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.status == "PROGRESS":
        response["result"] = task_result.info
    elif task_result.status == "FAILURE":
        response["error"] = str(task_result.result)
    else:
        response["result"] = task_result.result

    return response