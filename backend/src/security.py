import os,hashlib,jwt
from fastapi import Header,HTTPException
from datetime import datetime,timedelta,timezone
from .database import Session
from .models import User
SECRET=os.getenv('JWT_SECRET','poly-blend-local-change-me')
def password_hash(p):return hashlib.pbkdf2_hmac('sha256',p.encode(),b'poly-blend-v1',150000).hex()
def token_for(u):return jwt.encode({'sub':str(u.id),'exp':datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm='HS256')
def current(authorization:str=Header(default='')):
    try:
        d=jwt.decode(authorization.removeprefix('Bearer '),SECRET,algorithms=['HS256'])
        with Session() as s:
            u=s.get(User,int(d['sub']))
            if not u:raise ValueError()
            return {'email':u.email,'role':u.role}
    except Exception:raise HTTPException(401,'请重新登录')
def allow(u,*roles):
    if u['role'] not in roles:raise HTTPException(403,'当前角色无此操作权限')
