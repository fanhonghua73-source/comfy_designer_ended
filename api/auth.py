from fastapi import APIRouter, HTTPException, Depends, Header # 确保导入 Header
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginForm(BaseModel):
    username: str
    password: str

# 【新增】定义修改密码的接收模型
class ChangePwdForm(BaseModel):
    newPwd: str

# ---------- 登录 (保持不变) ----------
@router.post("/login")
def login(form: LoginForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or user.password != User.hash_pwd(form.password):
        raise HTTPException(401, "用户名或密码错误")
    token = f"{user.id}:{user.is_root}"
    return {"token": token, "isRoot": user.is_root, "username": user.username}

# ---------- 校验依赖 (保持不变) ----------
def get_current(token: str = Header(...), db: Session = Depends(get_db)):
    try:
        uid, is_root = token.split(":")
        user = db.query(User).get(int(uid))
        if not user: raise HTTPException(401, "非法 token")
        return user
    except Exception:
        raise HTTPException(401, "非法 token")

# ---------- 改自己密码 (修改此处) ----------
# 旧代码: def change_my_password(newPwd: str, ...):
# 新代码如下:
@router.put("/me/password")
def change_my_password(form: ChangePwdForm, user: User = Depends(get_current), db: Session = Depends(get_db)):
    # 注意这里通过 form.newPwd 获取
    user.password = User.hash_pwd(form.newPwd)
    db.commit()
    return {"msg": "已修改"}