"""Cria o primeiro usuário ADMIN a partir de SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD.

Rodar manualmente após `alembic upgrade head`:

    python -m scripts.seed_admin

Idempotente: não faz nada se as variáveis não estiverem definidas ou se o
e-mail já existir.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def main() -> None:
    settings = get_settings()
    if not settings.SEED_ADMIN_EMAIL or not settings.SEED_ADMIN_PASSWORD:
        print("SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD não definidos — nada a fazer.")
        return

    db = SessionLocal()
    try:
        service = AuthService(repo=UserRepository(db), settings=settings)
        try:
            user = service.create_user(
                name=settings.SEED_ADMIN_NAME,
                email=settings.SEED_ADMIN_EMAIL,
                password=settings.SEED_ADMIN_PASSWORD,
                role=UserRole.ADMIN,
            )
            print(f"Admin criado: {user.email}")
        except ValueError:
            print(f"Admin {settings.SEED_ADMIN_EMAIL} já existe — nada a fazer.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
