"""Schemas de request/response da gestão de usuários. UserResponse nunca inclui
password_hash."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.user import UserRole, UserStatus


def _validate_email_format(value: str) -> str:
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("E-mail inválido.")
    return value


def _validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Senha deve ter ao menos 8 caracteres.")
    return value


class UserCreateIn(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole = UserRole.COLABORADOR
    manager_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nome é obrigatório.")
        return value

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return _validate_email_format(value)

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserUpdateIn(BaseModel):
    name: str
    email: str
    role: UserRole
    manager_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nome é obrigatório.")
        return value

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return _validate_email_format(value)


class AdminResetPasswordIn(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    status: UserStatus
    manager_id: uuid.UUID | None
    manager_name: str | None = None
    team_size: int | None = None
    created_at: datetime
    last_login_at: datetime | None
