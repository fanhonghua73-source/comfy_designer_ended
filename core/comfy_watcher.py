# comfy_watcher.py
import asyncio
import json
import os
import shutil
import requests
import aiohttp
import time
import websockets
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import TaskLog
from core.config import settings
from core.progress_hub import broadcast


# --------------------------------------------------
# 1. WebSocket 监听：实时进度广播 + 触发搬运（加速器）
# --------------------------------------------------
async def watch_comfyui(host="127.0.0.1:8188"):
    ws_host = host.replace("http://", "").replace("https://", "")
    uri = f"ws://{ws_host}/ws"
    print(f"🚀 [Watcher] 启动并尝试连接: {uri}")

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("📡 [WebSocket] 成功连接，开始监控...")
                async for raw in websocket:
                    data = json.loads(raw)

                    # ------ 进度广播 ------
                    if data["type"] == "progress":
                        await broadcast({
                            "type": "progress",
                            "node": data.get("node"),
                            "value": data["data"]["value"],
                            "max": data["data"]["max"]
                        })
                    if data["type"] == "executing" and data["data"].get("node"):
                        await broadcast({"type": "node_start", "node": data["data"]["node"]})
                    if data["type"] == "executing" and data["data"].get("node") is None:
                        await broadcast({
                            "type": "finished",
                            "prompt_id": data["data"].get("prompt_id")
                        })
                    # ----------------------

                    # 原有搬运逻辑
                    if data["type"] in ["executing", "status"]:
                        pid = data["data"].get("prompt_id")
                        db: Session = SessionLocal()
                        try:
                            tasks = []
                            if pid:
                                tasks = db.query(TaskLog).filter(TaskLog.prompt_id == pid).all()
                            else:
                                tasks = db.query(TaskLog).filter(TaskLog.status == "pending").all()
                            for task in tasks:
                                await check_one_task(db, task)
                        finally:
                            db.close()
        except Exception as e:
            print(f"❌ WebSocket 异常: {e}，5 秒后重连...")
            await asyncio.sleep(5)


# --------------------------------------------------
# 2. 定时轮询：兜底搬运
# --------------------------------------------------
async def poll_pending_tasks():
    """每 5 秒扫一次最近 30 分钟的 pending 任务"""
    while True:
        await asyncio.sleep(5)
        db: Session = SessionLocal()
        try:
            cutoff = int(time.time()) - 30 * 60
            tasks = db.query(TaskLog)\
                      .filter(TaskLog.status == "pending",
                              TaskLog.created_at >= cutoff)\
                      .all()
            for task in tasks:
                await check_one_task(db, task)
        finally:
            db.close()


# --------------------------------------------------
# 3. 统一搬运函数（异步版，可被上面两处调用）
# --------------------------------------------------
async def check_one_task(db: Session, task: TaskLog):
    try:
        url = f"{settings.COMFY_URL}/history/{task.prompt_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                hist = await resp.json()
        if task.prompt_id not in hist:
            return
        ok = move_results(task, hist[task.prompt_id])
        if ok:
            task.status = "success"
            task.progress = 100
            db.commit()
            print(f"✅ 搬运成功：{task.prompt_id}")
    except Exception as e:
        print(f"搬运失败：{task.prompt_id} {e}")


def move_results(task: TaskLog, history_item):
    try:
        outputs = history_item.get("outputs", {})
        # 【修改 1】增加 found_any 标记，用于代替原来直接 return True 的逻辑，确保循环能跑完
        found_any = False

        for node_id, content in outputs.items():
            # 【修改 2】将原来的 if "images" in content: 改为遍历三种类型
            for type_key in ["images", "videos", "gifs"]:
                if type_key in content:
                    for item in content[type_key]:
                        fname = item["filename"]
                        src = os.path.join(settings.COMFY_OUTPUT_PATH, fname)

                        # 确保目录存在（原代码 121-122 行）
                        target_dir = os.path.join(os.getcwd(), task.output_path, "output")
                        os.makedirs(target_dir, exist_ok=True)

                        dst = os.path.join(target_dir, fname)
                        if os.path.exists(src):
                            shutil.copy(src, dst)
                            found_any = True
                            # 【修改 3】关键！直接删除原代码第 127 行：task.output_path = ...
                            # 绝对不要修改 task.output_path，保持它指向文件夹

        return found_any
    except Exception as e:
        print(f"move_results 失败: {e}")
        return False