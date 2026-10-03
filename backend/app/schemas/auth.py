"""Schemas de request/response da autenticação. UserResponse (gestão de usuários)
mora em app.schemas.user e é reexportado aqui para não quebrar imports existentes."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserResponse

__all__ = ["LoginRequest", "UserResponse"]


class LoginRequest(BaseModel):
    email: str
    password: str
