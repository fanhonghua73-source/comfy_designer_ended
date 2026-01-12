import json
import os
import uuid
import requests
from .storage_service import prepare_output_dir, save_inputs_and_link
from core.models import TaskLog
from core.database import SessionLocal

WORKFLOW_DIR = "workflows"


async def run_workflow_logic(workflow_id, params, files, user):
    # 1. 加载配置
    wf_path = f"{WORKFLOW_DIR}/{workflow_id}.json"
    ui_path = f"{WORKFLOW_DIR}/{workflow_id}.ui.json"

    with open(wf_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    with open(ui_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    task_id = uuid.uuid4().hex[:8]
    output_dir = prepare_output_dir(user, workflow_id, task_id)

    # 2. 处理上传图片
    image_filenames = save_inputs_and_link(files, output_dir)
    img_idx = 0

    # 3. 参数动态注入
    for item in schema["inputs"]:
        node_id = str(item["node_id"])
        if item["type"] in ["image", "video"]:
            if img_idx < len(image_filenames):
                # 关键修改：使用 item["field"] 动态决定是注入给 'image' 还是 'video' 字段
                workflow[node_id]["inputs"][item["field"]] = image_filenames[img_idx]
                img_idx += 1
        else:
            workflow[node_id]["inputs"][item["field"]] = params.get(item["key"])

    # 4. 提交 ComfyUI
    resp = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow})
    comfy_id = resp.json()["prompt_id"]

    # 5. 写入 MySQL 日志
    db = SessionLocal()
    new_log = TaskLog(
        prompt_id=comfy_id,
        user_name=user,
        workflow_id=workflow_id,
        output_path=output_dir,
        params=json.dumps(params)
    )
    db.add(new_log)
    db.commit()
    db.close()

    return {"task_id": task_id, "comfy_id": comfy_id, "output_dir": output_dir}