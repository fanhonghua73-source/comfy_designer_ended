from fastapi import APIRouter, HTTPException
import os
import json
from core.config import settings

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


@router.get("/list")
def list_workflows():
    """遍历工作流文件夹，返回所有已配置好的工作流"""
    items = []
    if not os.path.exists(settings.WORKFLOW_DIR):
        return items

    for f in os.listdir(settings.WORKFLOW_DIR):
        # 我们通过是否存在 .ui.json 来判断该工作流是否已由管理员配置完成
        if f.endswith(".ui.json"):
            try:
                with open(os.path.join(settings.WORKFLOW_DIR, f), "r", encoding="utf-8") as file:
                    data = json.load(file)
                    items.append({
                        "id": f.replace(".ui.json", ""),  # 使用文件名作为 ID
                        "name": data.get("name", f),
                        "description": data.get("description", "")
                    })
            except Exception as e:
                print(f"解析 {f} 失败: {e}")
    return items


@router.get("/{workflow_id}/schema")
def get_workflow_schema(workflow_id: str):
    """返回特定工作流的动态表单结构"""
    ui_path = os.path.join(settings.WORKFLOW_DIR, f"{workflow_id}.ui.json")
    if not os.path.exists(ui_path):
        raise HTTPException(status_code=404, detail="工作流 UI 配置不存在")

    with open(ui_path, "r", encoding="utf-8") as f:
        return json.load(f)