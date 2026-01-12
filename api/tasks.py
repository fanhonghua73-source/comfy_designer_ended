from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import TaskLog
from services.workflow_service import run_workflow_logic
import json
import os
from urllib.parse import quote

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

    results = []
    if task.status == "success" and task.output_path:
        # 1. 获取物理绝对路径，用于扫描文件
        # 假设 task.output_path 存的是 "outputs/user/..." 这种相对路径
        base_dir = os.getcwd()
        out_dir = os.path.join(base_dir, task.output_path, "output")

        if os.path.exists(out_dir):
            for f in os.listdir(out_dir):
                if not f.startswith("."):
                    # 2. 处理文件名中的空格和中文 (关键修复！)
                    # 例如 "Gemini Image.png" -> "Gemini%20Image.png"
                    safe_filename = quote(f)

                    # 3. 拼接 Web 路径 (强制使用正斜杠)
                    # 数据库里的 output_path 可能包含 Windows 反斜杠，先统一替换
                    clean_rel_path = task.output_path.replace("\\", "/")

                    # 拼成: outputs/user/xxx/output/filename.png
                    web_path = f"{clean_rel_path}/output/{safe_filename}"
                    results.append(web_path)

    return {
        "status": task.status,
        "progress": task.progress,
        "results": results
    }
@router.get("/queue_count")
def queue_count(db: Session = Depends(get_db)):
    """返回还在排队的任务数（pending + running）"""
    n = db.query(TaskLog).filter(TaskLog.status.in_(["pending", "running"])).count()
    return {"waiting": n}