from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.models import User, UserWorkflow
from api.auth import get_current
from core.database import get_db
from pydantic import BaseModel
from typing import Optional  # 1. 导入 Optional

router = APIRouter(prefix="/api/root", tags=["Root"])


# 依赖：必须是 root (保持不变)
def get_root(user: User = Depends(get_current)):
    if not user.is_root:
        raise HTTPException(403, "需要 root 权限")
    return user


# ---------- 用户列表 (修改逻辑：返回 workflows 数组) ----------
@router.get("/users")
def list_users(root: User = Depends(get_root), db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        # 查出该用户的所有权限 ID
        wfs = db.query(UserWorkflow.workflow_id).filter(UserWorkflow.user_id == u.id).all()
        result.append({
            "id": u.id,
            "username": u.username,
            "is_root": u.is_root,
            "workflows": [w[0] for w in wfs]  # 转成列表 ['rembg', 'gemini']
        })
    return result


# ---------- 模型定义 (修改：密码变为可选) ----------
class UserEdit(BaseModel):
    username: str
    password: Optional[str] = None  # 2. 修改：允许为空，用于更新权限时不改密码
    is_root: bool = False
    workflows: list[str] = []


# ---------- 新建用户 (保持逻辑，但增加密码校验) ----------
@router.post("/users")
def create_user(form: UserEdit, root: User = Depends(get_root), db: Session = Depends(get_db)):
    if not form.password:
        raise HTTPException(400, "新建用户必须填写密码")
    if db.query(User).filter(User.username == form.username).first():
        raise HTTPException(400, "用户名已存在")

    u = User(username=form.username, password=User.hash_pwd(form.password), is_root=form.is_root)
    db.add(u);
    db.flush()
    for wid in form.workflows:
        db.add(UserWorkflow(user_id=u.id, workflow_id=wid))
    db.commit()
    return {"id": u.id}


# ---------- (新增) 修改用户权限 ----------
@router.put("/users/{uid}")
def update_user_perm(uid: int, form: UserEdit, root: User = Depends(get_root), db: Session = Depends(get_db)):
    u = db.query(User).get(uid)
    if not u: raise HTTPException(404, "用户不存在")

    # 1. 更新 Root 状态
    u.is_root = form.is_root

    # 2. 如果填了密码，则重置密码
    if form.password:
        u.password = User.hash_pwd(form.password)

    # 3. 重写 workflows 权限 (先删后加)
    db.query(UserWorkflow).filter(UserWorkflow.user_id == uid).delete()
    for wid in form.workflows:
        db.add(UserWorkflow(user_id=uid, workflow_id=wid))

    db.commit()
    return {"msg": "权限已更新"}


# ---------- 删除用户 (保持不变) ----------
@router.delete("/users/{uid}")
def delete_user(uid: int, root: User = Depends(get_root), db: Session = Depends(get_db)):
    db.query(UserWorkflow).filter(UserWorkflow.user_id == uid).delete()
    db.query(User).filter(User.id == uid).delete()
    db.commit()
    return {"msg": "已删除"}


# ---------- 重置密码 (保持不变) ----------
@router.patch("/users/{uid}/password")
def reset_password(uid: int, newPwd: str, root: User = Depends(get_root), db: Session = Depends(get_db)):
    u = db.query(User).get(uid)
    if not u: raise HTTPException(404, "用户不存在")
    u.password = User.hash_pwd(newPwd)
    db.commit()
    return {"msg": "已重置"}