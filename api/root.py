from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.models import User, UserWorkflow
from api.auth import get_current
from core.database import get_db
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/root", tags=["Root"])


# =======================
# 1. 权限依赖
# =======================
def get_root(user: User = Depends(get_current)):
    """仅允许 Root 用户访问"""
    if not user.is_root:
        raise HTTPException(403, "需要 root 权限")
    return user


# =======================
# 2. Pydantic 模型定义
# =======================

# 用于新建用户 和 修改用户权限
class UserEdit(BaseModel):
    username: str
    password: Optional[str] = None  # 编辑时留空代表不修改
    is_root: bool = False
    workflows: list[str] = []  # 权限列表 ID


# 用于重置密码 (接收 JSON Body)
class ResetPwdForm(BaseModel):
    newPwd: str


# =======================
# 3. 接口逻辑
# =======================

# ---------- A. 用户列表 (含权限回显) ----------
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
            # 将 [('rembg',), ('gemini',)] 转为 ['rembg', 'gemini']
            "workflows": [w[0] for w in wfs]
        })
    return result


# ---------- B. 新建用户 ----------
@router.post("/users")
def create_user(form: UserEdit, root: User = Depends(get_root), db: Session = Depends(get_db)):
    # 新建时密码必填
    if not form.password:
        raise HTTPException(400, "新建用户必须填写密码")

    # 查重
    if db.query(User).filter(User.username == form.username).first():
        raise HTTPException(400, "用户名已存在")

    # 创建用户
    u = User(username=form.username, password=User.hash_pwd(form.password), is_root=form.is_root)
    db.add(u)
    db.flush()  # 获取 u.id

    # 添加权限
    for wid in form.workflows:
        db.add(UserWorkflow(user_id=u.id, workflow_id=wid))

    db.commit()
    return {"id": u.id}


# ---------- C. 修改用户权限 (PUT) ----------
@router.put("/users/{uid}")
def update_user_perm(uid: int, form: UserEdit, root: User = Depends(get_root), db: Session = Depends(get_db)):
    u = db.query(User).get(uid)
    if not u: raise HTTPException(404, "用户不存在")

    # 1. 更新 Root 状态
    u.is_root = form.is_root

    # 2. 如果填了新密码，则修改；没填则保持原样
    if form.password:
        u.password = User.hash_pwd(form.password)

    # 3. 重写 workflows 权限 (先全删，后重加)
    db.query(UserWorkflow).filter(UserWorkflow.user_id == uid).delete()
    for wid in form.workflows:
        db.add(UserWorkflow(user_id=uid, workflow_id=wid))

    db.commit()
    return {"msg": "权限已更新"}


# ---------- D. 删除用户 ----------
@router.delete("/users/{uid}")
def delete_user(uid: int, root: User = Depends(get_root), db: Session = Depends(get_db)):
    # 先删权限表引用
    db.query(UserWorkflow).filter(UserWorkflow.user_id == uid).delete()
    # 再删用户
    db.query(User).filter(User.id == uid).delete()

    db.commit()
    return {"msg": "已删除"}


# ---------- E. 重置密码 (PATCH) ----------
# 注意：这里使用了 ResetPwdForm 来接收 JSON，修复了之前无效的问题
@router.patch("/users/{uid}/password")
def reset_password(uid: int, form: ResetPwdForm, root: User = Depends(get_root), db: Session = Depends(get_db)):
    u = db.query(User).get(uid)
    if not u: raise HTTPException(404, "用户不存在")

    # 使用 form.newPwd 获取参数
    u.password = User.hash_pwd(form.newPwd)

    db.commit()
    return {"msg": "已重置"}