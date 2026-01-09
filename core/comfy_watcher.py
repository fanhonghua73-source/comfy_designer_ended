import asyncio, aiohttp, json, os, shutil, requests, time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import TaskLog
from core.config import settings
import websockets

# ---------- 新增：纯 HTTP 轮询 ----------
async def poll_pending_tasks():
    """每隔 5s 主动把所有 pending 任务拉到 history 接口查一遍"""
    while True:
        await asyncio.sleep(5)
        db: Session = SessionLocal()
        try:
            # 只扫最近 30 分钟的任务，避免历史脏数据
            cutoff = int(time.time()) - 30*60
            tasks = db.query(TaskLog)\
                      .filter(TaskLog.status == 'pending',
                              TaskLog.created_at >= cutoff)\
                      .all()
            for task in tasks:
                await check_one_task(db, task)
        finally:
            db.close()

async def check_one_task(db: Session, task: TaskLog):
    """真正去 ComfyUI /history 接口查状态并搬运"""
    try:
        url = f"{settings.COMFY_URL}/history/{task.prompt_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                hist = await resp.json()
        if task.prompt_id not in hist:
            return
        hist_item = hist[task.prompt_id]
        ok = move_results(task, hist_item)
        if ok:
            task.status = "success"
            task.progress = 100
            db.commit()
            print(f"✅ 轮询搬运成功：{task.prompt_id}")
    except Exception as e:
        print(f"轮询检查失败：{task.prompt_id} {e}")


async def watch_comfyui(host="127.0.0.1:8188"):
    ws_host = host.replace("http://", "").replace("https://", "")
    uri = f"ws://{ws_host}/ws"
    print(f"🚀 [Watcher] 启动并尝试连接: {uri}")

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("📡 [WebSocket] 成功连接，开始监控...")
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)

                    # 只要 ComfyUI 有动作（不管是进度还是完成），我们都去检查一下数据库
                    # 重点捕获 'executing' 且 node 为 None (表示任务结束)
                    if data['type'] in ['executing', 'status']:
                        db = SessionLocal()
                        try:
                            # 1. 获取当前可能结束的 prompt_id
                            pid = data['data'].get('prompt_id')

                            # 2. 如果消息里没带 ID，我们就把数据库里所有 pending 的任务拿出来对一次
                            tasks_to_check = []
                            if pid:
                                tasks_to_check = db.query(TaskLog).filter(TaskLog.prompt_id == pid).all()
                            else:
                                tasks_to_check = db.query(TaskLog).filter(TaskLog.status == 'pending').all()

                            for task in tasks_to_check:
                                # 去 ComfyUI 历史接口确认这个 ID 到底完事没
                                h_url = f"{settings.COMFY_URL}/history/{task.prompt_id}"
                                h_res = requests.get(h_url).json()

                                if task.prompt_id in h_res:
                                    print(f"🚩 发现已完成任务: {task.prompt_id}，开始搬运...")
                                    # 执行物理搬运
                                    sync_success = move_results(task, h_res[task.prompt_id])
                                    if sync_success:
                                        task.status = "success"
                                        task.progress = 100
                                        db.commit()
                                        print(f"✅ 任务 {task.prompt_id} 同步成功")
                        finally:
                            db.close()
        except Exception as e:
            print(f"❌ 监听异常: {e}，5秒后重连...")
            await asyncio.sleep(5)


def move_results(task: TaskLog, history_item):
    try:
        outputs = history_item.get("outputs", {})
        for node_id, content in outputs.items():
            if "images" in content:
                for img in content["images"]:
                    fname = img["filename"]
                    src = os.path.join(settings.COMFY_OUTPUT_PATH, fname)
                    target_dir = os.path.join(os.getcwd(), task.output_path, "output")
                    os.makedirs(target_dir, exist_ok=True)
                    dst = os.path.join(target_dir, fname)
                    if os.path.exists(src):
                        shutil.copy(src, dst)
                        task.output_path = f"{task.output_path}/output/{fname}".replace("\\", "/")
                        return True
        return False
    except Exception as e:
        print("搬运失败", e)
        return False