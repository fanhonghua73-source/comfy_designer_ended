from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import UserWorkflow
from api.auth import get_current          # 取出当前登录用户
from core.config import settings
import os, json

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])

# ---------- 依赖：已登录 ----------
def _current_user(user=Depends(get_current)):
    return user

# ---------- 列表（带权限） ----------
@router.get("/list")
def list_workflows(user=Depends(_current_user), db: Session = Depends(get_db)):
    if user.is_root:
        allowed = None                       # root 看全部
    else:
        allowed = [w.workflow_id for w in db.query(UserWorkflow.workflow_id)
                                           .filter(UserWorkflow.user_id == user.id).all()]
    items = []
    wf_dir = settings.WORKFLOW_DIR
    if not os.path.exists(wf_dir):
        return items

    for f in os.listdir(wf_dir):
        if f.endswith(".ui.json"):
            wid = f.replace(".ui.json", "")
            if allowed and wid not in allowed:
                continue                     # 普通用户跳过未授权的
            try:
                with open(os.path.join(wf_dir, f), encoding="utf-8") as fp:
                    data = json.load(fp)
                items.append({
                    "id": wid,
                    "name": data.get("name", wid),
                    "description": data.get("description", "")
                })
            except Exception as e:
                print(f"解析 {f} 失败: {e}")
    return items

# ---------- 表单结构（带权限） ----------
@router.get("/{workflow_id}/schema")
def get_workflow_schema(workflow_id: str,
                        user=Depends(_current_user),
                        db: Session = Depends(get_db)):
    # 先鉴权
    if not user.is_root:
        auth = db.query(UserWorkflow).filter(
            UserWorkflow.user_id == user.id,
            UserWorkflow.workflow_id == workflow_id
        ).first()
        if not auth:
            raise HTTPException(403, "你没有访问该工作流的权限")

    ui_path = os.path.join(settings.WORKFLOW_DIR, f"{workflow_id}.ui.json")
    if not os.path.exists(ui_path):
        raise HTTPException(404, "工作流 UI 配置不存在")
    with open(ui_path, encoding="utf-8") as f:
        return json.load(f)