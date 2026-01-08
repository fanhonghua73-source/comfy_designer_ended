import os


class Settings:
    # --- ComfyUI 相关 ---
    # 如果是双显卡，可以扩展为列表 ["http://127.0.0.1:8188", "http://127.0.0.1:8189"]
    COMFY_URL = "http://127.0.0.1:8188"
    COMFY_WS_URL = "ws://127.0.0.1:8188/ws"

    # ComfyUI 的物理安装路径中的 input 文件夹，用于存放设计师上传的图
    COMFY_INPUT_PATH = "F:\comfyuidesigner\ComfyUI_AzenV02\ComfyUI\input"
    COMFY_OUTPUT_PATH = r"F:\comfyuidesigner\ComfyUI_AzenV02\ComfyUI\output"
    # --- 数据库相关 ---
    DATABASE_URL = "mysql+pymysql://root:240039@localhost:3306/comfy_db"

    # --- 存储相关 ---
    # 设计师私有文件的根目录
    STORAGE_ROOT = os.path.abspath("./outputs")
    # 工作流配置文件的根目录
    WORKFLOW_DIR = os.path.abspath("./workflows")


settings = Settings()