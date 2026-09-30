"""Schemas de request/response da autenticação. UserResponse nunca inclui password_hash."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole, UserStatus


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None
