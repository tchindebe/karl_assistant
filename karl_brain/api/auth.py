"""
Authentification — login + token JWT.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.security import create_token, verify_admin_password

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    if not verify_admin_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_token("admin")
    return LoginResponse(token=token, username="admin")
