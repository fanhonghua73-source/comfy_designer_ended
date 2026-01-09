from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base
import hashlib

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

class User(Base):
    __tablename__ = "users"
    id        = Column(Integer, primary_key=True, index=True)
    username  = Column(String(50), unique=True, index=True)
    password  = Column(String(64))               # sha256
    is_root   = Column(Boolean, default=False)
    created_at= Column(DateTime, default=datetime.now)

    @staticmethod
    def hash_pwd(pwd: str) -> str:
        return hashlib.sha256(pwd.encode()).hexdigest()


class UserWorkflow(Base):
    __tablename__ = "user_workflow"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, index=True)
    workflow_id  = Column(String(50), index=True)   # 对应 *.ui.json 的文件名