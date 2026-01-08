from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(String(100), unique=True)  # ComfyUI 的任务ID
    user_name = Column(String(50))
    workflow_id = Column(String(50))
    status = Column(String(20), default="pending") # pending, running, success, failed
    progress = Column(Integer, default=0)
    output_path = Column(String(255))
    params = Column(Text)  # 存储当时输入的 JSON 参数串
    created_at = Column(DateTime, default=datetime.now)
    duration = Column(Integer, nullable=True) # 耗时（秒）