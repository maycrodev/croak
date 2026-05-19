"""Configuracion central leida de variables de entorno (estilo 12-factor).

Se instancia una sola vez (`settings`) al importar el modulo. Todos los servicios
comparten estas claves; los valores por defecto permiten correr en local sin .env.
"""
from __future__ import annotations

import os


class Settings:
    """Configuracion del proceso resuelta desde el entorno."""

    def __init__(self) -> None:
        self.service_name: str = os.environ.get("SERVICE_NAME", "croak-service")
        self.database_url: str = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://croak:croak@localhost:5432/croak",
        )
        self.jwt_secret: str = os.environ.get("JWT_SECRET", "croak-dev-secret-change-me")
        self.jwt_algorithm: str = os.environ.get("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))
        self.audit_url: str = os.environ.get("AUDIT_URL", "http://audit-service:8008")
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")


settings = Settings()
