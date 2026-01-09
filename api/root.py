from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.models import User, UserWorkflow
from api.auth import get_current
from core.database import get_db
from pydantic import BaseModel
router = APIRouter(prefix="/api/root", tags=["Root"])

# 依赖：必须是 root
def get_root(user: User = Depends(get_current)):
    if not user.is_root:
        raise HTTPException(403, "需要 root 权限")
    return user

# ---------- 用户列表 ----------
@router.get("/users")
def list_users(root: User = Depends(get_root), db: Session = Depends(get_db)):
    return db.query(User).all()

# ---------- 新建/修改用户 ----------
class UserEdit(BaseModel):
    username: str
    password: str
    is_root: bool = False
    workflows: list[str] = []   # 可见 workflow_id 列表

@router.post("/users")
def create_user(form: UserEdit, root: User = Depends(get_root), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == form.username).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=form.username, password=User.hash_pwd(form.password), is_root=form.is_root)
    db.add(u); db.flush()
    for wid in form.workflows:
        db.add(UserWorkflow(user_id=u.id, workflow_id=wid))
    db.commit()
    return {"id": u.id}

# ---------- 删除用户 ----------
@router.delete("/users/{uid}")
def delete_user(uid: int, root: User = Depends(get_root), db: Session = Depends(get_db)):
    db.query(UserWorkflow).filter(UserWorkflow.user_id == uid).delete()
    db.query(User).filter(User.id == uid).delete()
    db.commit()
    return {"msg": "已删除"}

# ---------- 重置密码 ----------
@router.patch("/users/{uid}/password")
def reset_password(uid: int, newPwd: str, root: User = Depends(get_root), db: Session = Depends(get_db)):
    u = db.query(User).get(uid)
    if not u: raise HTTPException(404, "用户不存在")
    u.password = User.hash_pwd(newPwd)
    db.commit()
    return {"msg": "已重置"}