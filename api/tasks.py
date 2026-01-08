from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import TaskLog
from services.workflow_service import run_workflow_logic
import json

router = APIRouter(prefix="/api/tasks")

@router.post("/run/{workflow_id}")
async def api_run_workflow(
    workflow_id: str,
    user: str = Form(...),
    params: str = Form(...), # UniApp 传来的 JSON 字符串
    files: list[UploadFile] = File([])
):
    param_dict = json.loads(params)
    return await run_workflow_logic(workflow_id, param_dict, files, user)

# api/tasks.py
# api/tasks.py
@router.get("/status/{prompt_id}")
def get_task_status(prompt_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskLog).filter(TaskLog.prompt_id == prompt_id).first()
    if not task:
        return {"status": "not_found"}

    # 返回状态、进度以及最终的图片相对 URL
    return {
        "status": task.status,
        "progress": task.progress,
        "result_url": task.output_path if task.status == "success" else None
    }