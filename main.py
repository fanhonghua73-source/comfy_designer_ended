import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 导入核心组件
from core.config import settings
from core.database import engine, Base
from core.comfy_watcher import watch_comfyui

# 导入接口路由
from api import workflows, tasks

# 1. 自动创建数据库表 (如果 MySQL 中不存在)
# 注意：在生产环境建议使用 Alembic 处理数据库迁移
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bonbon AI 设计管理中台",
    description="为设计师定制的 ComfyUI 简化工作流管理系统",
    version="1.0.0"
)

# 2. 配置跨域 (CORS)
# 允许 UniApp 端（可能是 localhost:8080 或桌面端）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载静态文件目录
# 设计师生成的图片可以直接通过 http://server-ip:8000/outputs/... 访问查看
app.mount("/outputs", StaticFiles(directory=settings.STORAGE_ROOT), name="outputs")

# 4. 注册路由模块
app.include_router(workflows.router)
app.include_router(tasks.router)



# 5. 服务启动时的钩子
# main.py
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 30)
    print("--- 正在初始化后台监听服务 ---")

    # 获取 WebSocket 地址 (去掉 http://)
    ws_host = settings.COMFY_URL.replace("http://", "").replace("https://", "")

    # 显式创建后台任务，并添加错误回调
    task = asyncio.create_task(watch_comfyui(host=ws_host))

    # 添加一个简单的回调，如果任务意外结束会打印日志
    def task_done_callback(t):
        try:
            t.result()
        except Exception as e:
            print(f"CRITICAL: 监听任务崩溃: {e}")

    task.add_done_callback(task_done_callback)

    print(f"WebSocket 监听目标: ws://{ws_host}/ws")
    print("=" * 30 + "\n")

@app.get("/")
def read_root():
    return {"status": "running", "service": "Bonbon AI Management API"}


# 6. 运行程序
if __name__ == "__main__":
    import uvicorn

    # 监听 0.0.0.0 以便公司局域网内其他电脑访问
    uvicorn.run(app, host="0.0.0.0", port=8000)