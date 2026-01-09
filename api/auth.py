from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import User, UserWorkflow
from pydantic import BaseModel
from fastapi import Header
router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginForm(BaseModel):
    username: str
    password: str

# ---------- 登录 ----------
@router.post("/login")
def login(form: LoginForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or user.password != User.hash_pwd(form.password):
        raise HTTPException(401, "用户名或密码错误")
    # 简易 token，生产可换 jwt
    token = f"{user.id}:{user.is_root}"
    return {"token": token, "isRoot": user.is_root, "username": user.username}

# ---------- 校验依赖 ----------
def get_current(token: str = Header(...), db: Session = Depends(get_db)):
    try:
        uid, is_root = token.split(":")
        user = db.query(User).get(int(uid))
        if not user: raise HTTPException(401, "非法 token")
        return user
    except Exception:
        raise HTTPException(401, "非法 token")

# ---------- 改自己密码 ----------
@router.put("/me/password")
def change_my_password(newPwd: str, user: User = Depends(get_current), db: Session = Depends(get_db)):
    user.password = User.hash_pwd(newPwd)
    db.commit()
    return {"msg": "已修改"}