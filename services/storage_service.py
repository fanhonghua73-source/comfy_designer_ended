import os
import shutil
from datetime import datetime

BASE_OUTPUT = "outputs"
COMFY_INPUT_DIR = "F:\comfyuidesigner\ComfyUI_AzenV02\ComfyUI\input"  # 替换为你实际的路径


def prepare_output_dir(user, workflow_id, task_id):
    path = os.path.join(BASE_OUTPUT, user, workflow_id, datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + task_id)
    os.makedirs(os.path.join(path, "input"), exist_ok=True)
    os.makedirs(os.path.join(path, "output"), exist_ok=True)
    return path


def save_inputs_and_link(files, output_dir):
    result_filenames = []
    for file in files:
        # 1. 保存到设计师私有目录
        dst = os.path.join(output_dir, "input", file.filename)
        with open(dst, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 2. 软链接或拷贝到 ComfyUI input 目录 (加上前缀防重名)
        comfy_filename = f"remote_{file.filename}"
        comfy_path = os.path.join(COMFY_INPUT_DIR, comfy_filename)
        shutil.copy(dst, comfy_path)  # 为了安全和权限，使用拷贝

        result_filenames.append(comfy_filename)
    return result_filenames